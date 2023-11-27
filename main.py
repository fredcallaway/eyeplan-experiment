from experiment import Experiment
from fire import Fire
import logging

def main(config_number=None, name=None, test=False, fast=False):
    if test and name is None:
        name = 'test'
    exp = Experiment(config_number, name, full_screen=not test)
    if test:
        exp.parameters['summarize_every'] = 2
        # exp.intro()
        # exp.practice(1)
        # exp.practice_timelimit()
        # exp.setup_eyetracker()
        # exp.show_gaze_demo()
        # exp.intro_gaze()
        # exp.intro_main()
        exp.run_main(6)
        return
    try:
        if fast:
            exp.intro()
            exp.practice(1)
            exp.practice_timelimit()
            exp.setup_eyetracker()
            exp.show_gaze_demo()
            exp.intro_gaze()
            exp.intro_main()
            exp.run_main(2)
        else:
            exp.intro()
            exp.practice(3)
            exp.practice_timelimit()
            exp.setup_eyetracker()
            exp.show_gaze_demo()
            exp.intro_gaze()
            exp.intro_main()
            exp.run_main()

        exp.save_data()
    except:
        logging.exception('Uncaught exception in main')
        exp.win.clearAutoDraw()
        exp.win.showMessage("Drat! The experiment has encountered an error.\nPlease inform the experimenter.")
        exp.win.flip()
        try:
            exp.save_data()
            raise
        except:
            logging.exception('error on second save data attempt')
            exp.emergency_save_data()
            raise


if __name__ == '__main__':
    Fire(main)