import pylink
import os
import random
import time
import sys
from functools import cached_property
from string import ascii_letters, digits
import logging
import numpy as np
import hashlib

from EyeLinkCoreGraphicsPsychoPy import EyeLinkCoreGraphicsPsychoPy
from psychopy import visual, core, event, monitors, gui

def hide_dock():
    os.system(f"""osascript -e '
    tell application "System Events"
      set autohide of dock preferences to true
    end tell
    '""")

class EyelinkError(Exception): pass

def ensure_edf_filename(name):
    return hashlib.md5(name.encode()).hexdigest()[:8] + '.EDF'

def configure_data(tracker):
    vstr = tracker.getTrackerVersionString()
    eyelink_ver = int(vstr.split()[-1].split('.')[0])

    # File and Link data control
    # what eye events to save in the EDF file, include everything by default
    file_event_flags = 'LEFT,RIGHT,FIXATION,SACCADE,BLINK,MESSAGE,BUTTON,INPUT'
    # what eye events to make available over the link, include everything by default
    link_event_flags = 'LEFT,RIGHT,FIXATION,SACCADE,BLINK,BUTTON,FIXUPDATE,INPUT'
    # what sample data to save in the EDF data file and to make available
    # over the link, include the 'HTARGET' flag to save head target sticker
    # data for supported eye trackers
    if eyelink_ver > 3:
        file_sample_flags = 'LEFT,RIGHT,GAZE,HREF,RAW,AREA,HTARGET,GAZERES,BUTTON,STATUS,INPUT'
        link_sample_flags = 'LEFT,RIGHT,GAZE,GAZERES,AREA,HTARGET,STATUS,INPUT'
    else:
        file_sample_flags = 'LEFT,RIGHT,GAZE,HREF,RAW,AREA,GAZERES,BUTTON,STATUS,INPUT'
        link_sample_flags = 'LEFT,RIGHT,GAZE,GAZERES,AREA,STATUS,INPUT'
    tracker.sendCommand("file_event_filter = %s" % file_event_flags)
    tracker.sendCommand("file_sample_data = %s" % file_sample_flags)
    tracker.sendCommand("link_event_filter = %s" % link_event_flags)
    tracker.sendCommand("link_sample_data = %s" % link_sample_flags)

    tracker.sendCommand("calibration_type = HV9")

def pix2height(win, pos):
    assert win.units == 'height'
    w, h = win.size / 2  # eyetracker uses non-retina pixels
    h
    x, y = pos

    y *= -1  # invert y axis
    x -= w/2
    y +=  h/2
    y /= h  # scale
    x /= h
    return x, y

def height2pix(win, pos):
    assert win.units == 'height'
    w, h = win.size / 2  # eyetracker uses non-retina pixels
    x, y = pos


    # scale and invert y
    y *= -h
    x *= h

    # center
    x += w/2
    y +=  h/2
    return x, y


