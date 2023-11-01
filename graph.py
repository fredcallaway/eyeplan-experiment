from psychopy import core, visual, gui, data, event
import numpy as np
wait = core.wait

FRAME_RATE = 60

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

def shift(obj, x, y):
    obj.setPos(obj.pos + np.array([x, y]))



class Graphics(object):
    def __init__(self, win):
        self.win = win
        self.objects = []

    def clear(self):
        for o in self.objects:
            o.autoDraw = False

    def circle(self, pos, r=.05, **kws):
        o = visual.Circle(self.win, radius=r, pos=pos, lineColor='black', lineWidth=10, autoDraw=True, **kws)
        self.objects.append(o)
        return o

    def line(self, start, end, **kws):
        o = visual.line.Line(self.win, start=start, end=end, lineColor='black', lineWidth=10, autoDraw=True, **kws)
        self.objects.append(o)
        return o

    def text(self, text, pos=(0,0), height=.03, color='black', **kws):
        o = visual.TextStim(self.win, text, pos=pos, autoDraw=True, height=height, color=color, **kws)
        self.objects.append(o)
        return o

    def arrow(self, c0, c1):
        self.line(c0.pos, c1.pos, depth=2)
        vertices = .01 * np.array([[-1, -2], [1, -2], [0, 0]])
        self.objects.append(visual.ShapeStim(self.win, vertices=vertices, autoDraw=True, fillColor='black',
                         pos=move_towards(c1.pos, c0.pos, c1.radius),
                         ori=90-angle(c0.pos, c1.pos)))

    def rect(self, pos, width, height, **kws):
        o = visual.Rect(self.win, width, height, pos=pos, autoDraw=True, **kws)
        self.objects.append(o)
        return o

    def animate(self, sec):
        total = round(sec * FRAME_RATE)
        for i in range(1,total+1):
            yield i / total
            self.win.flip()

    def shift(self, x=0, y=0):
        for o in self.objects:
            shift(o, x, y)


def reward_string(r):
    return f'{int(r):+}' if r else ''


class Graph(object):
    """Graph navigation interface"""
    def __init__(self, win, graph, rewards, start, layout, pos=(0, 0), **kws):
        self.win = win
        self.gfx = Graphics(win)
        self.graph = graph
        self.rewards = list(rewards)
        self.start = start
        self.layout = layout
        self.current_state = None
        self.data = []
        self.pos = pos
        self.mouse = event.Mouse()

    def log(self, event, info={}):
        time = core.getTime()
        print(f'{time:3.3f}', event, ', '.join(f'{k} = {v}' for k, v in info.items()))
        self.data.append({
            'time': time,
            'event': event,
            **info
        })

    def show(self):
        # self.win.clearAutoDraw()
        self.nodes = nodes = []
        for i, (x, y) in enumerate(self.layout):
            nodes.append(self.gfx.circle(0.8 * np.array([x, y]), name=i))

        self.reward_labels = []
        for i, n in enumerate(self.nodes):
            self.reward_labels.append(self.gfx.text(reward_string(self.rewards[i]), n.pos))

        for i, js in enumerate(self.graph):
            for j in js:
                self.gfx.arrow(nodes[i], nodes[j])

        self.mask = self.gfx.rect((0,0), 1, 1, color='gray', opacity=0)
        self.gfx.shift(*self.pos)

    def set_reward(self, s, r):
        self.rewards[s] = r
        self.reward_labels[s].text = reward_string(r)

    def get_click(self):
        if self.mouse.getPressed()[0]:
            pos = self.mouse.getPos()
            for n in self.nodes:
                if n.contains(pos):
                    return int(n.name)

    def set_state(self, s):
        self.log('visit', {'state': s})
        if self.current_state is not None:
            self.nodes[self.current_state].fillColor = 'white'

        self.current_state = s
        self.reward_labels[s].text = ''
        self.nodes[s].fillColor = '#1B79FF'

    def click(self, s):
        if s in self.graph[self.current_state]:
            self.set_state(s)

    def is_done(self):
        return len(self.graph[self.current_state]) == 0

    def fade_out(self):
        for p in self.gfx.animate(.2):
            self.mask.opacity = p
        self.gfx.clear()
        self.win.flip()
        wait(.3)

    def run(self, one_step=False):
        self.log('start')
        self.show()
        self.set_state(self.start)

        while True:
            clicked = self.get_click()
            if clicked is not None and clicked in self.graph[self.current_state]:
                self.set_state(clicked)
                if one_step:
                    self.win.flip()
                    return

            self.win.flip()
            if self.is_done():
                self.log('done')
                wait(.3)
                return self.fade_out()


