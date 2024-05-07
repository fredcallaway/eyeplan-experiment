from psychopy import core, visual, gui, data, event
import numpy as np
import logging
import json
from eyetracking import height2pix
from util import jsonify
import random

wait = core.wait

COLOR_PLAN = '#F2384A'
COLOR_ACT = '#126DEF'

COLOR_LOSS = '#9E0002'
COLOR_WIN =  '#0F7003'

KEY_SWITCH = 's'
KEY_SELECT = 't'

from graphics import Graphics, FRAME_RATE

def reward_color(r):
    return COLOR_WIN if r > 0 else COLOR_LOSS

def reward_string(r):
    return f'{int(r):+}' if r else ''

def distance(p1, p2):
    (x1, y1), (x2, y2) = (p1, p2)
    return np.sqrt((x1 - x2)**2 + (y1 - y2)**2)

class GraphTrial(object):
    """Graph navigation interface"""
    def __init__(self, win, graph, rewards, start, layout, pos=(0, 0), start_mode=None, max_score=None, stop_on_x=False,
                 plan_time=None, act_time=None,
                 images=None, description=None, targets=None, value=None,
                 initial_stage='planning', hide_states=False, hide_rewards_while_acting=True, hide_edges_while_acting=True,
                 eyelink=None, **kws):
        self.win = win
        self.graph = graph
        self.rewards = list(rewards)
        self.start = start
        self.layout = layout
        self.pos = pos
        self.start_mode = start_mode or ('drift_check' if eyelink else 'space')
        self.max_score = max_score
        self.stop_on_x = stop_on_x

        self.plan_time = plan_time
        self.act_time = act_time
        self.current_time = None
        self.start_time = None
        self.end_time = None

        self.images = images
        self.description = description
        self.targets = targets
        self.value = value

        self.stage = initial_stage
        self.hide_states = hide_states
        self.hide_rewards_while_acting = hide_states or hide_rewards_while_acting
        self.hide_edges_while_acting = hide_edges_while_acting

        self.eyelink = eyelink

        self.status = 'ok'
        self.disable_click = False
        self.score = 0
        self.current_state = None
        self.fixated = None
        self.fix_verified = None
        self.data = {
            "trial": {
                "kind": self.__class__.__name__,
                "graph": graph,
                "rewards": rewards,
                "description": description,
                "targets": targets,
                "value": value,
                "initial_stage": initial_stage,
                "hide_states": hide_states,
                "hide_rewards_while_acting": hide_rewards_while_acting,
                "hide_edges_while_acting": hide_edges_while_acting,

                "start": start,
                "plan_time": plan_time,
                "act_time": act_time,
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

    def description_text(self):
        points = 'point' if self.value == 1 else 'points'
        return f'{self.value} {points} for items matching: {self.description}'

    def show(self):
        if hasattr(self, 'nodes'):
            self.gfx.show()
            return

        self.nodes = nodes = []
        self.node_images = []
        for i, (x, y) in enumerate(self.layout):
            pos = 0.7 * np.array([x, y])
            nodes.append(self.gfx.circle(pos, name=f'node{i}', r=.05))
            if i > 0 and self.images is not None:
                self.node_images.append(self.gfx.image(pos, self.images[i-1], size=.08, autoDraw=not self.hide_states))
            else:
                self.node_images.append(None)
        self.data["trial"]["node_positions"] = [height2pix(self.win, n.pos) for n in self.nodes]

        self.arrows = {}
        for i, js in enumerate(self.graph):
            for j in js:
                self.arrows[(i, j)] = self.gfx.arrow(nodes[i], nodes[j])

        if self.plan_time is not None or self.act_time is not None:
            self.timer_wrap = self.gfx.rect((0.5,-0.45), .02, 0.9, anchor='bottom', color=-.1)
            self.timer = self.gfx.rect((0.5,-0.45), .02, 0.9, anchor='bottom', color=-.2)
        else:
            self.timer = None

        self.mask = self.gfx.rect((.1,0), 1.1, 1, color='gray', opacity=0)
        self.gfx.shift(*self.pos)

        if self.description:
            self.desc = self.gfx.text(self.description_text(), pos=(0, .45), color="white")
        else:
            self.desc = None

    def hide(self):
        self.gfx.clear()

    def shift(self, x, y):
        self.gfx.shift(x, y)
        self.pos = np.array(self.pos) + [x, y]


    def get_click(self):
        if self.mouse.getPressed()[0]:
            pos = self.mouse.getPos()
            for (i, n) in enumerate(self.nodes):
                if n.contains(pos):
                    return i

    def set_state(self, s):
        self.log('visit', {'state': s})
        self.nodes[s].fillColor = COLOR_PLAN if self.stage == 'planning' else COLOR_ACT
        self.score += self.rewards[s]
        prev = self.current_state

        self.current_state = s
        if len(self.graph[self.current_state]) == 0:
            self.done = True

        if prev is not None and prev != s:  # not initial
            self.nodes[prev].fillColor = 'white'
            txt = visual.TextStim(self.win, reward_string(self.rewards[s]),
                pos=self.nodes[s].pos + np.array([.06, .06]),
                bold=True, height=.04, color=reward_color(self.rewards[s]))
            txt.setAutoDraw(True)
            if self.node_images[s]:
                self.node_images[s].setAutoDraw(True)
            self.win.flip()
            txt.setAutoDraw(False)
            core.wait(.5)
            self.node_images[s].setAutoDraw(False)


    def click(self, s):
        if s in self.graph[self.current_state]:
            self.set_state(s)

    def is_done(self):
        return len(self.graph[self.current_state]) == 0

    def fade_out(self):
        self.mask.setAutoDraw(False); self.mask.setAutoDraw(True)  # ensure on top
        for p in self.gfx.animate(.3):
            self.mask.setOpacity(p)
            self.win.flip()
        self.gfx.clear()
        self.win.flip()
        wait(.3)

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
                arrow.setAutoDraw(False); arrow.setAutoDraw(True)  # on top
                arrow.setColor('#FFC910')
                self.nodes[j].setLineColor('#FFC910')
            else:
                arrow.setColor('black')
                self.nodes[j].setLineColor('black')

    def get_key_move(self):
        choices = []
        arrows = []
        for (i, j), arrow in self.arrows.items():
            if i == self.current_state:
                arrow.setAutoDraw(False); arrow.setAutoDraw(True)  # on top
                arrows.append(arrow)
                choices.append(j)
            else:
                if self.hide_edges_while_acting:
                    arrow.setAutoDraw(False)
                else:
                    arrow.setColor('black')

        idx = random.randint(0, len(choices) - 1)
        arrows[idx].setColor('#FFC910')
        self.win.flip()

        while True:
            pressed = event.waitKeys(keyList=[KEY_SELECT, KEY_SWITCH])
            if KEY_SELECT in pressed:
                if self.hide_edges_while_acting:
                    for arrow in arrows:
                        arrow.setAutoDraw(False)
                self.set_state(choices[idx])
                return True
            else:
                arrows[idx].setColor('black')
                idx = (idx + 1) % len(choices)
                arrows[idx].setColor('#FFC910')
                self.win.flip()

    def tick(self):
        self.current_time = core.getTime()
        if self.end_time is not None: # TODO
            time_left = self.end_time - self.current_time
            if time_left > 0:
                p = time_left / (self.end_time - self.start_time)
                self.timer.setHeight(0.9 * p)
                if self.stage == 'acting' and time_left < 3:
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
            self.set_state(random.choice(self.graph[self.current_state]))
            core.wait(.5)

    def start_recording(self):
        self.log('start recording')
        self.eyelink.start_recording()
        # TODO: draw reference
        # left = int(scn_width/2.0) - 60
        # top = int(scn_height/2.0) - 60
        # right = int(scn_width/2.0) + 60
        # bottom = int(scn_height/2.0) + 60
        # draw_cmd = 'draw_filled_box %d %d %d %d 1' % (left, top, right, bottom)
        # el_tracker.sendCommand(draw_cmd)


    def run_planning(self):
        self.log('start planning')
        self.stage = 'planning'
        self.nodes[self.current_state].fillColor = COLOR_PLAN
        self.start_time = self.current_time = core.getTime()
        self.end_time = None if self.plan_time is None else self.start_time + self.plan_time

        while not self.done:
            if self.end_time is not None and self.current_time > self.end_time:
                self.log('timeout planning')
                self.done = True
                break

            keys = event.waitKeys(keyList=[KEY_SWITCH, 'x', 'c', 'a'])

            if KEY_SWITCH in keys:
                self.log('end planning')
                break

            elif 'x' in keys or 'c' in keys:
                logging.warning('press x')
                self.log('press x')
                self.status = 'recalibrate'
                if self.stop_on_x:
                    self.done = True
                    break
            elif 'a' in keys:
                logging.warning('press a')
                self.log('press a')
                self.status = 'abort'
            self.tick()

        self.fixated = None
        self.win.flip()

    def hide_rewards(self):
        for img in self.node_images:
            if img:
                img.setAutoDraw(False)
        if self.desc is not None:
            self.desc.setAutoDraw(False)

    def hide_edges(self):
        for a in self.arrows.values():
            a.setAutoDraw(False)
        # for i in range(len(self.nodes)):
        #     self.set_node_label(i, '')

    def run_acting(self, one_step):
        self.nodes[self.current_state].fillColor = COLOR_ACT
        self.log('start acting')
        if self.hide_rewards_while_acting:
            self.hide_rewards()
        if self.hide_edges_while_acting:
            self.hide_edges()
        self.stage = 'acting'
        self.start_time = self.current_time = core.getTime()
        self.end_time = None if self.act_time is None else self.start_time + self.act_time

        while not self.done:
            if not self.done and self.end_time is not None and self.current_time > self.end_time:
                self.do_timeout()
            moved = self.get_key_move()
            if moved and one_step:
                return
            self.tick()

    def show_description(self):
        # targets
        visual.TextStim(self.win, self.description_text(), pos=(0, .1), color='white', height=.035).draw()
        xs = np.arange(len(self.targets)) * .1
        xs -= xs.mean()
        for x, t in zip(xs, self.targets):
            self.gfx.image((x, 0), self.images[t], size=.08, autoDraw=False).draw()
        self.win.flip()
        event.waitKeys(keyList=['space'])

    def run(self, one_step=False, skip_planning=False):
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
            self.log('done', {"status": self.status})
            return self.status

        if self.eyelink:
            self.start_recording()

        self.show_description()

        self.show()

        if self.current_state is None:
            self.set_state(self.start)

        self.start_time = self.tick()
        self.log('start', {'flip_time': self.start_time})

        if not (one_step or skip_planning):
            self.run_planning()

        if not self.done:
            self.run_acting(one_step)
            if one_step:
                return

        self.log('done')
        logging.info("end trial " + jsonify(self.data["events"]))
        if self.eyelink:
            self.eyelink.stop_recording()
        wait(.3)
        self.fade_out()
        return self.status
