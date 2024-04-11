using Graphs
using Random

model_dir = "../model/"
include("$model_dir/problem.jl")
include("$model_dir/utils.jl")

neighbor_list(sgraph) = neighbors.(Ref(sgraph), vertices(sgraph))


function build_graph(n_layer, n_per_layer)
    n_state = 3 + 2 * (n_per_layer * n_layer)
    g = DiGraph(n_state)
    gg = 1:n_per_layer*n_layer

    lft = gg .+ 3
    rht = gg .+ length(gg) .+ 3

    add_edge!(g, 1, 2)
    add_edge!(g, 1, 3)

    sides = chunk.((lft, rht), n_per_layer)

    for n in sides[1][1]
        add_edge!(g, 2, n)
    end
    for n in sides[2][1]
        add_edge!(g, 3, n)
    end

    for layers in sides
        for i in 1:n_layer-1
            next = shuffle(layers[i+1])
            for (i, n) in enumerate(layers[i])
                add_edge!(g, n, next[i])
                add_edge!(g, n, next[mod1(i+1, n_per_layer)])
            end
        end
    end
    outcomes = [sides[1][end]; sides[2][end]]
    g, outcomes
end

function grid_layout(n_layer, n_per_layer, left)
    offset = left * -(n_per_layer+1)
    layout = map(Iterators.product(1:n_per_layer, 1:n_layer)) do (i, j)
        (i + offset, -j)
    end[:]
end

function center_and_scale(x::Vector{<:Real})
    lo = minimum(x)
    hi = maximum(x)
    x = float.(x)
    x .-= (lo + hi) / 2
    x ./= (hi - lo)
end

function center_and_scale(layout::Vector{<:Tuple})
    x, y = center_and_scale.(invert(layout))
    x .*= 2
    collect(zip(x, y))
end

function build_layout(n_layer, n_per_layer)
    x = (1 + n_per_layer) / 2
    [
        [(0, 0), (-x, -0.3), (x, -0.3)];
        grid_layout(n_layer, n_per_layer, true);
        grid_layout(n_layer, n_per_layer, false)
    ] |> center_and_scale
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

function sample_trial(rdist; n_layer = 3, n_per_layer = 6)
    graph, outcomes = build_graph(n_layer, n_per_layer)
    rewards = zeros(Int, nv(graph))
    rewards[outcomes] .= rand(rdist, length(outcomes))
    layout = build_layout(n_layer, n_per_layer)

    graph = map(x -> x .- 1, neighbor_list(graph))
    (;graph, rewards, layout, start=0)
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

function make_trials(; )
    rdist = exponential_rewards(8)
    practice = [sample_trial(rdist, n_layer=2, n_per_layer=4) for i in 1:20]
    mask = map(!isequal(0), practice[1].rewards)
    practice[1].rewards[mask] .= rdist

    (;
        # intro = [sample_problem(;graph = neighbor_list(intro_graph(n)), start=1, kws..., rewards=zeros(n))],
        # vary_transition = [sample_problem(;kws...)],
        # practice_revealed = [sample_problem(;kws...) for i in 1:2],
        # intro_hover = [sample_problem(;kws...)],
        # practice_hover = [sample_problem(;kws...) for i in 1:2],
        practice,
        main = [sample_trial(rdist) for i in 1:100],
    )
end

# t = make_trials().main[1]
# graph = map(x -> x .+ 1, t.graph)
# prob = Problem(graph, t.rewards, t.start+1, -1)

# # %% --------


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
n_subj = 30  # better safe than sorry
Random.seed!(hash(version))
subj_trials = repeatedly(make_trials, n_subj)

# %% --------

points_per_cent = 2

dest = "config/$(version)"
rm(dest, recursive=true, force=true)
mkpath(dest)
foreach(enumerate(subj_trials)) do (i, trials)
    parameters = (;)
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
