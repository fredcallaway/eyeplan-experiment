from experiment import Experiment

exp = Experiment('fred', full_screen=False)
exp.trials['main'] = exp.trials['main'][0:10]
# exp.intro()
exp.practice()
# exp.setup_eyetracker()
# exp.show_gaze_demo()
exp.intro_main()
exp.run_main()
exp.save_data()
# todo save the bonus!
# jonathan did the first 6 trials