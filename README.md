
## Setup

```
python3 -m venv env
. env/bin/activate
pip install -r requirements.txt
```

You are likely to run into problems installing psychopy as it has many dependencies. The most common issue is caused by not having HDF5 installed, which leads to a pip error when installing the tables package. The solution to this is to install HDF5. 

- install homebrew (https://brew.sh/) if you don't already have it
- `brew install hdf5`

The experiment is only known to work with Python 3.10 running on macOS.

## Running the experiment

Make sure the virtual environment is active: `. env/bin/activate`

Run the experiment with `python main.py --test`. Some useful flags are:
- `--test` runs in test mode (always do this if you're not running a real participant)
- `--scale 0.5` scales down the window by 50% (useful on a laptop)
- `--full` use full screen in test mode (always full screen in normal mode)
- `--mouse` don't try to connect to an EyeLink device, uses the mouse as gaze position
- `--skip-survey` does what you think
- other flags get passed to Experiment

## Code structure

- main.py defines the CLI and the block-structure of the experiment
- experiment.py handles configuration, setup, and data saving
- `@stage` methods in experiment.py define content of the blocks
- trial.py defines the actual task. The `run` method is the entry point.
- graphics.py defines a more user-friendly graphics interface
- eyetracking.py handles communication with an EyeLink eyetracker

## Key commands while running the experiment

- X during a trial triggers recalibration 
- escape during a drift check triggers the eyelink setup screen
- escape again brings up a screen where you can abort the experiment, recalibrate, or disable drift checks