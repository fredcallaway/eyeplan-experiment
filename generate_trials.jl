using Graphs
using Random

model_dir = "/Users/fred/projects/graphnav/model"
include("$model_dir/problem.jl")
include("$model_dir/utils.jl")

# function default_graph_requirement(sgraph)
#     is_connected(sgraph) || return false
#     # all(vertices(sgraph)) do v
#     #     length(neighbors(sgraph, v)) ≥ 1
#     # end
# end

# function sample_graph(n; d=3, requirement=default_graph_requirement)
#     for i in 1:10000
#         sgraph = expected_degree_graph(fill(d, n)) |> random_orientation_dag
#         # sgraph = expected_degree_graph(fill(2, n))
#         requirement(sgraph) && return neighbor_list(sgraph)
#     end
#     error("Can't sample a graph!")
# end

neighbor_list(sgraph) = neighbors.(Ref(sgraph), vertices(sgraph))

"Adjacency list representation of the tree with specified branching at each depth"
AdjacenyList = Vector{Vector{Int}}
function regular_tree(branching::Vector{Int})
    t = AdjacenyList()
    function rec!(d)
        children = Int[]
        push!(t, children)
        idx = length(t)
        if d <= length(branching)
            for i in 1:branching[d]
                child = rec!(d+1)
                push!(children, child)
            end
        end
        return idx
    end
    rec!(1)
    t
end

empty_tree = AdjacenyList([[]])

function tree_join(g1, g2)
    n1 = length(g1)

    g1 = map(x -> x .+ 1, g1)
    g2 = map(x -> x .+ 1 .+ n1, g2)

    [[[2, n1+2]]; g1; g2]
end

function random_tree(splits)
    splits == 0 && return empty_tree
    splits == 1 && return tree_join(empty_tree, empty_tree)
    left = rand(0:splits-1)
    right = splits-1 - left
    tree_join(random_tree(left), random_tree(right))
end

function sample_graph(n)
    @assert !iseven(n)
    # base = [[2, 3], [4, 5], [6, 7], [], [], [], []]
    base = random_tree(div(n, 2))
    perm = randperm(length(base))
    graph = map(base[perm]) do x
        Int[findfirst(isequal(i), perm) for i in x]
    end
    start = findfirst(isequal(1), perm)
    graph, start
end

function default_problem_requirement(problem)
    n_steps = problem.n_steps
    if n_steps == -1
        n_steps = length(states(problem))
    end
    length(paths(problem; n_steps)) ≥ 2
end

function sample_problem_(;n, n_steps=-1, rdist=nothing, rewards=rand(rdist), graph=missing, start=missing)
    if ismissing(graph)
        graph, start = sample_graph(n)
    end
    @assert !ismissing(start)
    rewards = copy(rewards)
    rewards[start] = 0
    Problem(graph, rewards, start, n_steps)
end

function sample_problem(requirement=default_problem_requirement; kws...)
    for i in 1:10000
        problem = sample_problem_(;kws...)
        requirement(problem) && return problem
    end
    error("Can't sample a problem!")
end

discrete_uniform(v) = DiscreteNonParametric(v, ones(length(v)) / length(v))

function intro_graph(n)
    g = DiGraph(n)
    for i in 1:n
        add_edge!(g, i, mod1(i+1, n))
        add_edge!(g, i, mod1(i-3, n))
        # add_edge!(g, i, mod1(i+6, n))
    end
    g
end

function linear_rewards(n)
    @assert iseven(n)
    n2 = div(n,2)
    [-n2:1:-1; 1:1:n2]
end

function exponential_rewards(n; base=2)
    @assert iseven(n)
    n2 = div(n,2)
    v = base .^ (0:1:n2-1)
    sort!([-v; v])
end

function sample_nonmatching_perm(x)
    while true
        y = shuffle(x)
        if all(y .≠ x)
            return y
        end
    end
end

function sample_pairs(x)
    x = shuffle(x)
    y = sample_nonmatching_perm(x)
    collect(zip(x, y))
