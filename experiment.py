"""measure your JND in orientation using a staircase method"""
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

layout = config['parameters']['layout']
gfx = Graphics(win)

# %% --------

win.clearAutoDraw()
trial = config['trials']['main'][2]
g = Graph(win, **trial, layout=layout)
win.flip()
core.wait(1)
g.run()


# %% --------
for trial in config['trials']['main']:
    g = Graph(win, **trial, layout=layout)
    g.run()
