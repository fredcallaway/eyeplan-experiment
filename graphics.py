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