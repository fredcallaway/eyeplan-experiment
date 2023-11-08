import os
import logging
import json
from datetime import datetime
from psychopy import core, visual, gui, data, event
from psychopy.tools.filetools import fromFile, toFile
import numpy as np

from trial import GraphTrial
from graphics import Graphics
from bonus import Bonus
from eyetracking import EyeLink

def stage(f):
    def wrapper(self, *args, **kwargs):
        self.win.clearAutoDraw()
        logging.info('begin %s', f.__name__)
        f(self, *args, **kwargs)
        self.win.clearAutoDraw()
        self.win.flip()

    return wrapper


class Experiment(object):
    def __init__(self, participant_id, full_screen=False):
        self.id = datetime.now().strftime('%y-%m-%d-%H%M-') + participant_id
        self.full_screen = full_screen

        with open('json/config/1.json') as f:
            config = json.load(f)
            self.trials = config['trials']
            self.parameters = config['parameters']

        self.setup_logging()
        self.win = self.setup_window()
        self.bonus = Bonus(self.parameters['points_per_cent'], 50)
        self.eyelink = None

        self._message = visual.TextBox2(self.win, '', pos=(-.83, 0), color='white', autoDraw=True, size=(0.65, None), letterHeight=.035, anchor='left')
        self._tip = visual.TextBox2(self.win, '', pos=(-.83, -0.2), color='white', autoDraw=True, size=(0.65, None), letterHeight=.025, anchor='left')

        self._practice_trials = iter(self.trials['practice'])
        self.trial_data = []

    def get_practice_trial(self, **kws):
        trial = next(self._practice_trials)
        prm = {
            **self.parameters,
            'gaze_contingent': False,
            'time_limit': None,
            'pos': (.3, 0),
            **trial,
            **kws
        }

        return GraphTrial(self.win, **prm)


    @property
    def n_trial(self):
        return len(self.trials['main'])

    def setup_logging(self):
        logFormatter = logging.Formatter("%(asctime)s [%(levelname)s]  %(message)s")
        rootLogger = logging.getLogger()
        rootLogger.setLevel('DEBUG')

        os.makedirs('log', exist_ok=True)
        fileHandler = logging.FileHandler(f"log/{self.id}.log")
        fileHandler.setFormatter(logFormatter)
        rootLogger.addHandler(fileHandler)

        consoleHandler = logging.StreamHandler()
        consoleHandler.setFormatter(logFormatter)
        consoleHandler.setLevel('INFO')
        rootLogger.addHandler(consoleHandler)

        logging.info(f'starting up {self.id} at {core.getTime()}')

    def setup_window(self):
        size = (1500,1000) if self.full_screen else (900,500)
        win = visual.Window(size, allowGUI=True, units='height', fullscr=self.full_screen)
        framerate = win.getActualFrameRate(threshold=1, nMaxFrames=1000)
        assert abs(framerate - 60) < 2
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
        for i in range(n):
            self.message("Let's try a few more practice rounds.",
                         space=False, tip_text=f'complete {n - i} practice rounds to continue')
            self.get_practice_trial().run()

        self.message("Great job!", space=True)

    @stage
    def setup_eyetracker(self):
        self.message("Now we're going to calibrate the eyetracker. When the circle appears, look at it and press space.", space=True)
        print("here")
        self.hide_message()
        self.win.flip()
        self.eyelink = EyeLink(self.win, self.id)
        self.eyelink.setup_calibration()
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
                     "Look at it and press space to start the round.",
                     tip_text="look at the circle and press space", space=False)

        gt = self.get_practice_trial(gaze_contingent=True, eyelink=self.eyelink)
        gt.start_recording()
        gt.eyelink.stop_recording()
        self.message("Yup just like that. There's just one more thing...", space=True)
        self.message("The points will only be visible when you're looking at them.", space=True)
        self.message("Try it out! Look at every location to continue", tip_text='', space=False)
        while True:
            result = gt.practice_gazecontingent(timeout=10)
            if result == 'success':
                break
            else:
                self.message("It seems like the eyetracker isn't calibrated correctly. Let's try to fix that", space=True)
                self.hide_message()
                gt.hide()
                self.win.flip()
                self.eyelink.calibrate()
                self.message("OK we're going to try again. We'll use the center of the screen this time", space=True)
                self.hide_message()
                gt.shift(-.3, 0)

        self.message("Great! It looks like the eyetracker is working well.", space=True)

    @stage
    def intro_main(self):
        self.message("Alright! We're ready to begin the main phase of the experiment.", space=True)
        self.message(f"There will be {self.n_trial} rounds. "
                     f"Remember, you'll earn {self.bonus.describe_scheme()} you make in the game. "
                     "We'll start you off with 50 points for all your hard work so far.", space=True )
        self.message("Good luck!", space=True)

    @stage
    def run_one(self, i):
        trial = self.trials['main'][i]
        gt = GraphTrial(self.win, **trial, **self.parameters, eyelink=self.eyelink)
        gt.run()
        self.bonus.add_points(gt.score)
        self.trial_data.append(gt.data)

    @stage
    def run_main(self, n=None):
        summarize_every = self.parameters.get('summarize_every', 5)

        trials = self.trials['main']
        if n is not None:
            trials = trials[:n]

        for (i, trial) in enumerate(trials):
            if i > 0 and i % summarize_every == 0:
                msg = f'There are {self.n_trial - i} trials left\n{self.bonus.report_bonus()}'
                msg += f'\nFeel free to take a quick break. Then press space to continue'
                visual.TextBox2(self.win, msg, color='white', letterHeight=.035).draw()
                self.win.flip()
                event.waitKeys(keyList=['space'])
            # fixation_cross()
            gt = GraphTrial(self.win, **trial, **self.parameters, eyelink=self.eyelink)
            print('gt.gaze_contingent', gt.gaze_contingent)
            gt.run()
            self.bonus.add_points(gt.score)
            self.trial_data.append(gt.data)

    @stage
    def save_data(self):
        self.message("You're done! Let's just save your data...", tip_text="give us a few seconds", space=False)
        all_data = {
            'parameters': self.parameters,
            'trial_data': self.trial_data,
            'window': self.win.size.tolist(),
            'bonus': self.bonus.dollars()
        }
        os.makedirs('data/exp/', exist_ok=True)
        fp = f'data/exp/{self.id}.json'
        with open(fp, 'w') as f:
            json.dump(all_data, f)
        logging.info('wrote %s', fp)

        self.eyelink.save_data()
        self.message("Data saved! Please let the experimenter that you've completed the study.", space=True,
                    tip_text='press space to exit')


