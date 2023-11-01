"""measure your JND in orientation using a staircase method"""
from psychopy import core, visual, gui, data, event
from psychopy.tools.filetools import fromFile, toFile
import numpy as np
import json
from functools import cached_property
from graph import Graph

win = visual.Window([1400,800], allowGUI=True, units='height')

with open('json/config/1.json') as f:
    config = json.load(f)

layout = config['parameters']['layout']

# %% --------

win.clearAutoDraw()
win.flip()
trial = config['trials']['main'][2]
g = Graph(win, **trial, layout=layout)
win.flip()
g.run()
# %% --------
for trial in config['trials']['main']:
    g = Graph(win, **trial, layout=layout)
    g.run()

# %% --------
from graph import Graphics
win.clearAutoDraw()

gfx = Graphics(win)



gfx.line(n0.pos, n1.pos, depth=2)
vertices = .01 * np.array([[-1, -2], [1, -2], [0, 0]])



n1.pos
# visual.ShapeStim(win, vertices=vertices, autoDraw=True, fillColor='black',
#                  pos=move_towards(n1.pos, n0.pos, n1.radius),
#                  ori=90+angle(n0.pos, n1.pos))

# %% --------



# %% --------

win.clearAutoDraw()
n0 = gfx.circle((0, 0))
n1 = gfx.circle((-.4, .2))
gfx.line(n0.pos, n1.pos, depth=2)
visual.ShapeStim(win, vertices=vertices, autoDraw=True, fillColor='black',
                 pos=move_towards(n1.pos, n0.pos, n1.radius),
                 ori=90-angle(n0.pos, n1.pos))
win.flip()
angle(n0.pos, n1.pos)