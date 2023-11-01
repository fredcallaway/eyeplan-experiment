"""measure your JND in orientation using a staircase method"""
from psychopy import core, visual, gui, data, event
from psychopy.tools.filetools import fromFile, toFile
import numpy as np
import json
win = visual.Window([1400,800], allowGUI=True, units='height')

wait = core.wait
with open('json/config/1.json') as f:
    config = json.load(f)

layout = config['parameters']['layout']

# %% --------

SCALE = 40

def scale(x):
    return x
    return SCALE * np.array(x)

def circle(pos, r=.05, **kws):
    return visual.Circle(win, radius=r, pos=pos, lineColor='black', lineWidth=10, autoDraw=True, **kws)

def line(start, end, **kws):
    return visual.line.Line(win, start=start, end=end, lineColor='black', lineWidth=10, autoDraw=True, **kws)

def text(text, pos=(0,0), **kws):
    return visual.TextStim(win, text, pos=pos, autoDraw=True, **kws)



win.clearAutoDraw()

nodes = []
for i, (x, y) in enumerate(layout):
    nodes.append(circle(0.8 * np.array([x, y]), name=str(i)))

trial = config['trials']['main'][1]
for i, js in enumerate(trial['graph']):
    for j in js:
        line(nodes[i].pos, nodes[j].pos, depth=1)

def get_click():
    if mouse.getPressed()[0]:
        pos = mouse.getPos()
        for c in nodes:
            if c.contains(pos):
                return c

mouse = event.Mouse()

for i in range(10000):
    clicked = get_click()
    if clicked:
        print('clicked!', clicked.name)
        for n in nodes:
            n.fillColor = 'white'
        clicked.fillColor = 'blue'
    win.flip()
# %% --------


foil = visual.GratingStim(win, sf=1, size=4, mask='gauss',
                          ori=expInfo['refOrientation'])
target = visual.GratingStim(win, sf=1, size=4, mask='gauss',
                            ori=expInfo['refOrientation'])
fixation = visual.GratingStim(win, color=-1, colorSpace='rgb',
                              tex=None, mask='circle', size=0.2)
# and some handy clocks to keep track of time
globalClock = core.Clock()
trialClock = core.Clock()

# display instructions and wait
message1.draw()
win.flip()

win.flip()

message2 = visual.TextStim(win, pos=[0,-3],
    text="Then press left or right to identify the %.1f deg probe." %expInfo['refOrientation'])
message2.draw()
fixation.draw()
win.flip()#to show our newly drawn 'stimuli'
#pause until there's a keypress
event.waitKeys()

for thisIncrement in staircase:  # will continue the staircase until it terminates!
    # set location of stimuli
    targetSide= random.choice([-1,1])  # will be either +1(right) or -1(left)
    foil.setPos([-5*targetSide, 0])
    target.setPos([5*targetSide, 0])  # in other location

    # set orientation of probe
    foil.setOri(expInfo['refOrientation'] + thisIncrement)

    # draw all stimuli
    foil.draw()
    target.draw()
    fixation.draw()
    win.flip()

    # wait 500ms; but use a loop of x frames for more accurate timing
    core.wait(0.5)

    # blank screen
    fixation.draw()
    win.flip()

    # get response
    thisResp=None
    while thisResp==None:
        allKeys=event.waitKeys()
        for thisKey in allKeys:
            if thisKey=='left':
                if targetSide==-1: thisResp = 1  # correct
                else: thisResp = -1              # incorrect
            elif thisKey=='right':
                if targetSide== 1: thisResp = 1  # correct
                else: thisResp = -1              # incorrect
            elif thisKey in ['q', 'escape']:
                core.quit()  # abort experiment
        event.clearEvents()  # clear other (eg mouse) events - they clog the buffer

    # add the data to the staircase so it can calculate the next level
    staircase.addData(thisResp)
    dataFile.write('%i,%.3f,%i\n' %(targetSide, thisIncrement, thisResp))
    core.wait(1)

# staircase has ended
dataFile.close()
staircase.saveAsPickle(fileName)  # special python binary file to save all the info

# give some output to user in the command line in the output window
print('reversals:')
print(staircase.reversalIntensities)
approxThreshold = numpy.average(staircase.reversalIntensities[-6:])
print('mean of final 6 reversals = %.3f' % (approxThreshold))

# give some on-screen feedback
feedback1 = visual.TextStim(
        win, pos=[0,+3],
        text='mean of final 6 reversals = %.3f' % (approxThreshold))

feedback1.draw()
fixation.draw()
win.flip()
event.waitKeys()  # wait for participant to respond

win.close()
core.quit()