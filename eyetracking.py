import pylink
import os
import random
import time
import sys
from string import ascii_letters, digits
import logging
import numpy as np
import hashlib

from config import KEY_CONTINUE

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
    tracker.sendCommand("button_function 1 'accept_target_fixation'");

    tracker.sendCommand("calibration_type = HV9")
    tracker.sendCommand("enable_automatic_calibration = NO")

def pix2height(win, pos):
    assert win.units == 'height'
    w, h = win.size
    x, y = pos

    y *= -1  # invert y axis
    x -= w/2
    y +=  h/2
    y /= h  # scale
    x /= h
    return x, y

def height2pix(win, pos):
    assert win.units == 'height'
    w, h = win.size
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
        self.disable_drift_checks = True

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
        if self.disable_drift_checks:
            return self.fake_drift_check(pos)

        self.win.units = 'height'
        x, y = map(int, height2pix(self.win, pos))
        try:
            self.tracker.doDriftCorrect(x, y, 1, 1)
        except RuntimeError:
            logging.info('escape in drift correct')
            self.win.showMessage('Experimenter, choose:\n(C)ontinue  (A)bort  (R)ecalibrate  (D)isable drift check')
            self.win.flip()
            keys = event.waitKeys(keyList=['space', 'c', 'a', 'r', 'd'])
            logging.info('drift check keys %s', keys)
            self.win.showMessage(None)
            self.win.flip()
            if 'a' in keys:
                return 'abort'
            elif 'r' in keys:
                return 'recalibrate'
            elif 'd' in keys:
                self.disable_drift_checks = True
                return 'disable'
            else:
                self.drift_check(pos)
                return 'ok'
        finally:
            self.win.units = 'height'

    def fake_drift_check(self, pos=(0,0)):
        self.win.units = 'height'
        x, y = map(int, height2pix(self.win, pos))
        self.genv.update_cal_target()
        self.genv.draw_cal_target(x, y)
        self.win.units = 'height'
        keys = event.waitKeys(keyList=['space', 'escape', KEY_CONTINUE])
        if 'escape' not in keys:
            return 'ok'

        self.win.showMessage('Experimenter, choose:\n(C)ontinue  (A)bort  (R)ecalibrate  (D)isable drift check')
        self.win.flip()
        keys = event.waitKeys(keyList=['space', 'c', 'a', 'r', 'd'])
        logging.info('drift check keys %s', keys)
        self.win.showMessage(None)
        self.win.flip()
        if 'a' in keys:
            return 'abort'
        elif 'r' in keys:
            return 'recalibrate'
        elif 'd' in keys:
            return 'disable'
        else:
            return self.fake_drift_check(pos)


    def message(self, msg, log=True):
        if log:
            logging.debug('EyeLink.message %s', msg)
        self.tracker.sendMessage(msg + f'time({core.getTime()})')

    def start_recording(self):
        logging.info('start_recording')
        self.tracker.startRecording(1, 1, 1, 1)
        pylink.pumpDelay(100)  # maybe necessary to clear out old samples??

    def stop_recording(self):
        logging.info('stop_recording')
        self.tracker.stopRecording()

    def setup_calibration(self, full_screen=False):
        # Open a window, be sure to specify monitor parameters
        self.message(f'Set up calibration')
        scn_width, scn_height = np.round(self.win.size)
        # pygame.mouse.set_visible(True)  # show mouse cursor

        # Pass the display pixel coordinates (left, top, right, bottom) to the tracker
        # see the EyeLink Installation Guide, "Customizing Screen Settings"

        scale = 0.9
        h_trim = int(((1 - scale) * scn_height) / 2)
        w_trim = int((scn_width - scale * scn_height) / 2)

        el_coords = f"screen_pixel_coords = {w_trim} {h_trim} {scn_width - w_trim - 1} {scn_height - h_trim - 1}"
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
        self.win.mouseVisible = False
        self.win.clearAutoDraw()
        self.genv.setup_cal_display()
        self.win.flip()
        logging.info('doTrackerSetup')
        self.tracker.doTrackerSetup()
        logging.info('done doTrackerSetup')
        self.genv.exit_cal_display()
        self.win.flip()
        self.win.units = 'height'
        self.win.mouseVisible = True

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
            eye = sample.getLeftEye() or sample.getRightEye()
            return pix2height(self.win, eye.getGaze())

    def close_connection(self):
        # TODO make sure this gets called
        if self.tracker.isConnected():
            self.tracker.close()

class MouseLink(EyeLink):
    """Fake eyelink"""
    def __init__(self, win, uniqueid, dummy_mode=False):
        self.win = win
        self.mouse = event.Mouse()
        self.disable_drift_checks = False

        print("UNITS", self.win.units)

        self.genv = genv = EyeLinkCoreGraphicsPsychoPy(None, self.win)
        foreground_color = (-1, -1, -1)
        genv.setCalibrationColors(foreground_color, self.win.color)
        genv.setTargetType('circle')
        genv.setTargetSize(24)
        # genv.setCalibrationSounds('', '', '')
        genv.fixMacRetinaDisplay()
        self.win.units = 'height'
        print("UNITS", self.win.units)

    def drift_check(self, pos=(0,0)):
        logging.info('MouseLink drift_check')
        return super().fake_drift_check()

    def message(self, msg, log=True):
        logging.debug('MouseLink message')
        return

    def start_recording(self):
        logging.info('MouseLink start_recording')
        return

    def stop_recording(self):
        logging.info('MouseLink stop_recording')
        return

    def setup_calibration(self, full_screen=False):
        logging.info('MouseLink setup_calibration')
        return

    def calibrate(self):
        logging.info('MouseLink calibrate')
        self.win.showMessage('This would be a calibration if not in mouse mode\npress space to continue')
        self.win.flip()
        keys = event.waitKeys(keyList=['space', 'c'])
        self.win.showMessage(None)
        self.win.flip()
        return

    def save_data(self):
        logging.info('MouseLink save_data')
        return

    def gaze_position(self):
        return self.mouse.getPos()

    def close_connection(self):
        logging.info('MouseLink close_connection')
        return


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
