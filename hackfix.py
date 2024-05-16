from psychopy import core, visual, gui, data, event

def clearAutoDraw(self):
    """
    Remove all autoDraw components, meaning they get autoDraw set to False and are not
    added to any list (as in .stashAutoDraw)
    """
    for thisStim in self._toDraw.copy():
        # set autoDraw to False
        thisStim.autoDraw = False


def stashAutoDraw(self):
    """
    Put autoDraw components on 'hold', meaning they get autoDraw set to False but
    are added to an internal list to be 'released' when .releaseAutoDraw is called.
    """
    for thisStim in self._toDraw.copy():
        # set autoDraw to False
        thisStim.autoDraw = False
        # add stim to held list
        self._heldDraw.append(thisStim)


def retrieveAutoDraw(self):
    """
    Add all stimuli which are on 'hold' back into the autoDraw list, and clear the
    hold list.
    """
    for thisStim in self._heldDraw:
        # set autoDraw to True
        thisStim.autoDraw = True
    # clear list
    self._heldDraw = []


def showMessage(self, msg):
    if msg is None:
        return
    visual.TextStim(self, msg, color='white', alignText='center', height=.05).draw()

def add_missing_methods(win):
    win.clearAutoDraw = clearAutoDraw
    win.stashAutoDraw = stashAutoDraw
    win.retrieveAutoDraw = retrieveAutoDraw
    win.showMessage = showMessage
