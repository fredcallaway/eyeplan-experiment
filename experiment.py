import os
import logging
import json
import re
from datetime import datetime
from psychopy import core, visual, gui, data, event
from psychopy.tools.filetools import fromFile, toFile
import numpy as np

from util import jsonify
from trial import GraphTrial
from graphics import Graphics
from bonus import Bonus
from eyetracking import EyeLink, MouseLink

import subprocess
from copy import deepcopy
from config import VERSION


DATA_PATH = f'data/exp/{VERSION}'
CONFIG_PATH = f'config/{VERSION}'
LOG_PATH = 'log'
for p in (DATA_PATH, CONFIG_PATH, LOG_PATH, ):
    os.makedirs(p, exist_ok=True)


def stage(f):
    def wrapper(self, *args, **kwargs):
        self.win.clearAutoDraw()
        logging.info('begin %s', f.__name__)
        try:
            f(self, *args, **kwargs)
        except:
            stage = f.__name__
            logging.exception(f"Caught exception in stage {stage}")
            if f.__name__ == "run_main":
                logging.warning('Continuing to save data...')
            else:
                self.win.clearAutoDraw()
                self.win.showMessage('The experiment ran into a problem! Please tell the experimenter.\nThen press C to continue.')
                self.win.flip()
                event.waitKeys(keyList=['c'])
                self.win.showMessage(None)
                logging.warning(f'Retrying {stage}')
                f(self, *args, **kwargs)
        finally:
            self.win.clearAutoDraw()
            self.win.flip()

    return wrapper

def get_next_config_number():
    print("FIX ME!")
    used = set()
    for fn in os.listdir(DATA_PATH):
        m = re.match(r'.*_P(\d+)\.', fn)
        if m:
            used.add(int(m.group(1)))

    possible = range(1, 1 + len(os.listdir(CONFIG_PATH)))
    try:
        n = next(i for i in possible if i not in used)
        return n
    except StopIteration:
        print("WARNING: USING RANDOM CONFIGURATION NUMBER")
        return np.random.choice(list(possible))


