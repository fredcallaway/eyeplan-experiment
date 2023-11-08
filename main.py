from experiment import Experiment
exp = Experiment('test', full_screen=False)
exp.parameters.update({
    'time_limit': 7,
    'gaze_contingent': True
})

exp.intro()
exp.practice(2)
exp.practice_timelimit()
# exp.setup_eyetracker()
# exp.show_gaze_demo()
# exp.intro_gaze()
# exp.intro_main()
# exp.run_main(10)
# exp.save_data()
