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
    def __init__(self, win, graph, rewards, start, layout, time_limit=None, start_mode=None,
                 eyelink=None, gaze_contingent=False, gaze_tolerance=1.2, fixation_lag = .5, show_gaze=False,
                 pos=(0, 0), space_start=True, max_score=None, **kws):
        self.win = win
        self.graph = graph
        self.rewards = list(rewards)
        self.start = start
        self.layout = layout
        self.time_limit = time_limit
        if start_mode is None:
            start_mode = 'drift_check' if eyelink else 'space'
        self.start_mode = start_mode

        self.eyelink = eyelink
        self.gaze_contingent = gaze_contingent
        self.gaze_tolerance = gaze_tolerance
        self.fixation_lag = fixation_lag
        self.show_gaze = show_gaze

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
                "gaze_contingent": gaze_contingent,
                "gaze_tolerance": gaze_tolerance,
                "fixation_lag": fixation_lag
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
        logging.debug(f'{self.__class__.__name__}.log {time:3.3f} {event} ' + ', '.join(f'{k} = {v}' for k, v in info.items()))
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
            nodes.append(self.gfx.circle(0.7 * np.array([x, y]), name=f'node{i}', r=.03))
        self.data["trial"]["node_positions"] = [height2pix(self.win, n.pos) for n in self.nodes]

        self.reward_labels = [self.gfx.text('', n.pos, name=f'lab{i}') for i, n in enumerate(self.nodes)]
        self.update_node_labels()

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

        if self.show_gaze:
            self.gaze_dot = self.gfx.circle((0,0), .005, color='red', lineWidth=1, lineColor="red")

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
            for (i, n) in enumerate(self.nodes):
                if n.contains(pos):
                    return i

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

    def node_label(self, i):
        if self.gaze_contingent:
            if i == self.fixated:
                return reward_string(self.rewards[i])
            elif self.rewards[i]:
                return '?'
            else:
                return ''
        else:
            return reward_string(self.rewards[i])

    def update_node_labels(self):
        for i in range(len(self.nodes)):
            self.set_node_label(i, self.node_label(i))

    def set_node_label(self, i, new):
        old = self.reward_labels[i].text
        if old != new:
            logging.debug(f'Changing reward_label[%s] from %s to %s', i, old, new)
            self.reward_labels[i].text = new


    def update_fixation(self):
        if not self.eyelink:
            return
        gaze = self.eyelink.gaze_position()
        if self.show_gaze:
            self.gaze_dot.setPos(gaze)
        self.last_fixated = self.fixated
        # visual.Circle(self.win, radius=.01, pos=gaze, color='red',).draw()

        for i in range(len(self.nodes)):
            if distance(gaze, self.nodes[i].pos) < self.gaze_tolerance * self.nodes[i].radius:
                if self.fixated != i:
                    self.log('fixate state', {'state': i})
                self.fixated = i
                self.fix_verified = core.getTime()
                break

        if self.fixated is not None and core.getTime() - self.fix_verified > self.fixation_lag:
            self.log('unfixate state', {'state': self.fixated})
            self.fixated = None

        if self.gaze_contingent and self.last_fixated != self.fixated:
            self.update_node_labels()

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
        self.last_flip = t = self.win.flip()
        self.data["mouse"].append(self.mouse.getPos())
        self.data["flips"].append(t)
        return t

    def do_timeout(self):
        self.log('timeout')
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
        self.log('start recording')
        self.eyelink.start_recording()

    def run(self, one_step=False, highlight_edges=False, stop_on_x=False):
        if self.start_mode == 'drift_check':
            self.log('begin drift_check')
            self.status = self.eyelink.drift_check(self.pos)
        elif self.start_mode == 'fixation':
            self.log('begin fixation')
            self.status = self.eyelink.fake_drift_check(self.pos)
        elif self.start_mode == 'space':
            self.log('begin space')
            visual.TextStim(self.win, 'press space to start', pos=self.pos, color='white', height=.035).draw()
            self.win.flip()
            event.waitKeys(keyList=['space'])

        self.log('initialize status', {'status': self.status})

        if self.status in ('abort', 'recalibrate'):
            return self.status

        if self.eyelink:
            self.start_recording()

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
            if 'x' in keys or 'c' in keys:
                logging.warning('press x')
                self.log('press x')
                self.status = 'recalibrate'
                if stop_on_x:
                    return self.status
            elif 'a' in keys:
                logging.warning('press a')
                self.log('press a')
                self.status = 'abort'
            self.tick()

        self.log('done')
        logging.info("end trial " + jsonify(self.data["events"]))
        if self.eyelink:
            self.eyelink.stop_recording()
        wait(.3)
        self.fade_out()
        return self.status




