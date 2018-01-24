from flask import Flask
from roboclaw import Roboclaw

app = Flask(__name__)

@app.route('/')
def hello_world():
	rc = Roboclaw("/dev/ttyACM0",115200)
	rc.Open()
	ver = rc.ReadVersion(0x80)
	return "Hello, Flask World! " + ver[1]