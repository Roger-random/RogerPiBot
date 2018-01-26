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

def tryParseAddress(addressString, default):
	if addressString is None:
		return default

	try:
		retVal = int(addressString)
	except ValueError:
		try:
			retVal = int(addressString,16)
		except ValueError:
			retVal = default
	return retVal

# Root menu
@app.route('/')
def root_menu():
	if rc is None:
		return redirect(url_for('connect_menu'))
	rcAddr = tryParseAddress(request.args.get('address'), default=None)

	displayMenu = False
	if rcAddr is not None:
		ret = rc.ReadVersion(rcAddr)
		if ret[0]==1:
			roboResponse = "Roboclaw at address {0} ({0:#x}) version: {1}".format(rcAddr, ret[1])
			displayMenu = True
		else:
			roboResponse = "No Roboclaw response from address {0} ({0:#x})".format(rcAddr)
	else:
		roboResponse = None

	return render_template("root_menu.html", response=roboResponse, display=displayMenu, address=rcAddr)


# Connect menu let's the user specify serial port parameters for creating
# a Roboclaw object
@app.route('/connect', methods=['GET', 'POST'])
def connect_menu():
	global rc
	if request.method == 'GET':
		if rc is None:
			return render_template("connect_menu.html")
		else:
			return redirect(url_for('root_menu'))
	elif request.method == 'POST':
		portName = request.form['port']
		baudrate = int(request.form['baudrate'])
		interCharTimeout = float(request.form['interCharTimeout'])
		retries = int(request.form['retries'])
		newrc = Roboclaw(portName,baudrate,interCharTimeout,retries)
		ret = newrc.Open()
		if ret == 1:
			rc = newrc
			flash("Roboclaw API connected to " + portName)
			return redirect(url_for('root_menu', address="0x80"))
		else:
			flash("Roboclaw API could not open " + portName)
			return redirect(url_for('connect_menu'))
	else:
		flash("Unexpected request method on connect")
		return redirect(url_for('connect_menu'))

# Config menu pulls down the current values of the general settings we care 
# about and lets the user put in new ones.
@app.route('/config', methods=['GET', 'POST'])
def config_menu():
	global rc
	if rc is None:
		return redirect(url_for('root_menu'))

	rcAddr = tryParseAddress(request.args.get('address'), default=None)

	if rcAddr is not None:
		if request.method == 'GET':
			return config_read()
		elif request.method == 'POST':
			return config_update()
		else:
			return redirect(url_for('config_menu'))
	else:
		return redirect(url_for('root_menu'))

# Retrieve all the settings so we can show them in the rendered template.
def config_read():
	return "Placeholder - Roboclaw configurations"

# Send values to Roboclaw
def config_update():
	return redirect(url_for('config_menu'))
