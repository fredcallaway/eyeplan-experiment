import os
import logging
import json
from datetime import datetime
from psychopy import core, visual, gui, data, event
from psychopy.tools.filetools import fromFile, toFile
import numpy as np

from trial import GraphTrial
from instructions import Instructions
from graphics import Graphics
from bonus import Bonus
from eyetracking import EyeLink


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

        self._message = visual.TextBox2(self.win, '', pos=(-.83, 0), color='white', autoDraw=True, size=(0.65, None), letterHeight=.035, anchor='left')
        self._tip = visual.TextBox2(self.win, '', pos=(-.83, -0.2), color='white', autoDraw=True, size=(0.65, None), letterHeight=.025, anchor='left')

        self.practice_trials = (
            GraphTrial(self.win, **trial, **self.parameters, pos=(.3, 0))
            for trial in self.trials['practice']
        )
        self.trial_data = []


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
        size = (1500,100) if self.full_screen else (1400,800)
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


    def intro(self):
        self.message('Welcome!', space=True)
        gt = next(self.practice_trials)
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

        self.message("You can move by clicking on a location that has an arrow pointing from your current location. Try it now!", space=False)
        gt.run(one_step=True)
        gt.start = gt.current_state

        self.message("The round ends when you get to a location with no outgoing connections.", space=False)
        gt.run()
        self.hide_message()


    def practice(self):
        gt = next(self.practice_trials)
        self.message("Both the connections and points change on every round of the game.", space=False)
        gt.run()

        self.message("Let's try a few more practice rounds.", space=False)

        for gt in self.practice_trials:
            gt.run()

        self.message("Great job!", space=True)
        self.hide_message()


    def setup_eyetracker(self):
        self.message("Now we're going to calibrate the eyetracker. When the circle appears, look at it and press space.", space=True)
        print("here")
        self.hide_message()
        self.win.flip()
        self.eyelink = EyeLink(self.win, self.id)
        self.eyelink.setup_calibration()
        self.eyelink.calibrate()


    def show_gaze_demo(self):
        self.message("Check it out! This is where the eyetracker thinks you're looking.",
                     tip_text='press space to continue')

        self.eyelink.start_recording()
        while 'space' not in event.getKeys():
            visual.Circle(self.win, radius=.01, pos=self.eyelink.gaze_position(), color='red').draw()
            self.win.flip()
        self.win.flip()


    def intro_main(self):
        self.message("Alright! We're ready to begin the main phase of the experiment.", space=True)
        self.message(f"There will be {self.n_trial} rounds. "
                     f"Remember, you'll earn {self.bonus.describe_scheme()} you make in the game. "
                     "We'll start you off with 50 points for all your hard work so far.", space=True )
        self.message("Good luck!", space=True)
        self.hide_message()


    def run_main(self):
        summarize_every = 1
        for (i, trial) in enumerate(self.trials['main']):
            if i > 0 and i % summarize_every == 0:
                msg = f'There are {self.n_trial - i} trials left\n{self.bonus.report_bonus()}'
                msg += f'\nFeel free to take a quick break. Then press space to continue'
                visual.TextBox2(self.win, msg, color='white', letterHeight=.035).draw()
                self.win.flip()
                event.waitKeys(keyList=['space'])
            # fixation_cross()
            gt = GraphTrial(self.win, **trial, **self.parameters, eyelink=self.eyelink)
            gt.run()
            self.bonus.add_points(gt.score)
            self.trial_data.append(gt.data)

    def save_data(self):
        all_data = {
            'parameters': self.parameters,
            'trial_data': self.trial_data,
        }
        os.makedirs('data/exp/', exist_ok=True)
        fp = f'data/exp/{self.id}.json'
        with open(fp, 'w') as f:
            json.dump(all_data, f)
        logging.info('wrote %s', fp)

        self.eyelink.save_data()


