from experiment import Experiment
from fire import Fire
import logging

version = 'p3'

def main(participant_id=None, config=None, test=False):

    if test:
        participant_id = participant_id or 'test'
        config = config or 1
    if participant_id is None:
        participant_id = input('participant ID: ') or 'default'
    if config is None:
        config = input('configuration number: ') or 1 + random.choice(range(10))
        config = int(config)

    exp = Experiment(version, participant_id, config, full_screen=not test)
    try:
        exp.intro()
        exp.practice(2)
        exp.practice_timelimit()
        exp.setup_eyetracker()
        exp.show_gaze_demo()
        exp.intro_gaze()
        exp.intro_main()
        exp.run_main(100)
        exp.save_data()
    except:
        exp.win.clearAutoDraw()
        exp.win.showMessage("Drat! The experiment has encountered an error.\nPlease inform the experimenter.")
        exp.win.flip()
        logging.exception('oh no!')
        import IPython, time; IPython.embed(); time.sleep(0.5)
        exp.win.showMessage(None)
        raise


if __name__ == '__main__':
    Fire(main)