class CalibrationTrial(GraphTrial):
    """docstring for CalibrationTrial"""
    all_failures = np.zeros(11)  # across separate runs ASSUME graph doesn't change

    def __init__(self, *args, saccade_time=.5, n_success=2, n_fail=3, target_delay=.2, **kwargs):
        kwargs['gaze_contingent'] = True
        kwargs['fixation_lag'] = .1
        kwargs['time_limit'] = None

        self.saccade_time = saccade_time
        self.n_success = n_success
        self.n_fail = n_fail
        self.target_delay = target_delay

        self.target = None
        self.last_target = None
        self.arrow = None
        self.result = None

        super().__init__(*args, **kwargs)

    def node_label(self, i):
        return {
            # self.completed: ''
            # self.fixated: '',
            self.target: 'O',
        }.get(i, '')

    def do_timeout(self):
        self.log('timeout')
        logging.info('timeout')
        self.result = 'timeout'

    def draw_arrow(self):
        if self.arrow is not None:
            self.arrow.setAutoDraw(False)
        if self.last_target is not None:
            self.arrow = self.gfx.arrow(self.nodes[self.last_target], self.nodes[self.target])

    def new_target(self):
        initial = self.target is None
        self.last_target = self.target

        if initial:
            self.target = np.random.choice(len(self.successes))
        else:
            p = np.exp(
                -5 * self.successes +
                self.all_failures[:len(self.successes)]
            )
            p[self.target] = 0
            p /= (sum(p) or 1)  # prevent divide by 0
            self.target = np.random.choice(len(p), p=p)

        self.target_time = 'flip'  # updated to be next flip time
        self.draw_arrow()
        self.update_node_labels()

    def tick(self):
        t = super().tick()
        if self.target_time == 'flip':
            self.target_time = t

    def run(self, timeout=15):
        assert self.eyelink
        # self.eyelink.drift_check(self.pos)
        self.start_recording()
        self.show()
        self.successes = np.zeros(len(self.nodes))
        self.failures = np.zeros(len(self.nodes))
        self.uncomplete = set(range(len(self.nodes)))
        self.new_target()
        self.start_time = self.tick()
        self.log('start', {'flip_time': self.start_time})

        self.win.mouseVisible = False

        self.target_time += 5  # extra time for first fixation
        while self.result is None:
            self.update_fixation()
            if 'x' in event.getKeys():  # cancel key
                self.log('cancel')
                self.result = 'cancelled'
                self.fade_out()
                return self.result

            elif self.last_flip > self.target_time + self.saccade_time:  # timeout
                self.log('timeout', {"state": self.target})
                self.failures[self.target] += 1
                self.all_failures[self.target] += 1

                self.set_node_label(self.target, 'X')
                lab = self.reward_labels[self.target]
                for p in range(FRAME_RATE):
                    lab.setOpacity(1 - (p // 10) % 2)
                    self.tick()
                wait(self.target_delay)
                lab.setOpacity(1)

                if sum(self.failures) == self.n_fail or self.failures[self.target] == 2:
                    self.result = 'failure'
                else:
                    self.new_target()

            elif self.fixated == self.target:  # fixated within time
                self.log('fixated target', {"state": self.target})
                self.successes[self.target] += 1

                lab = self.reward_labels[self.target]
                for p in self.gfx.animate(6/60):
                    lab.setHeight(0.03 + p * 0.02)
                    self.tick()
                for p in self.gfx.animate(12/60):
                    lab.setHeight(0.05 - p * 0.03)
                    lab.setOpacity(1-p)
                    self.tick()
                wait(self.target_delay)
                lab.setOpacity(1)

                if self.successes[self.target] == self.n_success:
                    self.uncomplete.remove(self.target)
                if self.uncomplete:
                    self.new_target()
                else:
                    self.result = 'success'

            # if not self.done and self.time_limit is not None and self.start_time + self.time_limit < core.getTime():
            #     self.do_timeout()


            t = self.tick()

        self.log('done')
        self.eyelink.stop_recording()
        wait(.3)
        self.fade_out()
        self.win.mouseVisible = True

        return self.result