class EyeLink(object):
    """Nice pylink interface"""
    def __init__(self, win, uniqueid, dummy_mode=False):
        logging.info('New EyeLink object')
        self.win = win
        uniqueid = uniqueid.replace(':', '_')
        self.dummy_mode = dummy_mode
        self.uniqueid = uniqueid
        self.edf_file = ensure_edf_filename(uniqueid)

        if pylink.getEYELINK():
            logging.info('Using existing tracker')
            self.tracker = pylink.getEYELINK()
        else:
            logging.info('Initializing new tracker')
            if dummy_mode:
                self.tracker = pylink.EyeLink(None)
            else:
                self.tracker = pylink.EyeLink("100.1.1.1")
                self.tracker.openDataFile(self.edf_file)
                configure_data(self.tracker)
                self.setup_calibration()
                self.tracker.setOfflineMode()
                logging.info('Tracker initialized')

    def drift_check(self, pos=(0,0)):
        # TODO: might want to implement this myself, to make it more stringent
        x, y = map(int, height2pix(self.win, pos))
        try:
            self.tracker.doDriftCorrect(x, y, 1, 1)
        except RuntimeError:
            logging.info('escape in drift correct')
            self.tracker.doDriftCorrect(x, y, 1, 1)
        self.win.units = 'height'

    def message(self, msg):
        logging.info('EyeLink.message %s', msg)
        self.tracker.sendMessage(msg + f'time({core.getTime()})')

    def start_recording(self):
        logging.info('start_recording')
        self.tracker.startRecording(1, 1, 1, 1)

    def stop_recording(self):
        logging.info('stop_recording')
        self.tracker.stopRecording()

    def setup_calibration(self, full_screen=False):
        # Open a window, be sure to specify monitor parameters
        self.message(f'Set up calibration')
        scn_width, scn_height = np.round(self.win.size / 2)  # / 2 for retina
        # pygame.mouse.set_visible(True)  # show mouse cursor

        # Pass the display pixel coordinates (left, top, right, bottom) to the tracker
        # see the EyeLink Installation Guide, "Customizing Screen Settings"

        offset = int((scn_width - scn_height) / 2)

        el_coords = f"screen_pixel_coords = {offset} 0 {scn_width - offset - 1} {scn_height - 1}"
        self.tracker.sendCommand(el_coords)
        # For EyeLink Data Viewer
        # dv_coords = "DISPLAY_COORDS  0 0 %d %d" % (scn_width - 1, scn_height - 1)
        # self.tracker.sendMessage(dv_coords)

        # Configure a graphics environment (genv) for tracker calibration
        self.genv = genv = EyeLinkCoreGraphicsPsychoPy(self.tracker, self.win)
        foreground_color = (-1, -1, -1)
        genv.setCalibrationColors(foreground_color, self.win.color)
        genv.setTargetType('circle')
        genv.setTargetSize(24)
        # genv.setCalibrationSounds('', '', '')
        genv.fixMacRetinaDisplay()
        pylink.closeGraphics()
        pylink.openGraphicsEx(genv)

    def calibrate(self):
        logging.info('doTrackerSetup')
        self.tracker.doTrackerSetup()
        logging.info('done doTrackerSetup')
        self.genv.exit_cal_display()
        self.win.flip()
        self.win.units = 'height'

    def save_data(self):
        self.tracker.closeDataFile()

        # Set up a folder to store the EDF data files and the associated resources
        # e.g., files defining the interest areas used in each trial
        results_folder = 'data/eyelink'
        if not os.path.exists(results_folder):
            os.makedirs(results_folder)

        # create a folder for the current testing session in the "results" folder
        session_folder = os.path.join(results_folder, self.uniqueid)
        if not os.path.exists(session_folder):
            os.makedirs(session_folder)

        # Download the EDF data file from the Host PC to a local data folder
        # parameters: source_file_on_the_host, destination_file_on_local_drive
        local_edf = os.path.join(session_folder,  'raw.edf')
        logging.info('receiving eyelink data')
        self.tracker.receiveDataFile(self.edf_file, local_edf)
        logging.info('wrote %s', local_edf)
        self.tracker.close()

    def gaze_position(self):
        sample = gaze = self.tracker.getNewestSample()
        if sample is None:
            return (-100000, -100000)
        else:
            gaze = sample.getLeftEye().getGaze()
            return pix2height(self.win, gaze)

    def close_connection(self):
        # TODO make sure this gets called
        if self.tracker.isConnected():
            self.tracker.close()


if __name__ == '__main__':
    mon = monitors.Monitor('myMonitor', width=53.0, distance=70.0)
    win = visual.Window(fullscr=False,
                        monitor=mon,
                        # winType='pyglet',
                        units='pix')
    el = EyeLink(win, 'oct9', dummy_mode=False)
    print('try to calibrate')
    el.tracker.sendCommand("calibration_type = HV3")
    el.setup_calibration()
    el.calibrate()
    print('success!')
    # el.start_recording()
    # time.sleep(5)
    el.message("TEST MESSAGE")
    el.save_data()
