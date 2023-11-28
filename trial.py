from psychopy import core, visual, gui, data, event
import numpy as np
import logging
import json
from eyetracking import height2pix
from util import jsonify

wait = core.wait

from graphics import Graphics, FRAME_RATE

def reward_string(r):
    return f'{int(r):+}' if r else ''

def distance(p1, p2):
    (x1, y1), (x2, y2) = (p1, p2)
    return np.sqrt((x1 - x2)**2 + (y1 - y2)**2)

class GraphTrial(object):
    """Graph navigation interface"""
    def __init__(self, win, graph, rewards, start, layout, time_limit=None,
                 gaze_contingent=False, eyelink=None, pos=(0, 0), space_start=True, max_score=None, **kws):
        self.win = win
        self.graph = graph
        self.rewards = list(rewards)
        self.start = start
        self.layout = layout
        self.time_limit = time_limit
        self.gaze_contingent = gaze_contingent
        self.eyelink = eyelink
        self.pos = pos
        self.space_start = space_start
        self.max_score = max_score

        self.status = 'ok'
        self.start_time = None
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
                "gaze_contingent": gaze_contingent
            },
            "events": [],
            "flips": [],
            "mouse": [],
        }
        logging.info("begin trial " + jsonify(self.data["trial"]))
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
            self.eyelink.message(jsonify(datum), log=False)


    def show(self):
        # self.win.clearAutoDraw()
        if hasattr(self, 'nodes'):
            self.gfx.show()
            if self.gaze_contingent:
                self.update_fixation()
            return

        self.nodes = nodes = []
        for i, (x, y) in enumerate(self.layout):
            nodes.append(self.gfx.circle(0.7 * np.array([x, y]), name=i))
        self.data["trial"]["node_positions"] = [height2pix(self.win, n.pos) for n in self.nodes]

        self.reward_labels = []
        self.reward_unlabels = []
        for i, n in enumerate(self.nodes):
            self.reward_labels.append(self.gfx.text(reward_string(self.rewards[i]), n.pos))

        self.arrows = {}
        for i, js in enumerate(self.graph):
            for j in js:
                self.arrows[(i, j)] = self.gfx.arrow(nodes[i], nodes[j])


        if self.time_limit is not None:
            self.timer_wrap = self.gfx.rect((0.5,-0.45), .02, 0.9, anchor='bottom', color=-.1)
            self.timer = self.gfx.rect((0.5,-0.45), .02, 0.9, anchor='bottom', color=-.2)
        else:
            self.timer = None

        self.mask = self.gfx.rect((.1,0), 1.1, 1, color='gray', opacity=0)
        self.gfx.shift(*self.pos)
        if self.gaze_contingent:
            self.update_fixation()

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
            for p in self.gfx.animate(6/60):
                lab.setHeight(0.03 + p * 0.02)
                self.tick()
            for p in self.gfx.animate(12/60):
                lab.setHeight(0.05 - p * 0.05)
                lab.setOpacity(1-p)
                self.tick()

        lab.setText('')

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

    def update_fixation(self):
        if not self.eyelink:
            return
        gaze = self.eyelink.gaze_position()
        # visual.Circle(self.win, radius=.01, pos=gaze, color='red',).draw()

        for i in range(len(self.nodes)):
            if distance(gaze, self.nodes[i].pos) < 1.2 * self.nodes[i].radius:
                if self.fixated != i:
                    self.log('fixate state', {'state': i})
                self.fixated = i
                self.fix_verified = core.getTime()
                break

        if self.fixated is not None and core.getTime() - self.fix_verified > .5:
            self.log('unfixate state', {'state': self.fixated})
            self.fixated = None

        if self.gaze_contingent:
            for i in range(len(self.nodes)):
                if i == self.fixated:
                    lab = reward_string(self.rewards[i])
                elif self.rewards[i]:
                    lab = '?'
                else:
                    lab = ''
                self.reward_labels[i].text = lab

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
        if self.start_time is not None and self.time_limit is not None:
            time_left = self.start_time + self.time_limit - core.getTime()
            if time_left > 0:
                p = time_left / self.time_limit
                self.timer.setHeight(0.9 * p)
                if time_left < 3:
                    p2 = time_left / 3
                    original = -.2 * np.ones(3)
                    red = np.array([1, -1, -1])
                    self.timer.setColor(p2 * original + (1-p2) * red)
        t = self.win.flip()
        self.data["mouse"].append(self.mouse.getPos())
        self.data["flips"].append(t)
        return t

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

    def start_recording(self, drift_check=True):
        self.log('drift check')
        if drift_check:
            self.eyelink.drift_check(self.pos)
        self.eyelink.start_recording()
        self.log('start recording')

    def practice_gazecontingent(self, callback, timeout=15):
        assert self.eyelink
        self.start_recording(drift_check=False)
        self.show()
        self.set_state(self.start)

        self.start_time = self.tick()
        self.log('start', {'flip_time': self.start_time})
        fixated = set()
        done = False
        result = None
        while result is None:
            self.update_fixation()
            fixated.add(self.fixated)
            if not done and len(fixated) == len(self.nodes):
                done = True
                callback()
            self.tick()

            if (not done) and core.getTime() > self.start_time + timeout:
                result = 'timeout'

            pressed = event.getKeys()
            if 'x' in pressed:
                logging.info('press x')
                result = 'cancelled'
            if done and 'space' in pressed:
                result = 'success'

        self.log('done')
        self.log('practice_gazecontingent result', {"result": result})
        self.eyelink.stop_recording()
        wait(.3)
        self.fade_out()
        return result

    def run(self, one_step=False, stop_on_space=True, highlight_edges=False):
        if self.eyelink:
            self.start_recording()
        elif self.space_start:
            visual.TextStim(self.win,  'press space to start', pos=self.pos, color='white', height=.035).draw()
            self.win.flip()
            event.waitKeys(keyList=['space'])

        self.show()

        if self.current_state is None:
            self.set_state(self.start)

        self.start_time = self.tick()
        self.log('start', {'flip_time': self.start_time})

        while not self.done:
            moved = self.check_click()
            if moved and one_step:
                return
            self.update_fixation()
            if highlight_edges:
                self.highlight_current_edges()
            if not self.done and self.time_limit is not None and self.start_time + self.time_limit < core.getTime():
                self.do_timeout()

            keys = event.getKeys()
            if 'x' in keys:
                logging.warning('press x')
                self.log('press x')
                self.status = 'x'
            elif 'a' in keys:
                logging.warning('press a')
                self.log('press a')
                self.status = 'a'
            self.tick()

        self.log('done')
        logging.info("end trial " + jsonify(self.data["events"]))
        if self.eyelink:
            self.eyelink.stop_recording()
        wait(.3)
        return self.fade_out()


