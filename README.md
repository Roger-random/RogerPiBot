# RogerPiBot
Raspberry Pi-driven robot project

---

# PiBotBrain
First attempt at a robot controller, focused on test and configuration tasks.

## Dependencies 
- Written under `python 2.7.14` with associated `pip 9.0.1`. 
  - Python 2 was used because this project originally referenced another RoboClaw control application that was written under Python 2. Expect to write a new Python 3 version later.
- `virtualenv` recommended to help keep Python libraries manageable
  - Install VirtualEnv `pip install virtualenv`
  - Switch to PiBotBrain directory `cd RogerPiBot/PiBotBrain`
  - Create new virtual environment `python -m virtualenv venv`
  - Activate virtual environment `. venv/bin/activate` Command prompt should be prepended with `(venv)` after activation.
- Install Python libraries required for this project
  - Serial port library `pip install pyserial`
  - Flask web framework `pip install flask`
- Copy roboclaw.py from root directory of project
  - `cp ../roboclaw.py .`
  
## Start PiBotBrain
- If not already active, activate virtual environment: `. venv/bin/activate`
- Tell Flask which Python file to run: `export FLASK_APP=testconfig.py`
- (For development purposes only) turn on debug mode: `export FLASK_DEBUG=1`
- Launch Flask: `flask run`
- Open app in web browser. The exact URL is shown when running `flask run`, probably `http://localhost:5000`

## Raspberry Pi: Automatic Launch on Startup
To have a Raspberry Pi (running Raspbian) launch the app on startup:
- Clone this repository and set up virtualenv as above.
- Configure Flask for launch by editing `/etc/rc.local`, adding the following command just above the `exit 0` at the end. (Adjust `/home/pi/RogerPiBot/PiBotBrain` as needed if not cloned into pi user root.)
```
cd /home/pi/RogerPiBot/PiBotBrain
export FLASK_APP=testconfig.py
. venv/bin/activate
flask run &
```
- Configure Chromium browser for launch by editing `/home/pi/.config/lxsession/LXDE-pi/autostart`, adding the following command to the end.
```
@chromium-browser --kiosk http://localhost:5000/
```
- Optional: Turn off screensaver https://www.raspberrypi.org/documentation/configuration/screensaver.md
- Reboot
