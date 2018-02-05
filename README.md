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
  - Create new virtual environment `virtualenv venv`
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
