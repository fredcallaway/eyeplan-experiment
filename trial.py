from psychopy import core, visual, gui, data, event
import numpy as np
import logging
import json
from eyetracking import height2pix
from util import jsonify
import random

wait = core.wait

from config import COLOR_PLAN, COLOR_ACT, COLOR_LOSS, COLOR_WIN, COLOR_HIGHLIGHT, KEY_CONTINUE, KEY_SWITCH, KEY_SELECT, KEY_ABORT

from graphics import Graphics, FRAME_RATE

def reward_color(r):
    return COLOR_WIN if r > 0 else COLOR_LOSS

def reward_string(r):
    return f'{int(r):+}' if r else ''

def distance(p1, p2):
    (x1, y1), (x2, y2) = (p1, p2)
    return np.sqrt((x1 - x2)**2 + (y1 - y2)**2)


TRIGGERS = {
    'show description': 0,
    'show graph': 1,
    'start acting': 2,
    'done': 3,
}


class AbortKeyPressed(Exception): pass


class GraphTrial(object):
    """Graph navigation interface"""
    def __init__(self, win, graph, rewards, start, layout, pos=(0, 0), start_mode=None, max_score=None,
                 images=None, reward_info=None,
                 initial_stage='planning', hide_states=False, hide_rewards_while_acting=True, hide_edges_while_acting=True,
                 eyelink=None, triggers=None, **kws):
        self.win = win
        self.graph = graph
        self.rewards = list(rewards)
        self.start = start
        self.layout = layout
        self.pos = pos
        self.start_mode = start_mode or ('drift_check' if eyelink else 'space')
        self.max_score = max_score

        self.images = images
        self.reward_info = reward_info

        self.stage = initial_stage
        self.hide_states = hide_states
        self.hide_rewards_while_acting = hide_states or hide_rewards_while_acting
        self.hide_edges_while_acting = hide_edges_while_acting

        self.eyelink = eyelink
        self.triggers = triggers

        self.status = 'ok'
        self.show_time = self.done_time = None
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
                "reward_info": reward_info,
                "initial_stage": initial_stage,
                "hide_states": hide_states,
                "hide_rewards_while_acting": hide_rewards_while_acting,
                "hide_edges_while_acting": hide_edges_while_acting,

                "start": start,
            },
            "events": [],
            "flips": [],
            "mouse": [],
        }
        logging.info("begin trial " + jsonify(self.data["trial"]))
        self.gfx = Graphics(win)
        self.mouse = event.Mouse()
        self.done = False

    def wait_keys(self, keys):
        keys = event.waitKeys(keyList=[*keys, KEY_ABORT])
        if KEY_ABORT in keys:
            self.status = 'abort'
            raise AbortKeyPressed()
        else:
            return keys


    def log(self, event, info={}):
        time = core.getTime()
        logging.debug(f'{self.__class__.__name__}.log {time:3.3f} {event} ' + ', '.join(f'{k} = {v}' for k, v in info.items()))
        datum = {
            'time': time,
            'event': event,
            **info
        }
        self.data["events"].append(datum)
        if self.triggers and event in TRIGGERS:
            self.triggers.send(TRIGGERS[event])
        if self.eyelink:
            self.eyelink.message(jsonify(datum), log=False)

    def description_text(self):
        def fmt(x):
            val, desc, targets = x["val"], x["desc"], x["targets"]
            return f'{val:+d} for {desc}'

        return "   ".join(fmt(x) for x in self.reward_info)

    def show(self):
        self.show_time = core.getTime()
        self.log('show graph')
        self.gfx.rect((-.5, .45), .1, .1, fillColor='white')
        if hasattr(self, 'nodes'):
            self.gfx.show()
            return

        self.nodes = nodes = []
        self.node_images = []
        for i, (x, y) in enumerate(self.layout):
            pos = 0.7 * np.array([x, y])
            nodes.append(self.gfx.circle(pos, name=f'node{i}', r=.05))
            self.node_images.append(self.gfx.image(pos, self.images[i], size=.08, autoDraw=not self.hide_states))
        self.data["trial"]["node_positions"] = [height2pix(self.win, n.pos) for n in self.nodes]

        self.arrows = {}
        for i, js in enumerate(self.graph):
            for j in js:
                self.arrows[(i, j)] = self.gfx.arrow(nodes[i], nodes[j])

        self.mask = self.gfx.rect((.1,0), 1.1, 1, fillColor='gray', opacity=0)
        self.gfx.shift(*self.pos)

        if self.reward_info:
            self.desc = self.gfx.text(self.description_text(), pos=(0.45, .45), color="white", anchorHoriz='right')
        else:
            self.desc = None

    def hide(self):
        self.gfx.clear()

    def shift(self, x, y):
        self.gfx.shift(x, y)
        self.pos = np.array(self.pos) + [x, y]

    def set_state(self, s):
        self.log('visit', {'state': s})
        self.nodes[s].fillColor = COLOR_PLAN if self.stage == 'planning' else COLOR_ACT
        self.score += self.rewards[s]
        prev = self.current_state

        self.current_state = s
        if len(self.graph[self.current_state]) == 0:
            self.done = True


        if prev is None:  # initial
            self.node_images[s].setAutoDraw(False)

        else:  # not initial
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

    def fade_out(self):
        self.mask.setAutoDraw(False); self.mask.setAutoDraw(True)  # ensure on top
        for p in self.gfx.animate(.3):
            self.mask.setOpacity(p)
            self.win.flip()
        self.gfx.clear()
        self.win.flip()
        wait(.3)

    def highlight_current_edges(self):
        for (i, j), arrow in self.arrows.items():
            if i == self.current_state:
                arrow.setAutoDraw(False); arrow.setAutoDraw(True)  # on top
                arrow.setColor(COLOR_HIGHLIGHT)
                self.nodes[j].setLineColor(COLOR_HIGHLIGHT)
            else:
                arrow.setColor('black')
                self.nodes[j].setLineColor('black')

    def get_move(self):
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
        arrows[idx].setColor(COLOR_HIGHLIGHT)
        self.win.flip()
        self.log('get move', {"selected": choices[idx]})

        while True:
            pressed = self.wait_keys([KEY_SELECT, KEY_SWITCH, KEY_ABORT])
            if KEY_SELECT in pressed:
                self.log('select', {"selected": choices[idx]})
                if self.hide_edges_while_acting:
                    for arrow in arrows:
                        arrow.setAutoDraw(False)
                self.set_state(choices[idx])
                return True
            else:
                arrows[idx].setColor('black')
                idx = (idx + 1) % len(choices)
                arrows[idx].setColor(COLOR_HIGHLIGHT)
                self.log('switch', {"selected": choices[idx]})
                self.win.flip()

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

        keys = self.wait_keys([KEY_SWITCH, KEY_ABORT])

        if KEY_SWITCH in keys:
            self.log('end planning')

        elif KEY_ABORT in keys:
            logging.warning('abort key pressed')
            self.log('abort planning')
            self.status = 'abort'

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

        while not self.done:
            moved = self.get_move()
            if moved and one_step:
                return
            self.win.flip()

    def show_description(self):
        self.log('show description')
        descs = self.description_text().split("   ")
        ys = (.05, -.05) if self.hide_states else (.25, -.05)
        for i, y in enumerate(ys):
            visual.TextStim(self.win, descs[i], pos=(0, y), color='white', height=.035).draw()
            if not self.hide_states:
                targets = self.reward_info[i]["targets"]
                xs = np.arange(len(targets)) * .1
                xs -= xs.mean()
                for x, t in zip(xs, targets):
                    self.gfx.image((x, y-.1), self.images[t], size=.08, autoDraw=False).draw()

        self.win.flip()
        self.wait_keys([KEY_CONTINUE])

    def run(self, one_step=False, skip_planning=False):
            # if self.start_mode == 'drift_check':
            #     self.log('begin drift_check')
            #     self.status = self.eyelink.drift_check(self.pos)
            # elif self.start_mode == 'fixation':
            #     self.log('begin fixation')
            #     self.status = self.eyelink.fake_drift_check(self.pos)
            # elif self.start_mode == 'space':
            #     self.log('begin space')
            #     visual.TextStim(self.win, f'press {KEY_CONTINUE.upper()} to start', pos=self.pos, color='white', height=.035).draw()
            #     self.win.flip()
            #     self.wait_keys(['space', KEY_CONTINUE])

        self.log('initialize', {'status': self.status})

        if self.status in ('abort', 'recalibrate'):
            self.log('done', {"status": self.status})
            return self.status

        if self.eyelink:
            self.start_recording()

        if self.reward_info:
            self.show_description()

        self.eyelink.fake_drift_check(self.pos)
        self.show()

        if self.current_state is None:
            self.set_state(self.start)

        self.log('start', {'flip_time': self.win.flip()})

        if not (one_step or skip_planning):
            self.run_planning()
        if self.status == 'abort':
            return 'abort'

        self.run_acting(one_step)
        if self.status == 'abort':
            return 'abort'
        if one_step:
            return

        self.log('done')
        self.done_time = core.getTime()
        logging.info("end trial " + jsonify(self.data["events"]))
        if self.eyelink:
            self.eyelink.stop_recording()
        wait(.3)
        self.fade_out()
        return self.status