class Experiment(object):
    def __init__(self, config_number, name=None, full_screen=False):
        if config_number is None:
            config_number = get_next_config_number()
        self.config_number = config_number
        print('>>>', self.config_number)
        self.full_screen = full_screen

        timestamp = datetime.now().strftime('%y-%m-%d-%H%M')
        self.id = f'{timestamp}_P{config_number}'
        if name:
            self.id += '-' + str(name)

        self.setup_logging()
        logging.info('git SHA: ' + subprocess.getoutput('git rev-parse HEAD'))

        config_file = f'{CONFIG_PATH}/{config_number}.json'
        logging.info('Configuration file: ' + config_file)
        with open(config_file) as f:
            conf = json.load(f)
            self.trials = conf['trials']
            self.parameters = conf['parameters']
            logging.info('parameters %s', self.parameters)

        self.win = self.setup_window()
        self.bonus = Bonus(0, 50)
        # self.bonus = Bonus(self.parameters['points_per_cent'], 50)
        self.eyelink = None
        self.disable_gaze_contingency = False

        self._message = visual.TextBox2(self.win, '', pos=(-.83, 0), color='white', autoDraw=True, size=(0.65, None), letterHeight=.035, anchor='left')
        self._tip = visual.TextBox2(self.win, '', pos=(-.83, -0.2), color='white', autoDraw=True, size=(0.65, None), letterHeight=.025, anchor='left')

        # self._practice_trials = iter(self.trials['practice'])
        self.practice_i = -1
        self.trial_data = []
        self.practice_data = []

    def _reset_practice(self):
        self._practice_trials = iter(self.trials['practice'])

    def get_practice_trial(self, repeat=False,**kws):
        if not repeat:
            self.practice_i += 1
        prm = {
            **self.parameters,
            'gaze_contingent': False,
            'time_limit': None,
            'pos': (.3, 0),
            'space_start': False,
            **self.trials['practice'][self.practice_i],
            **kws
        }
        gt = GraphTrial(self.win, **prm)
        self.practice_data.append(gt.data)
        return gt


    @property
    def n_trial(self):
        return len(self.trials['main'])

    def setup_logging(self):
        logFormatter = logging.Formatter("%(asctime)s [%(levelname)s]  %(message)s")
        rootLogger = logging.getLogger()
        rootLogger.setLevel('DEBUG')

        fileHandler = logging.FileHandler(f"{LOG_PATH}/{self.id}.log")
        fileHandler.setFormatter(logFormatter)
        rootLogger.addHandler(fileHandler)

        consoleHandler = logging.StreamHandler()
        consoleHandler.setFormatter(logFormatter)
        consoleHandler.setLevel('INFO')
        rootLogger.addHandler(consoleHandler)

        logging.info(f'starting up {self.id} at {core.getTime()}')


    def setup_window(self):
        size = (1350,750) if self.full_screen else (900,500)
        win = visual.Window(size, allowGUI=True, units='height', fullscr=self.full_screen)
        # framerate = win.getActualFrameRate(threshold=1, nMaxFrames=1000)
        # assert abs(framerate - 60) < 2
        win.flip()
        # win.callOnFlip(self.on_flip)
        return win

    def on_flip(self):
        if 'q' in event.getKeys():
            exit()
        # if 'f' in event.getKeys():

        self.win.callOnFlip(self.on_flip)

    def hide_message(self):
        self._message.autoDraw = False
        self._tip.autoDraw = False

    def show_message(self):
        self._message.autoDraw = True
        self._tip.autoDraw = True

    def message(self, msg, space=False, tip_text=None):
        logging.debug('message: %s (%s)', msg, tip_text)
        self.show_message()
        self._message.setText(msg)
        self._tip.setText(tip_text if tip_text else
                    'press space to continue' if space else
                    'click the board to continue')
        self.win.flip()
        if space:
            event.waitKeys(keyList=['space'])

    @stage
    def intro(self):
        self.message('Welcome!', space=True)
        gt = self.get_practice_trial()

        gt.show()
        for l in gt.reward_labels:
            l.setOpacity(0)
        self.message("In this experiment, you will play a game on the board shown to the right.", space=True)

        gt.set_state(gt.start)
        self.message("Your current location on the board is highlighted in blue.", space=True)

        for l in gt.reward_labels:
            l.setOpacity(1)
        self.message("The goal of the game is to collect as many points as you can.", space=True)
        if self.bonus:
            self.message(f"The points will be converted to a cash bonus: {self.bonus.describe_scheme()}!", space=True)

        self.message("You can move by clicking on a location that has an arrow pointing from your current location. Try it now!",
                     tip_text='click one of the highlighted locations', space=False)
        gt.run(one_step=True, highlight_edges=True)
        gt.start = gt.current_state

        self.message("The round ends when you get to a location with no outgoing connections.",
                     tip_text='click one of the highlighted locations', space=False)
        gt.run(highlight_edges=True)

    @stage
    def practice_change(self):
        gt = self.get_practice_trial()

        self.message("Both the connections and points change on every round of the game.",
                     tip_text='complete the round to continue', space=False)
        gt.run()

    @stage
    def practice_timelimit(self):
        gt = self.get_practice_trial(time_limit=3)
        gt.disable_click = True

        self.message("To make things more exciting, each round has a time limit.", space=True)
        gt.show()
        gt.timer.setLineColor('#FFC910')
        gt.timer.setLineWidth(5)
        gt.win.flip()

        self.message("The time left is indicated by a bar on the right.", space=True)
        gt.timer.setLineWidth(0)
        self.message("Let's see what happens when it runs out...", space=False,
            tip_text='wait for it')
        gt.run()
        self.message("If you run out of time, we'll make random decisions for you. Probably something to avoid.", space=True)

    @stage
    def practice(self, n):
        intervened = False
        for i in range(n):
            self.message("Let's try a few more practice rounds.",
                         space=False, tip_text=f'complete {n - i} practice rounds to continue')

            gt = self.get_practice_trial()
            for i in range(3):
                gt.run()
                if intervened or gt.score == gt.max_score:
                    break
                else:
                    self.message(
                        f"You got {int(gt.score)} points on that round, but you could have gotten {int(gt.max_score)}.\n"
                        f"Let's try again. Try to make as many points as possible!"
                    )
                gt = self.get_practice_trial(repeat=True)
            else:  # never succeeded
                logging.warning(f"failed practice trial {i}")
                if not intervened:
                    intervened = True
                    self.message("Please check in with the experimenter",
                        tip_text="Wait for the experimenter (space)", space=True)
                    self.get_practice_trial(repeat=True).run()


        self.message("Great job!", space=True)

    @stage
    def setup_eyetracker(self, mouse=False):
        self.message("Now we're going to calibrate the eyetracker. Please tell the experimenter.",
            tip_text="Wait for the experimenter (space)", space=True)
        self.hide_message()
        self.win.flip()
        if mouse:
            self.eyelink = MouseLink(self.win, self.id)
        else:
            self.eyelink = EyeLink(self.win, self.id)
        self.eyelink.setup_calibration()
        self.eyelink.calibrate()

    @stage
    def recalibrate(self):
        self.message("We're going to recalibrate the eyetracker. Please tell the experimenter.",
            tip_text="Wait for the experimenter (c or x)")
        keys = event.waitKeys(keyList=['c', 'x'])
        self.hide_message()
        self.win.flip()
        if 'x' in keys:
            if self.parameters.get('gaze_tolerance') == 1.5:
                logging.warning("Disabling gaze-contingency")
                self.disable_gaze_contingency = True
                self.message("Gaze-contingency disabled for the remainder of the experiment.", space=True)
            else:
                logging.warning('Setting gaze_tolerance to 1.5')
                self.parameters['gaze_tolerance'] = 1.5
                self.eyelink.calibrate()

        else:
            self.eyelink.calibrate()


    @stage
    def show_gaze_demo(self):
        self.message("Check it out! This is where the eyetracker thinks you're looking.",
                     tip_text='press space to continue')

        self.eyelink.start_recording()
        while 'space' not in event.getKeys():
            visual.Circle(self.win, radius=.01, pos=self.eyelink.gaze_position(), color='red').draw()
            self.win.flip()
        self.win.flip()

    @stage
    def intro_gaze(self):
        self.message("At the beginning of each round, a circle will appear. "
                     "Look straight at it and press space to start the round.",
                     tip_text="look at the circle and press space", space=False)

        gt = self.get_practice_trial(gaze_contingent=True, eyelink=self.eyelink, pos=(0,0))

        gt.start_recording()
        gt.eyelink.stop_recording()

        self.message("Yup just like that. Make sure you hold your gaze steady on the circle before pressing space.", space=True)
        self.message("There's just one more thing...", space=True)
        self.message("On some rounds, the points will only be visible when you're looking at them.", space=True)
        self.message("Try it out!\nShow all the points\nto continue", tip_text='press X to recalibrate', space=False)

        def on_done():
            self.message("Great! Keep looking\naround as long\nas you like", tip_text='press space to continue\n or X to recalibrate', space=False)


        for attempt in range(1, 4):
            result = gt.practice_gazecontingent(on_done, timeout=60)
            if result == 'success':
                break
            else:
                if attempt == 1:
                    self.message("It seems like the eyetracker isn't calibrated correctly. Let's try to fix that.", space=True)
                if attempt == 2:
                    self.parameters['gaze_tolerance'] = 1.5
                    logging.warning('Setting gaze_tolerance to 1.5')
                    self.message("Hmmm, let's try one more time", space=True)
                if attempt == 3:
                    logging.warning('disabling gaze contingency')
                    self.disable_gaze_contingency = True
                    self.message("OK. We'll just leave the number visible all the time", space=True)
                    return

                self.hide_message()
                gt.hide()
                self.win.flip()
                self.eyelink.calibrate()
                self.message("OK we're going to try again.", space=True)
                self.message("Show all the points\nto continue", tip_text='press X to recalibrate', space=False)

                gt = self.get_practice_trial(gaze_contingent=True, eyelink=self.eyelink, pos=(0,0), repeat=True)
                # self.hide_message()

        self.message("Great! It looks like the eyetracker is working well.", space=True)
        self.message("By the way, if it ever seems like the eyetracker isn't working correctly, "
                     "please let the experimenter know so we can fix it!", space=True)

    @stage
    def intro_main(self):
        self.message("Alright! We're ready to begin the main phase of the experiment.", space=True)
        if self.bonus:
            self.message(f"There will be {self.n_trial} rounds. "
                         f"Remember, you'll earn {self.bonus.describe_scheme()} you make in the game. "
                         "We'll start you off with 50 points for all your hard work so far.", space=True )
            self.message("Good luck!", space=True)
        else:
            self.message(f"There will be {self.n_trial} rounds. Good luck!", space=True)

    @stage
    def run_one(self, i, **kws):
        trial = self.trials['main'][i]
        prm = {
            **self.parameters,
            **trial,
            **kws
        }
        gt = GraphTrial(self.win, **prm, eyelink=self.eyelink)
        gt.run()
        self.bonus.add_points(gt.score)
        self.trial_data.append(gt.data)

    @stage
    def run_main(self, n=None):
        summarize_every = self.parameters.get('summarize_every', 5)

        trials = self.trials['main']
        if n is not None:
            trials = trials[:n]

        block_earned = 0
        block_possible = 0
        for (i, trial) in enumerate(trials):
            logging.info(f"Trial {i+1} of {len(trials)}")
            if i == 49:
                self.recalibrate()
            try:
                if i > 0 and i % summarize_every == 0:
                    msg = f"In the last {summarize_every} rounds, you earned {int(block_earned)} points out of {int(block_possible)} possible points."
                    block_earned = block_possible = 0
                    if self.bonus:
                        msg += f"\n{self.bonus.report_bonus()}"
                    msg += f'\n\nThere are {self.n_trial - i} rounds left. Feel free to take a quick break. Then press space to continue.'
                    visual.TextBox2(self.win, msg, color='white', letterHeight=.035).draw()
                    self.win.flip()
                    event.waitKeys(keyList=['space'])
                if self.disable_gaze_contingency:
                    trial['gaze_contingent'] = False
                gt = GraphTrial(self.win, **trial, **self.parameters, eyelink=self.eyelink)
                gt.run()
                block_earned += gt.score
                block_possible += gt.max_score
                self.bonus.add_points(gt.score)

                self.trial_data.append(gt.data)
                if gt.status == 'x':
                    self.recalibrate()
                elif gt.status == 'a':
                    self.win.clearAutoDraw()
                    self.win.showMessage(
                       'Abort key was pressed!\n'
                       'Press A again to stop the experiment early.'
                       )
                    self.win.flip()
                    keys = event.waitKeys()
                    self.win.showMessage(None)
                    if 'a' in keys:
                        break
            except:
                logging.exception(f"Caught exception in run_main")
                self.win.clearAutoDraw()
                self.win.showMessage(
                    'The experiment ran into a problem! Please tell the experimenter.\n'
                    'Press C to continue or A to abort and save data'
                    )
                self.win.flip()
                keys = event.waitKeys(keyList=['c', 'a'])
                self.win.showMessage(None)
                print('keys are', keys)
                if 'c' in keys:
                    continue
                else:
                    print('return')
                    return

    @property
    def all_data(self):
        return {
            'config_number': self.config_number,
            'parameters': self.parameters,
            'trial_data': self.trial_data,
            'practice_data': self.practice_data,
            'window': self.win.size,
            'bonus': self.bonus.dollars()
        }

    @stage
    def save_data(self):
        self.message("You're done! Let's just save your data...", tip_text="give us a few seconds", space=False)

        fp = f'{DATA_PATH}/{self.id}.json'
        with open(fp, 'w') as f:
            f.write(jsonify(self.all_data))
        logging.info('wrote %s', fp)

        if self.eyelink:
            self.eyelink.save_data()
        self.message("Data saved! Please let the experimenter that you've completed the study.", space=True,
                    tip_text='press space to exit')

    def emergency_save_data(self):
        logging.warning('emergency save data')
        fp = f'{DATA_PATH}/{self.id}.txt'
        with open(fp, 'w') as f:
            f.write(str(self.all_data))
        logging.info('wrote %s', fp)



