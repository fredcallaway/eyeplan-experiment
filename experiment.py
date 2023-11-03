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

# from eyetracking import EyeLink

subjid = 'fred'
uniqueid = datetime.now().strftime('%y-%m-%d-%H%M-') + subjid

logFormatter = logging.Formatter("%(asctime)s [%(levelname)s]  %(message)s")
rootLogger = logging.getLogger()
rootLogger.setLevel('DEBUG')

os.makedirs('log', exist_ok=True)
fileHandler = logging.FileHandler(f"log/{uniqueid}.log")
fileHandler.setFormatter(logFormatter)
rootLogger.addHandler(fileHandler)

consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(logFormatter)
consoleHandler.setLevel('INFO')
rootLogger.addHandler(consoleHandler)
logging.info(f'starting up {uniqueid} at {core.getTime()}')

win = visual.Window([1400,800], allowGUI=True, units='height')
framerate = win.getActualFrameRate(threshold=1, nMaxFrames=1000)
assert abs(framerate - 60) < 2
win.flip()
with open('json/config/1.json') as f:
    config = json.load(f)

gfx = Graphics(win)

BONUS = Bonus(config['parameters']['points_per_cent'], 50)
N_TRIAL = len(config['trials']['main'])

# %% ==================== instructions ====================
win.clearAutoDraw()
win.flip()

trials = iter(config['trials']['practice'])

instruct = visual.TextBox2(win, '', pos=(-.83, 0), color='white', autoDraw=True, size=(0.65, None), letterHeight=.035, anchor='left')
tip = visual.TextBox2(win, '', pos=(-.83, -0.2), color='white', autoDraw=True, size=(0.65, None), letterHeight=.025, anchor='left')

def message(msg, space=False, tip_text=None):
    logging.debug('message: %s (%s)', msg, tip_text)
    instruct.text = msg
    tip.setText(tip_text if tip_text else
                'press space to continue' if space else
                'click the board to continue')
    win.flip()
    if space:
        event.waitKeys(keyList=['space'])


practice_trials = (
    GraphTrial(win, **trial, **config['parameters'], pos=(.3, 0))
    for trial in config['trials']['practice']
)

message('Welcome!', space=True)

gt = next(practice_trials)
gt.show()
for l in gt.reward_labels:
    l.setOpacity(0)
message("In this experiment, you will play a game on the board shown to the right.", space=True)

gt.set_state(gt.start)
message("Your current location on the board is highlighted in blue.", space=True)

for l in gt.reward_labels:
    l.setOpacity(1)
message("The goal of the game is to collect as many points as you can.", space=True)
message(f"The points will be converted to a cash bonus: {BONUS.describe_scheme()}!", space=True)

message("You can move by clicking on a location that has an arrow pointing from your current location. Try it now!", space=False)
gt.run(one_step=True)
gt.start = gt.current_state

message("The round ends when you get to a location with no outgoing connections.", space=False)
gt.run()

gt = next(practice_trials)
message("Both the connections and points change on every round of the game.", space=False)
gt.run()


message("Let's try a few more practice rounds.", space=False)

for gt in practice_trials:
    gt.run()

message("Great job!", space=True)

# %% --------

message("""
Now we're going to calibrate the eyetracker. When the circle appears, look at it and press space.
""", space=True)
win.stashAutoDraw()
el = EyeLink(win, uniqueid)
el.setup_calibration()
el.calibrate()

# %% --------
win.retrieveAutoDraw()
message("Check it out! This is where the eyetracker thinks you're looking.",
        tip_text='press space to continue')

el.start_recording()
gaze = gfx.circle((0,0), r=.01, color='red')
while 'space' not in event.getKeys():
    gaze.setPos(el.gaze_position())
    win.flip()
gaze.autoDraw = False

# %% --------
message("Alright! We're ready to begin the main phase of the experiment.", space=True)
message(f"There will be  {N_TRIAL} rounds. \
Remember, you'll earn {BONUS.describe_scheme()} you make in the game \
We'll start you off with 50 points for all your hard work so far \
", space=True )
message("Good luck!", space=True)
# %% --------

win.clearAutoDraw()
win.flip()

trial_data = []
summarize_every = 1
for (i, trial) in enumerate(config['trials']['main']):
    if i > 0 and i % summarize_every == 0:
        msg = f'There are {N_TRIAL - i} trials left\n{BONUS.report_bonus()}'
        msg += f'\nFeel free to take a quick break. Then press space to continue'
        visual.TextBox2(win, msg, color='white', letterHeight=.035).draw()
        win.flip()
        event.waitKeys(keyList=['space'])
    # fixation_cross()
    gt = GraphTrial(win, **trial, **config['parameters'], eyelink=el)
    gt.run()
    BONUS.add_points(gt.score)
    trial_data.append(gt.data)

all_data = {
    'parameters': config['parameters'],
    'trial_data': trial_data,
    'fixation_cross_times': fixation_cross_times
}
all_data
os.makedirs('data/exp/', exist_ok=True)
with open(f'data/exp/{uniqueid}.json', 'w') as f:
    json.dump(all_data, f)

el.save_data()