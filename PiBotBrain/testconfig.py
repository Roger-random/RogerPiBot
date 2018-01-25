# App to configure Roboclaw and test PID values

from flask import Flask, flash, g, redirect, render_template, request, url_for
import os
from roboclaw import Roboclaw

app = Flask(__name__)

# Randomly generated key means session cookies will not be usable across 
# instances. This flaw is acceptable for the test config app.
app.secret_key = os.urandom(24)

# Global Roboclaw - this is a terrible idea for web apps in general, but since
# we are catering to a single user instance it is an ugly but sufficient hack.
rc = None

# Root menu
@app.route('/')
def root_menu():
	if rc is None:
		return redirect(url_for('connect_menu'))
	ret = rc.ReadVersion(0x80)
	if ret[0]==1:
		versionText = ret[1]
		return render_template("root_menu.html", version=versionText)
	return "Error encountered reading version from Roboclaw"


# Connect menu let's the user specify serial port parameters for creating
# a Roboclaw object
@app.route('/connect', methods=['GET', 'POST'])
def connect_menu():
	if request.method == 'GET':
		if rc is None:
			return render_template("connect_menu.html")
		else:
			return redirect(url_for('root_menu'))
	elif request.method == 'POST':
		newrc = Roboclaw(request.form['port'],115200)
		ret = newrc.Open()
		if ret == 1:
			global rc
			rc = newrc
			flash("Roboclaw API connected to specified serial port")
			return redirect(url_for('root_menu'))
		else:
			flash("could not open specified port")
			return redirect(url_for('connect_menu'))
	else:
		return "Unexpected method on connect"
