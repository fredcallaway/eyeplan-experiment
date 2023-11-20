from experiment import Experiment
import sys
from fire import Fire

version = 'p3'

def main(participant_id=None, config=None):

    if participant_id is None:
        participant_id = input('participant ID: ') or 'default'
    if config is None:
        config = input('configuration number: ') or 1 + random.choice(range(10))

    exp = Experiment(version, participant_id, config, full_screen=False)

    exp.parameters.update({
        'time_limit': 7,
        'gaze_contingent': True,
        'summarize_every': 10,
    })
    for i, t in enumerate(exp.trials['main']):
        t['gaze_contingent'] = not (i % 3 == 2)

    exp.intro()
    exp.practice(2)
    exp.practice_timelimit()
    exp.setup_eyetracker()
    exp.show_gaze_demo()
    exp.intro_gaze()
    exp.intro_main()
    exp.run_main(100)
    exp.save_data()

if __name__ == '__main__':
    Fire(main)