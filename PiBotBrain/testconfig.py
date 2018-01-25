# App to configure Roboclaw and test PID values

from flask import Flask, g, redirect, render_template, url_for
from roboclaw import Roboclaw

app = Flask(__name__)

@app.route('/')
def root_menu():
	rc = getattr(g, 'roboclaw', None)
	if rc is None:
		return redirect(url_for('connect_menu'))
	return render_template("root_menu.html")

# Connect menu let's the user specify serial port parameters for creating
# a Roboclaw object

@app.route('/connect')
def connect_menu():
	rc = getattr(g, 'roboclaw', None)
	if rc is None:
		return render_template("connect_menu.html")
	else:
		return redirect(url_for('root_menu'))
