from psychopy import core, visual, gui, data, event
import numpy as np
import logging
import json
from eyetracking import height2pix

wait = core.wait

from graphics import Graphics, FRAME_RATE

def reward_string(r):
    return f'{int(r):+}' if r else ''

def distance(p1, p2):
    (x1, y1), (x2, y2) = (p1, p2)
    return np.sqrt((x1 - x2)**2 + (y1 - y2)**2)

class GraphTrial(object):
    """Graph navigation interface"""
    def __init__(self, win, graph, rewards, start, layout, time_limit=None, gaze_contingent=False, eyelink=None, pos=(0, 0), **kws):
        self.win = win
        self.graph = graph
        self.rewards = list(rewards)
        self.start = start
        self.layout = layout
        self.frames_left = self.total_frames = round(FRAME_RATE * time_limit) if time_limit else None
        self.gaze_contingent = gaze_contingent

        self.eyelink = eyelink
        self.pos = pos

        self.disable_click = False
        self.score = 0
        self.current_state = None
        self.fixated = None
        self.fix_verified = None
        self.data = {
            "trial": {
                "graph": graph,
                "rewards": rewards,
                "start": start,
                "time_limit": time_limit,
                # layout
            },
            "events": []
        }
        self.gfx = Graphics(win)
        self.mouse = event.Mouse()
        self.done = False

    def log(self, event, info={}):
        time = core.getTime()
        logging.debug(f'GraphTrial.log {time:3.3f} {event} ' + ', '.join(f'{k} = {v}' for k, v in info.items()))
        datum = {
            'time': time,
            'event': event,
            **info
        }
        self.data["events"].append(datum)
        if self.eyelink:
            self.eyelink.message(json.dumps(datum), log=False)


    def show(self):
        # self.win.clearAutoDraw()
        if self.gfx.objects:
            self.gfx.show()
            if self.gaze_contingent:
                self.gaze_contingency()
            return

        self.nodes = nodes = []
        for i, (x, y) in enumerate(self.layout):
            nodes.append(self.gfx.circle(0.8 * np.array([x, y]), name=i))

        self.reward_labels = []
        self.reward_unlabels = []
        for i, n in enumerate(self.nodes):
            self.reward_labels.append(self.gfx.text(reward_string(self.rewards[i]), n.pos))
            ul = self.gfx.text('?', n.pos, opacity=0)
            self.reward_unlabels.append(ul)

        self.arrows = {}
        for i, js in enumerate(self.graph):
            for j in js:
                self.arrows[(i, j)] = self.gfx.arrow(nodes[i], nodes[j])


        if self.total_frames is not None:
            self.timer_wrap = self.gfx.rect((0.5,-0.45), .02, 0.9, anchor='bottom', color=-.1)
            self.timer = self.gfx.rect((0.5,-0.45), .02, 0.9, anchor='bottom', color=-.2)
        else:
            self.timer = None

        self.mask = self.gfx.rect((.1,0), 1.1, 1, color='gray', opacity=0)
        self.gfx.shift(*self.pos)
        if self.gaze_contingent:
            self.gaze_contingency()

    def hide(self):
        self.gfx.clear()

    def shift(self, x, y):
        self.gfx.shift(x, y)
        self.pos = np.array(self.pos) + [x, y]


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
        lab = self.reward_labels[s]
        self.score += self.rewards[s]
        prev = self.current_state


        self.current_state = s
        if len(self.graph[self.current_state]) == 0:
            self.done = True

        if prev is not None and prev != s:  # not initial
            self.nodes[prev].fillColor = 'white'
            lab.color = 'white'
            # lab.bold = True
            for p in self.gfx.animate(.1):
                lab.setHeight(0.03 + p * 0.02)
                self.tick()
            for p in self.gfx.animate(.2):
                lab.setHeight(0.05 - p * 0.05)
                lab.setOpacity(1-p)
                self.tick()

        lab.setText('')
        self.reward_unlabels[s].setText('')

    def click(self, s):
        if s in self.graph[self.current_state]:
            self.set_state(s)

    def is_done(self):
        return len(self.graph[self.current_state]) == 0

    def fade_out(self):
        for p in self.gfx.animate(.2):
            self.mask.setOpacity(p)
            self.win.flip()
        self.gfx.clear()
        self.win.flip()
        wait(.3)

    def gaze_contingency(self):
        gaze = self.eyelink.gaze_position()
        # visual.Circle(self.win, radius=.01, pos=gaze, color='red',).draw()

        for i in range(len(self.nodes)):
            if distance(gaze, self.nodes[i].pos) < .08:
                if self.fixated != i:
                    self.log('show state', {'state': i})
                self.fixated = i
                self.fix_verified = core.getTime()

        if self.fixated is not None and core.getTime() - self.fix_verified > .5:
            self.log('hide state', {'state': self.fixated})
            self.fixated = None

        for i in range(len(self.nodes)):
            fixated = i == self.fixated
            self.reward_labels[i].setOpacity(float(fixated))
            self.reward_unlabels[i].setOpacity(float(not fixated))

    def check_click(self):
        if self.disable_click:
            return
        clicked = self.get_click()
        if clicked is not None and clicked in self.graph[self.current_state]:
            self.set_state(clicked)
            return True

    def highlight_current_edges(self):
        for (i, j), arrow in self.arrows.items():
            if i == self.current_state:
                arrow.setColor('#FFC910')
                arrow.objects[0].setDepth(1)  # make sure the line is on top
                self.nodes[j].setLineColor('#FFC910')
            else:
                arrow.setColor('black')
                arrow.objects[0].setDepth(2)
                self.nodes[j].setLineColor('black')

    def tick(self):
        if self.frames_left is not None and self.frames_left >= 0:
            self.frames_left -= 1
            p = (self.frames_left / self.total_frames)
            self.timer.setHeight(0.9 * p)
            if self.frames_left < 3 * FRAME_RATE:
                p2 = self.frames_left / (3 * FRAME_RATE)
                original = -.2 * np.ones(3)
                red = np.array([1, -1, -1])
                self.timer.setColor(p2 * original + (1-p2) * red)
        return self.win.flip()

    def do_timeout(self):
        logging.info('timeout')
        for i in range(3):
            self.timer_wrap.setColor('red'); self.win.flip()
            wait(0.3)
            self.timer_wrap.setColor(-.2); self.win.flip()
            wait(0.3)

        # random choices
        while not self.done:
            self.set_state(np.random.choice(self.graph[self.current_state]))
            core.wait(.5)

    def start_recording(self):
        self.log('drift check')
        self.eyelink.drift_check(self.pos)
        self.eyelink.start_recording()
        self.log('start recording')

    def practice_gazecontingent(self, timeout=15):
        assert self.eyelink
        self.start_recording()
        self.show()
        self.set_state(self.start)
        self.log('node positions', {
            'node_positions': [height2pix(self.win, n.pos) for n in self.nodes]
        })

        start_time = self.tick()
        self.log('start', {'flip_time': start_time})
        fixated = set()
        while len(fixated) != len(self.nodes):
            self.gaze_contingency()
            fixated.add(self.fixated)
            self.tick()
            if core.getTime() > start_time + timeout:
                return 'timeout'

        self.log('done')
        self.eyelink.stop_recording()
        wait(.3)
        self.fade_out()
        return 'success'

    def run(self, one_step=False, stop_on_space=True, highlight_edges=False):
        if self.eyelink:
            self.start_recording()
        self.show()
        if self.eyelink:
            self.log('node positions', {
                'node_positions': [height2pix(self.win, n.pos) for n in self.nodes]
            })

        if self.current_state is None:
            self.set_state(self.start)

        start_time = self.tick()
        self.log('start', {'flip_time': start_time})

        while not self.done:
            moved = self.check_click()
            if moved and one_step:
                return
            if self.gaze_contingent:
                self.gaze_contingency()
            if highlight_edges:
                self.highlight_current_edges()
            if not self.done and self.frames_left is not None and self.frames_left <= 0:
                self.do_timeout()
            self.tick()

        self.log('done')
        if self.eyelink:
            self.eyelink.stop_recording()
        wait(.3)
        return self.fade_out()