end

struct Shuffler{T}
    x::Vector{T}
end

function Random.rand(rng::AbstractRNG, s::Random.SamplerTrivial{<:Shuffler})
    shuffle(s[].x)
end

struct IIDSampler{T}
    n::Int
    x::Vector{T}
end

function Random.rand(rng::AbstractRNG, s::Random.SamplerTrivial{<:IIDSampler})
    (;n, x) = s[]
    rand(x, n)
end

struct ForceMoveTrial
    p::Problem
    path::Vector{Int}
end

function JSON.lower(t::ForceMoveTrial)
    (;JSON.lower(t.p)..., path=t.path .+ 1)
end

struct ForceHoverTrial
    p::Problem
    expansions::Vector{Tuple{Int, Int}}
end

function JSON.lower(t::ForceHoverTrial)
    (;JSON.lower(t.p)..., expansions=map(e -> e .- 1, t.expansions))
end

abstract type HoverGenerator end

function ForceHoverTrial(gen::HoverGenerator; kws...)
    problem = sample_problem(;kws...)
    expansions = generate(gen, problem)
    ForceHoverTrial(problem, expansions)
end


struct RolloutGenerator <: HoverGenerator
    n::Int
end

function generate(g::RolloutGenerator, problem::Problem)
    mapreduce(vcat, 1:g.n) do i
        sliding_window(rollout(problem), 2)
    end
end

sliding_window(xs, n) = [(xs[i], xs[i+1]) for i in 1:length(xs)-1]

function rollout(p::Problem)
    res = [p.start]
    n_steps = p.n_steps <= 0 ? 100 : p.n_steps
    for i in 1:n_steps
        childs = children(p, res[end])
        isempty(childs) && break
        push!(res, rand(childs))
    end
    res
end

struct RandomGenerator <: HoverGenerator
    n::Int
end

function generate(g::RandomGenerator, problem::Problem)
    repeatedly(g.n) do
        a = rand(states(problem))
        b = rand(children(problem, a))
        (a, b)
    end
end

function intro_problem(kws)
    @assert kws.n == 11
    graph = g = [
        [2, 11],
        [3],
        [4],
        [5],
        [6],
        [],
        [],
        [7],
        [8],
        [9],
        [10],
    ]
    Problem(graph, zeros(11), 1, -1)
end


function make_trials(; )
    n = 11
    rewards = exponential_rewards(8)
    rdist = IIDSampler(n, rewards)
    kws = (;n, rdist)

    (;
        intro = intro_problem(kws),
        calibration = Problem(neighbor_list(DiGraph(n)), zeros(n), 1, -1),
        vary_transition = sample_problem(;kws...),
        practice_revealed = [sample_problem(;kws...) for i in 1:2],
        main = [sample_problem(;kws...) for i in 1:30]
    )
end


# %% --------

function reward_graphics(n=8)
    emoji = [
        "🎈","🎀","📌","✏️","🔮","⚙️","💡","⏰",
        "✈️","🍎","🌞","⛄️","🐒","👟","🤖",
    ]
    Dict(zip(exponential_rewards(n), sample(emoji, n; replace=false)))
end

version = "e0.1"
Random.seed!(hash(version))
subj_trials = repeatedly(make_trials, 30)

# %% --------

points_per_cent = 2

dest = "json/config"
rm(dest, recursive=true)
mkpath(dest)
foreach(enumerate(subj_trials)) do (i, trials)
    parameters = (;points_per_cent)
    write("$dest/$i.json", json((;parameters, trials)))
    println("$dest/$i.json")
end

# %% --------

value(t::ForceHoverTrial) = value(t.p)

bonus = map(subj_trials) do trials
    trials = mapreduce(vcat, [:main, :eyetracking]) do t
        get(trials, t, [])
    end
    points = 50 + sum(value.(trials))
    points / (points_per_cent * 100)
end

using UnicodePlots
if length(bonus) > 1
    display(histogram(bonus, nbins=10, vertical=true, height=10))
end
