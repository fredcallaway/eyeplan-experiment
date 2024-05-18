from experiment import Experiment
from fire import Fire
import logging

def main(config_number=None, name=None, test=False, fast=False, full=False, mouse=False, hotfix=False, skip_instruct=False, **kws):
    if test and name is None:
        name = 'test'
    if fast:
        kws['n_practice'] = 2
        kws['n_block'] = 2
        kws['block_duration'] = 15/60
    exp = Experiment(config_number, name, full_screen=(not test) or full, test_mode=bool(test), **kws)
    if test == "save":
        exp.save_data()
        exit()
    if test == "practice":
        exp.practice()
        exit()
    if test == "main":
        if not mouse:
            exp.setup_eyetracker()
        exp.main()
        exit()
    elif test == "practice":
        exp.practice()
        exp.intro_main()
        exp.main()
    else:
        try:
            if not skip_instruct:
                exp.welcome()
                exp.setup_eyetracker(mouse)
                exp.show_gaze_demo()
                # exp.intro_gaze()
                exp.practice()
                exp.intro_main()
            exp.main()
            exp.save_data()
        except:
            if test:
                exit(1)
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