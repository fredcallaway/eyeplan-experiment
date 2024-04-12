using Graphs
using Random
using Memoize

model_dir = "../model/"
include("$model_dir/problem.jl")
include("$model_dir/utils.jl")

neighbor_list(sgraph) = neighbors.(Ref(sgraph), vertices(sgraph))

@memoize function directed_binary_tree(k)
    t = binary_tree(k)
    g = DiGraph(nv(t))
    for e in edges(t)
        add_edge!(g, e)
    end
    g
end

@memoize function tree_levels(g)
    levels = Vector{Int}[]
    function rec(i, d)
        if length(levels) < d
            push!(levels, Int[])
        end
        push!(levels[d], i)
        for j in outneighbors(g, i)
            rec(j, d+1)
        end
    end
    rec(1, 1)
    levels
end

@memoize descendants(g, i) = findall(!isequal(0), bfs_parents(g, i))

function sample_perm(k)
    for i in 1:1000
        perm = randperm(k)
        bad = any(sliding_window(perm, 2)) do (a, b)
            d = abs(a - b)
            d == 1 || d > 5
        end
        !bad && return perm
    end
    error("Can't sample a perm")
end

function scrambled_tree_layout(g; depth=3)
    layout = buchheim(g)
    levels = tree_levels(g)
    for (i, level) in enumerate(levels[depth:end])
        for section in chunk(level, 2^i)
            layout[section] .= layout[shuffle(section)]
        end
    end
    layout[descendants(g, 2)] .-= Point(.5, 0)
    layout[descendants(g, 3)] .+= Point(.5, 0)
    layout
end

function center_and_scale(x::Vector{<:Real})
    lo = minimum(x)
    hi = maximum(x)
    x = float.(x)
    x .-= (lo + hi) / 2
    x ./= (hi - lo)
end

function center_and_scale(layout::Vector{<:Point})
    x, y = center_and_scale.(invert(layout))
    x .*= 2
    collect(zip(x, y))
end


function sample_trial(rdist; k=5)
    g = directed_binary_tree(k)
    outcomes = tree_levels(g)[end]
    rewards = zeros(Int, nv(g))
    rewards[outcomes] .= rand(rdist, length(outcomes))
    layout = scrambled_tree_layout(g) |> center_and_scale

    graph = map(x -> x .- 1, neighbor_list(g))
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
    practice = [sample_trial(rdist; k=4) for i in 1:20]
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
