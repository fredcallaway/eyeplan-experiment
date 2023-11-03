from psychopy import core, visual, gui, data, event
import numpy as np
import logging

wait = core.wait

from graphics import Graphics

def reward_string(r):
    return f'{int(r):+}' if r else ''

def distance(p1, p2):
    (x1, y1), (x2, y2) = (p1, p2)
    return np.sqrt((x1 - x2)**2 + (y1 - y2)**2)

class GraphTrial(object):
    """Graph navigation interface"""
    def __init__(self, win, graph, rewards, start, layout, eyelink=None, pos=(0, 0), **kws):
        self.win = win
        self.gfx = Graphics(win)
        self.graph = graph
        self.rewards = list(rewards)
        self.start = start
        self.layout = layout
        self.current_state = None
        self.eyelink = eyelink
        self.fixated = None
        self.fix_verified = None
        self.data = {
            "trial": {
                "graph": graph,
                "rewards": rewards,
                "start": start,
                # layout
            },
            "events": []
        }
        self.pos = pos
        self.mouse = event.Mouse()

    def log(self, event, info={}):
        time = core.getTime()

        logging.debug(f'GraphTrial.log {time:3.3f} {event}' + ', '.join(f'{k} = {v}' for k, v in info.items()))
        self.data["events"].append({
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
        self.nodes[s].fillColor = '#1B79FF'

        if self.current_state is not None:  # not initial
            self.nodes[self.current_state].fillColor = 'white'
            lab = self.reward_labels[s]
            lab.color = 'white'
            # lab.bold = True
            for p in self.gfx.animate(.1):
                lab.setHeight(0.03 + p * 0.02)
            for p in self.gfx.animate(.2):
                lab.setHeight(0.05 - p * 0.05)
                lab.setOpacity(1-p)
            lab.autoDraw = False

        self.current_state = s


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

    def gaze_contingency(self):
        gaze = self.eyelink.gaze_position()
        visual.Circle(self.win, radius=.01, pos=gaze, color='red',).draw()

        for i in range(len(self.nodes)):
            if distance(gaze, self.nodes[i].pos) < .1:
                self.fixated = i
                self.fix_verified = core.getTime()

        if self.fixated is not None and core.getTime() - self.fix_verified > .5:
            self.fixated = None

        for i in range(len(self.nodes)):
            self.reward_labels[i].setOpacity(int(i == self.fixated))

    def run(self, one_step=False):
        if self.eyelink:
            self.log('drift check')
            self.eyelink.drift_check()
            self.log('start recording')
            self.eyelink.start_recording()
        self.log('start')
        if not hasattr(self, 'nodes'):
            self.show()
        if self.current_state is None:
            self.set_state(self.start)

        while True:
            clicked = self.get_click()
            if clicked is not None and clicked in self.graph[self.current_state]:
                self.set_state(clicked)

                if one_step:
                    self.win.flip()
                    return
            if self.eyelink:
                self.gaze_contingency()

            self.win.flip()
            if self.is_done():
                self.log('done')
                wait(.3)
                return self.fade_out()


