from experiment import Experiment
from fire import Fire
import logging

def main(config_number=None, name='test', test=False, fast=False, full=False, mouse=False, hotfix=False, **kws):
    if test and name is None:
        name = 'test'
    if fast:
        kws['score_limit'] = 10
    exp = Experiment(config_number, name, full_screen=(not test) or full, skip_survey = True, **kws)

    try:
        exp.setup_eyetracker(mouse)
        exp.show_gaze_demo()
        exp.calibrate_gaze_tolerance()
        exp.intro_contingent()
        exp.intro_main()
        exp.run_main()
    except:
        logging.exception('Exception in main, saving data...')
        try:
            exp.save_data()
        except:
            logging.exception('Failed to save data, trying again.')
            exp.emergency_save_data()

if __name__ == '__main__':
    Fire(main)