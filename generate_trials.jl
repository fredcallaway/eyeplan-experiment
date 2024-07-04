using Graphs
using Random
using Memoize
using NetworkLayout
Point = NetworkLayout.Point
model_dir = "../model/"
include("$model_dir/problem.jl")
include("$model_dir/utils.jl")

neighbor_list(sgraph) = neighbors.(Ref(sgraph), vertices(sgraph))

function directed_binary_tree(k)
    t = binary_tree(k)
    g = DiGraph(nv(t))
    for e in edges(t)
        add_edge!(g, e)
    end
    g
end

function tree_levels(g, i=1)
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
    rec(i, 1)
    levels
end

descendants(g, i) = findall(!isequal(0), bfs_parents(g, i))

function sample_perm(k)
    # return [mod1(i+1, k) for i in 1:k]
    k < 8 && return randperm(k)
    for i in 1:10000
        perm = randperm(k)
        good = all(zip(1:k, perm)) do (a, b)
            d = abs(a - b)
            1 < d < 5
        end
        good && return perm
    end
    error("Can't sample a perm")
end

function scramble(g)
    childs = outneighbors(g, 1)
    g1 = DiGraph(nv(g))
    for c in childs
        add_edge!(g1, 1, c)
        for c1 in outneighbors(g, c)
            add_edge!(g1, c, c1)
        end
        levels = tree_levels(g, c)[2:end]
        for (this_level, next_level) in sliding_window(levels, 2)
            perm = sample_perm(length(next_level))
            shuffled = Iterators.Stateful(next_level[perm])
            # @infiltrate length(perm) == 8
            for i in this_level
                # ASSUME BINARY
                add_edge!(g1, i, first(shuffled))
                add_edge!(g1, i, first(shuffled))
            end
        end
    end
    g1
end

function center_and_scale(x::Vector{<:Real})
    lo = minimum(x)
    hi = maximum(x)
    x = float.(x)
    x .-= (lo + hi) / 2
    x ./= (hi - lo)
end

function center_and_scale(layout::Vector{<:Point}; stretch=1.7)
    x, y = center_and_scale.(invert(layout))
    x .*= stretch
    collect(Point.(x, y))
end

function rotate(layout, clockwise=true)
    R = clockwise ? [0 1; -1 0] : [0 -1; 1 0]
    map(layout) do l
        Point2(R * l)
    end
end

function sample_trial(rdist; k=5)
    g = directed_binary_tree(k)
    layout = center_and_scale(build_layout(k))
    outcomes = tree_levels(g)[end]
    rewards = zeros(Int, nv(g))
    # rewards[outcomes] .= rand(rdist, length(outcomes))
    if k > 4
        n_per_side = length(outcomes) ÷ 2
        rewards[outcomes[1:n_per_side]] = sort(rand(rdist, n_per_side); rev=true)
        rewards[outcomes[n_per_side+1:end]] = sort(rand(rdist, n_per_side))
    else
        rewards[outcomes] = sort(rand(rdist, length(outcomes)))
    end

    graph = map(x -> x .- 1, neighbor_list(scramble(g)))
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
        practice_big = [sample_trial(rdist) for i in 1:20],
        main = [sample_trial(rdist) for i in 1:300],
    )
end


# %% --------

function build_layout(k; shape=:tall)
    g = directed_binary_tree(k)
    a, b, c, stretch = shape == :tall ? (1.6, 1.3, 3, 2.) : (1.4, 1.4, 5, 2.)

    if k > 4
        half = build_layout(k-1; shape)
        layout = fill(Point(0., 0.), nv(g))

        shift = Point(abs(half[end][2] / c), 0)

        layout[descendants(g, 2)] .= rotate(half) .- shift
        layout[descendants(g, 3)] .= rotate(half, false) .+ shift
        if shape == :tall
            rotate(layout)
        else
            layout
        end

    else
        layout = buchheim(g)

        for (level, nodes) in enumerate(tree_levels(g)[2:end])
            for i in nodes
                layout[i] = Point(a ^ level, b ^ level) * layout[i]
            end
        end
        layout
    end
end



using GraphMakie
include("$model_dir/figure.jl")
figure() do
    k = 5
    g = directed_binary_tree(k)
    layout = build_layout(k)

    # middle_nodes = vcat(tree_levels(g, 2)[2:end-1]...)

    # rand(Uniform(-0.75, -0.25)), rand(Uniform(-0.5, 0.5))
    # for i in middle_nodes
    #     layout[i] = Point(rand(Uniform(-0.75, -0.25)), rand(Uniform(-0.5, 0.5)))
    # end

    graphplot(scramble(g); layout, ilabels=vertices(g))
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
n_subj = 30  # better safe than sorry
Random.seed!(hash(version))
subj_trials = repeatedly(make_trials, n_subj)


points_per_cent = 2

dest = "config/$(version)"
rm(dest, recursive=true, force=true)
mkpath(dest)
conditions = [
    (;score_limit=480, force_rate=.2),
    (;score_limit=160, force_rate=.8),
]

foreach(enumerate(subj_trials)) do (i, trials)
    parameters = conditions[mod1(i, length(conditions))]
    write("$dest/$i.json", json((;parameters, trials)))
    println("$dest/$i.json")
end
