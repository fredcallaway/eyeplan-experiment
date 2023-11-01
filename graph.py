from psychopy import core, visual, gui, data, event
import numpy as np
MOUSE = event.Mouse()

def move_towards(pos, dest, dist):
    total = np.linalg.norm(pos - dest)
    frac = dist / total
    return (1 - frac) * pos + frac * dest

def angle(p1, p2):
    x1, y1 = (1, 0)
    x2, y2 = p2 - p1
    dot = x1*x2 + y1*y2
    det = x1*y2 - y1*x2
    θ = np.arctan2(det, dot)
    return θ * 180 / np.pi


class Graphics(object):
    def __init__(self, win):
        self.win = win

    def circle(self, pos, r=.05, **kws):
        return visual.Circle(self.win, radius=r, pos=pos, lineColor='black', lineWidth=10, autoDraw=True, **kws)

    def line(self, start, end, **kws):
        return visual.line.Line(self.win, start=start, end=end, lineColor='black', lineWidth=10, autoDraw=True, **kws)

    def text(self, text, pos=(0,0), **kws):
        return visual.TextStim(self.win, text, pos=pos, autoDraw=True, height=.03, color='black', **kws)

    def arrow(self, c0, c1):
        self.line(c0.pos, c1.pos, depth=2)
        vertices = .01 * np.array([[-1, -2], [1, -2], [0, 0]])
        visual.ShapeStim(self.win, vertices=vertices, autoDraw=True, fillColor='black',
                         pos=move_towards(c1.pos, c0.pos, c1.radius),
                         ori=90-angle(c0.pos, c1.pos))

class Graph(object):
    """Graph navigation interface"""
    def __init__(self, win, graph, rewards, start, layout, **kws):
        self.win = win
        self.gfx = Graphics(win)
        self.graph = graph
        self.rewards = rewards
        self.start = start
        self.layout = layout
        self.current_state = None
        self.build_graph()
        self.set_state(self.start)


    def build_graph(self):
        self.win.clearAutoDraw()
        self.nodes = nodes = []
        for i, (x, y) in enumerate(self.layout):
            nodes.append(self.gfx.circle(0.8 * np.array([x, y]), name=i))

        self.reward_labels = []
        for i, n in enumerate(self.nodes):
            lab = str(int(self.rewards[i])) if self.rewards[i] else ''
            self.reward_labels.append(self.gfx.text(lab, n.pos))

        for i, js in enumerate(self.graph):
            for j in js:
                self.gfx.arrow(nodes[i], nodes[j])

    def get_click(self):
        if MOUSE.getPressed()[0]:
            pos = MOUSE.getPos()
            for n in self.nodes:
                if n.contains(pos):
                    return n

    def set_state(self, s):
        if self.current_state is not None:
            self.nodes[self.current_state].fillColor = 'white'

        self.current_state = s
        self.reward_labels[s].text = ''
        self.nodes[s].fillColor = '#1B79FF'

    def click(self, s):
        print('clicked!', s)
        if s in self.graph[self.current_state]:
            self.set_state(s)

    def done(self):
        return len(self.graph[self.current_state]) == 0

    def run(self):
        print('start trial')
        while True:
            clicked = self.get_click()
            if clicked is not None:
                self.click(int(clicked.name))

            self.win.flip()
            if self.done():
                print('done!')
                return
