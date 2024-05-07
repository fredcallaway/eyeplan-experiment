using Graphs
using Random

model_dir = "../model/"
include("$model_dir/problem.jl")
include("$model_dir/utils.jl")

IMAGES = [
    "images/Animal_Sea_Solid_Small.png",
    "images/Animal_Sea_Pattern_Small.png",
    "images/Animal_Land_Solid_Large.png",
    "images/Animal_Land_Pattern_Small.png",
    "images/Object_Sea_Solid_Large.png",
    "images/Object_Sea_Pattern_Large.png",
    "images/Object_Land_Solid_Small.png",
    "images/Object_Land_Pattern_Large.png",
]
parse_features(img) = split(rsplit(img, "/")[end], "_")[1:3]
FEATURES = map(IMAGES) do img
    parse_features(IMAGES[1]) .== parse_features(img)
end

function describe_mask(mask)
    lookup = [
        Dict(true => "Animal", false => "Object"),
        Dict(true => "Sea", false => "Land"),
        Dict(true => "Solid", false => "Pattern"),
    ]
    items = map(1:3, mask) do i, m
        ismissing(m) && return missing
        lookup[i][m]
    end |> skipmissing
    join(items, " & ")
end

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

    i = findfirst(isequal(1), perm)
    perm[1], perm[i] = 1, perm[1]

    graph = map(base[perm]) do x
        Int[findfirst(isequal(i), perm) for i in x]
    end
    start = findfirst(isequal(1), perm)
    graph, start
end

function linear_rewards(n)
    @assert iseven(n)
    n2 = div(n,2)
    [-n2:1:-1; 1:1:n2]
end

function exponential_rewards(n; base=2)
    # @assert iseven(n)
    n2 = div(n,2)
    v = base .^ (0:1:n2-1)
    if iseven(n)
        sort!([-v; v])
    else
        sort!([-v; 0; v])
    end
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

function sample_trial(perm; n_feature=rand(1:3), value=rand(1:3), revealed=true, kws...)
    graph, start = sample_graph(length(perm)+1)
    for es in graph
        es .-= 1
    end
    start -= 1
    mask = Union{Missing,Bool}[missing, missing, missing]
    chosen = sample(1:3, n_feature; replace=false)
    mask[chosen] .= rand((true, false))
    targets = map(FEATURES[perm]) do f
        all(skipmissing(f .== mask))
    end
    rewards = [1; (value+1) .* targets] .- 1
    (;start, graph, rewards, value, revealed,
      targets = findall(targets) .- 1, description=describe_mask(mask), kws...)
end

function trial2problem(t)
    graph = map(t.graph) do es
        es .+ 1
    end
    Problem(graph, t.rewards, t.start+1, -1)
end

function intro_trial(perm; reward, kws...)
    t = sample_trial(perm)
    while true
        prob = trial2problem(t)
        if minimum(length, paths(prob)) ≥ 2
            break
        else
            t = sample_trial(perm)
        end
    end
    rewards = zeros(Int, length(perm)+1)
    if reward == :posneg
        rewards .= -1
        for s in t.graph[1]
            rewards[s+1] = 2
            # for s2 in t.graph[s+1]
            #     rewards[s+1] = -1
            # end
        end
    end
    (;t..., rewards, revealed=true, kws...)
end


function make_trials(; perm)
    # rdist = IIDSampler(n, rewards)
    (;
        # intro = [
        #     intro_trial(perm; reward=:zero),
        #     intro_trial(perm; reward=:posneg),
        # ],
        # intro_describe = [
        #     sample_trial(perm; n_feature=1, value=2),
        #     sample_trial(perm; n_feature=2, value=1),
        #     sample_trial(perm; n_feature=3, value=3),
        # ],
        # practice_revealed = [sample_trial(perm) for i in 1:3],
        # main = [sample_trial(perm) for i in 1:30],
        # intro_hover = [sample_trial(perm)],
        # main_revealed = [sample_trial(perm, hover_edges=true) for i in 1:200],
        main = [sample_trial(perm) for i in 1:200],
        # calibration = intro,
        # eyetracking = [sample_problem(;kws..., n_steps) for n_steps in shuffle(repeat(3:5, 7))]
    )
end

# %% --------

function circle_layout(N)
    # we use 0:N-1 to match python's 0 indexing
    map(0:N-1) do s
        angle = π/2 + s * 2 * π / N
        x = (cos(angle) + 1) / 2 - 0.5
        y = (sin(angle) + 1) / 2 - 0.5
        (-x, y)
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
Random.seed!(hash("v23"))  # TODO HAVE TO MAKE PERM THE SAME!!
layout = circle_layout(9)

# %% --------

dest = "config/$(version)"
rm(dest, recursive=true, force=true)
mkpath(dest)
for i in 1:30
    n = length(IMAGES) + 1
    perm = randperm(n-1)
    trials = make_trials(;perm)
    parameters = (;
        images = IMAGES[perm],
        points_per_cent = 1,
        layout,
    )

    write("$dest/$i.json", json((;parameters, trials)))
    println("$dest/$i.json")
end

# # %% --------


# points_per_cent = 2

# dest = "config/$(version)"
# rm(dest, recursive=true, force=true)
# mkpath(dest)
# foreach(enumerate(subj_trials)) do (i, trials)
#     parameters = (;points_per_cent, layout, time_limit=15, summarize_every=10, gaze_contingent=true)
#     write("$dest/$i.json", json((;parameters, trials)))
#     println("$dest/$i.json")
# end

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
