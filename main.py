from experiment import Experiment
import sys

if len(sys.argv) > 1:
    participant_id = sys.argv[1]
else:
    participant_id = input('participant ID: ')
if not participant_id:
    participant_id = 'default'

exp = Experiment('p2', participant_id, full_screen=False)
exp.parameters.update({
    'time_limit': 7,
    'gaze_contingent': True
})

exp.intro()
exp.practice(2)
exp.practice_timelimit()
exp.setup_eyetracker()
exp.show_gaze_demo()
exp.intro_gaze()
exp.intro_main()
exp.run_main(10)
exp.save_data()
