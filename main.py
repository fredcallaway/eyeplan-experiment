from experiment import Experiment
from fire import Fire
import logging

def main(config_number=None, name=None, test=False, fast=False, full=False, mouse=False, block=None, initial_score=None, **kws):
    if test and name is None:
        name = 'test'
    if fast:
        kws['score_limit'] = 10
    exp = Experiment(config_number, name, full_screen=(not test) or full, **kws)
    if test:
        if test == 'survey':
            exp.save_data(survey=True)
        elif test == 'main':
            exp.run_main()
        else:
            # exp.intro()
            # exp.practice_start()
            exp.practice(2)
            # exp.practice_timelimit()
            exp.setup_eyetracker(mouse)
            exp.show_gaze_demo()
            exp.intro_gaze()
            exp.calibrate_gaze_tolerance()
            exp.intro_contingent()
            exp.intro_main()
            exp.run_main()
            # exp.do_survey()
            # exp.save_data()
        return
    else:
        try:
            if fast:
                exp.intro()
                exp.practice_start()
                exp.practice(1)
                exp.setup_eyetracker(mouse)
                exp.show_gaze_demo()
                exp.intro_gaze()
                exp.calibrate_gaze_tolerance()
                exp.intro_contingent()
                exp.intro_main()
                exp.run_main()
                # exp.do_survey()
            elif block:
                if initial_score:
                    exp.total_score = initial_score
                blocks = [
                    'intro'
                    'practice_start'
                    'practice'
                    'setup_eyetracker'
                    'show_gaze_demo'
                    'intro_gaze'
                    'calibrate_gaze_tolerance'
                    'intro_contingent'
                    'intro_main'
                    'run_main'
                ]
                # Start Generation Here
                try:
                    start = blocks.index(block)
                    for b in blocks[start:]:
                        getattr(exp, b)()
                except ValueError:
                    logging.error(f"Block '{block}' not found in blocks list.")

            else:
                exp.intro()
                exp.practice_start()
                exp.practice(2)
                exp.setup_eyetracker(mouse)
                exp.show_gaze_demo()
                exp.intro_gaze()
                exp.calibrate_gaze_tolerance()
                exp.intro_contingent()
                exp.intro_main()
                exp.run_main()

            exp.save_data(survey=True)
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