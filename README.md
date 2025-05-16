# Software

Start by [installing the SR development tools](https://www.sr-research.com/support/showthread.php?tid=13). If you have a Mac, you might be able to use this installer:

[EyeLinkDevKit_macOS10.12_and_up_v2.1.1197.dmg](attachment:75b2bf92-9d94-45ee-9a4c-adeccbdd0943:EyeLinkDevKit_macOS10.12_and_up_v2.1.1197.dmg)

You will also need HDF5.


Then install the pylink library and psychopy. **NOTE:** I wasn't able to get this to work with Python 3.11, but it did work with Python 3.10. Check out pyenv for a way to manage different versions of Python.

Using a virtual environment is highly recommended.

```bash
python3 -m venv env
. env/bin/activate  # run this every time you open a new terminal window.
```

With the env active, install the Python dependencies

```bash
pip install --index-url=https://pypi.sr-support.com sr-research-pylink
pip install psychopy --no-deps
pip install arabic-reshaper astunparse blosc2 cryptography esprima ffpyplayer freetype-py future gevent gitpython imageio imageio-ffmpeg javascripthon jedi markdown-it-py matplotlib msgpack msgpack-numpy "numpy<2.0" opencv-python openpyxl pandas pillow psutil psychtoolbox "pyglet<2.0" pyobjc pyobjc-core pyobjc-framework-Quartz pypi-search pyqt5 pyserial python-bidi python-gitlab python-vlc pyyaml pyzmq questplus requests scipy setuptools soundfile ujson websockets wxPython xmlschema fire
```


- X during a trial triggers recalibration 
- escape during a drift check triggers the eyelink setup screen
- escape again brings up a screen allowing you to do several things: abort experiment, recalibrate, disable drift checks