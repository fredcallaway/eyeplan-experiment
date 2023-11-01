from psychopy import core, visual, gui, data, event
from psychopy.tools.filetools import fromFile, toFile
import numpy as np
import json
from functools import cached_property
from graph import Graph, Graphics

win = visual.Window([1400,800], allowGUI=True, units='height')
framerate = win.getActualFrameRate(threshold=1, nMaxFrames=1000)
assert abs(framerate - 60) < 2
win.flip()

# %% --------

with open('json/config/1.json') as f:
    config = json.load(f)

gfx = Graphics(win)

# %% ==================== instructions ====================
win.clearAutoDraw()
win.flip()

trials = iter(config['trials']['practice'])

instruct = visual.TextBox2(win, '', pos=(-.83, 0), color='white', autoDraw=True, size=(0.65, None), letterHeight=.035, anchor='left')
tip = visual.TextBox2(win, '', pos=(-.83, -0.2), color='white', autoDraw=True, size=(0.65, None), letterHeight=.025, anchor='left')

def message(msg, space=False, tip_text=None):
    instruct.text = msg
    tip.setText(tip_text if tip_text else
                'press space to continue' if space else
                'click the board to continue')
    win.flip()
    if space:
        event.waitKeys(keyList=['space'])


def fixation_cross(pos=(0,0)):
    print('fixation')
    visual.ShapeStim(win, pos=pos, size=.03, vertices='cross', fillColor="black").draw()
    win.flip()
    event.waitKeys(keyList=['space'])
    print('space')

practice_graphs = (
    Graph(win, **trial, **config['parameters'], pos=(.3, 0))
    for trial in config['trials']['practice']
)

# message('Welcome!', space=True)

# g = next (practice_graphs)
# g.show()
# for l in g.reward_labels:
#     l.setOpacity(0)
# message("In this experiment, you will play a game on the board shown to the right.", space=True)

# g.set_state(g.start)
# message("Your current location on the board is highlighted in blue.", space=True)

# for l in g.reward_labels:
#     l.setOpacity(1)
# message("The goal of the game is to collect as many points as you can.", space=True)

# message("You can move by clicking on a location that has an arrow pointing from your current location. Try it now!", space=False)
# g.run(one_step=True)
# g.start = g.current_state

# message("The round ends when you get to a location with no outgoing connections.", space=False)
# g.run()

# g = next(practice_graphs)
# message("Both the connections and points change on every round of the game.", space=False)
# g.run()


message("Before each round, a cross will appear. Look at it and press space to start the round.",
        tip_text="Look at the cross and press space to continue")
fixation_cross((.3, 0))
win.flip()

message("Try a few more practice rounds.")
next(practice_graphs).run()

for g in practice_graphs:
    message("Try a few more practice rounds.", tip_text="Look at the cross and press space to continue")
    fixation_cross((0.3, 0))
    message("Try a few more practice rounds.")
    g.run()


# %% --------
for trial in config['trials']['main']:
    visual.ShapeStim(win, size=.03, vertices='cross', fillColor="black").draw()
    win.flip()
    event.waitKeys(keyList=['space'])
    g = Graph(win, **trial, **config['parameters'])
    g.run()



# %% --------


win.clearAutoDraw()
# gfx.circle((0,0), .015)

visual.ShapeStim(win, size=.03, vertices='cross', fillColor="black").draw()

win.flip()