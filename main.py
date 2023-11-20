from experiment import Experiment
from fire import Fire

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

    exp.intro()
    exp.practice(2)
    exp.practice_timelimit()
    exp.setup_eyetracker()
    exp.show_gaze_demo()
    exp.intro_gaze()
    exp.intro_main()
    exp.run_main(2)
    exp.save_data()

if __name__ == '__main__':
    Fire(main)