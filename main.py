from experiment import Experiment
from fire import Fire
import logging

def main(config_number=None, name=None, test=False, fast=False):
    exp = Experiment(config_number, name, full_screen=not test)
    try:
        if fast:
            exp.setup_eyetracker()
            exp.show_gaze_demo()
            exp.intro_gaze()
            exp.intro_main()
            exp.run_main()
        else:
            exp.intro()
            exp.practice(2)
            exp.practice_timelimit()
            exp.setup_eyetracker()
            exp.show_gaze_demo()
            exp.intro_gaze()
            exp.intro_main()
            exp.run_main(80)

        exp.save_data()
    except:
        exp.win.clearAutoDraw()
        exp.win.showMessage("Drat! The experiment has encountered an error.\nPlease inform the experimenter.")
        exp.win.flip()
        logging.exception('oh no!')
        try:
            exp.save_data()
            raise
        except:
            logging.exception('error on second save data attempt')
            exp.emergency_save_data()
            raise


if __name__ == '__main__':
    Fire(main)