using Graphs
using Random

model_dir = "../model"
include("$model_dir/problem.jl")
include("$model_dir/utils.jl")


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
    two_paths = length(paths(problem; n_steps)) ≥ 2

    no_skip2 = !any(enumerate(problem.graph)) do (n, kids)
        mod1(n+2, 11) in kids || mod1(n-2, 11) in kids
    end

    no_skip1 = !any(enumerate(problem.graph)) do (n, kids)
        mod1(n+1, 11) in kids || mod1(n-1, 11) in kids
    end

    two_paths && no_skip2 && no_skip1
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



function make_trials(; )
    n = 11
    rewards = exponential_rewards(8)
    rdist = IIDSampler(n, rewards)
    kws = (;n, rdist)


    practice = repeatedly(10) do
        p = sample_problem(;kws...) do p
            default_problem_requirement(p) || return false
            # value(p) > 0 || return false
            # opaths = optimal_paths(p)
            # length(opaths) == 1 || return false

            ps = paths(p)
            pv = value.(p, ps)
            is_optimal = pv .== maximum(pv)
            sum(is_optimal) == 1 || return false
            opt_i = findall(is_optimal)[1]
            pv[opt_i] > 0 || return false
            maximum(pv[.!is_optimal]) ≤ pv[opt_i] - 2 || return false
            2 ≤ length(ps[opt_i]) ≤ 3 || return false
        end
        (;JSON.lower(p)..., max_score=value(p))
    end

    main = repeatedly(300) do
        p = sample_problem(;kws...)
        (;JSON.lower(p)..., max_score=value(p))
    end
    (; practice, main )
end

# %% --------

function circle_layout(N)
    # we use 0:N-1 to match python's 0 indexing
    map(0:N-1) do s
        angle = π/2 + s * 2 * π / N
        x = (cos(angle) + 1) / 2 - 0.5
        y = (sin(angle) + 1) / 2 - 0.5
        (x, y)
    end
end


# %% --------

function get_version()
    for line in readlines("config.py")
        m = match(r"VERSION = '(.*)'", line)
        if !isnothing(m)
            return m.captures[1]
        end
    end
    error("Cannot find version")
end


version = get_version()
n_subj = 200  # better safe than sorry
Random.seed!(hash(version))
subj_trials = repeatedly(make_trials, n_subj)
layout = circle_layout(11)

# %% --------

points_per_cent = 2

dest = "config/$(version)"
rm(dest, recursive=true, force=true)
mkpath(dest)
foreach(enumerate(subj_trials)) do (i, trials)
    parameters = (;points_per_cent, layout, time_limit=15, summarize_every=10, gaze_contingent=true)
    write("$dest/$i.json", json((;parameters, trials)))
    println("$dest/$i.json")
end

# %% --------

# bonus = map(subj_trials) do trials
#     trials = mapreduce(vcat, [:main, :eyetracking]) do t
#         get(trials, t, [])
#     end
#     points = 50 + sum(value.(trials))
#     points / (points_per_cent * 100)
# end

# using UnicodePlots
# if length(bonus) > 1
#     display(histogram(bonus, nbins=10, vertical=true, height=10))
# end
