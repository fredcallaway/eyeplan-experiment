from experiment import Experiment
from fire import Fire
import logging

def main(name=None, test=False, full=False, mouse=False, **kws):
    if test and name is None:
        name = 'test'

    exp = Experiment(name=name, full_screen=(not test) or full, test_mode=bool(test), **kws)
    if test == 'main':
        exp.setup_eyetracker(mouse)
        exp.debug_main()
        return
    elif test == 'forced':
        exp.intro_forced()
        exp.practice_forced(10)
    else:
        try:
            exp.intro()
            exp.intro_change()
            exp.practice(2)
            exp.intro_forced()
            exp.practice_forced(3)
            exp.intro_double()
            exp.setup_eyetracker(mouse)
            exp.show_gaze_demo()
            exp.intro_gaze()
            # exp.calibrate_gaze_tolerance()
            # exp.intro_contingent()
            exp.intro_main()
            exp.run_main()
            exp.save_data()
        except:
            logging.exception('Uncaught exception in main')
            if test:
                exit(1)
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