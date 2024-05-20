from experiment import Experiment
from fire import Fire
import logging
import random

def main(pid=None, name=None, test=False, fast=False, full=False, mouse=False, hotfix=False, skip_instruct=False, resume_block=None, **kws):
    if test and name is None:
        name = 'test'
    if fast:
        kws['n_practice'] = 2
        kws['n_block'] = 2
        kws['block_duration'] = 15/60

    if pid is None:
        if test:
            pid = 0
        else:
            pid = int(input("\n Please enter the participant ID number: "))

    exp = Experiment(pid, name, full_screen=(not test) or full, test_mode=bool(test), **kws)
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
            if not (skip_instruct or resume_block):
                exp.welcome()
                exp.setup_eyetracker(mouse)
                exp.show_gaze_demo()
                # exp.intro_gaze()
                exp.practice()
                exp.intro_main()

            if resume_block:
                exp.message(
                    f"Resuming experiment at Block {resume_block}.\n"
                    "Note that the reported bonuses will not reflect the money you've already earned "
                    "(but we still have that information!)",
                    space=True
                )
                random.shuffle(exp.trials['main'])
                exp.main_trials = iter(exp.trials['main'])

            exp.main(resume_block)
            exp.save_data()
        except:
            if test:
                raise
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