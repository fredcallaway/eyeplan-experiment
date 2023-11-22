from experiment import Experiment
from fire import Fire
import logging

from config import VERSION

def main(participant_id=None, config=None, test=False, fast=False):

    if test:
        participant_id = participant_id or 'test'
        config = config or 1
    if participant_id is None:
        participant_id = input('participant ID: ') or 'default'
    if config is None:
        config = input('configuration number: ') or 1 + random.choice(range(10))
        config = int(config)

    exp = Experiment(VERSION, participant_id, config, full_screen=not test)
    try:
        if fast:
            exp.setup_eyetracker()
            exp.show_gaze_demo()
            exp.intro_gaze()
            exp.intro_main()
            exp.run_main(5)
        else:
            exp.intro()
            exp.practice(2)
            exp.practice_timelimit()
            exp.setup_eyetracker()
            exp.show_gaze_demo()
            exp.intro_gaze()
            exp.intro_main()
            exp.run_main()

        exp.save_data()
    except:
        exp.win.clearAutoDraw()
        exp.win.showMessage("Drat! The experiment has encountered an error.\nPlease inform the experimenter.")
        exp.win.flip()
        logging.exception('oh no!')
        exp.save_data()
        raise


if __name__ == '__main__':
    Fire(main)