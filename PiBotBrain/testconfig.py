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
	addrParam = request.args.get('address')
	rcAddr = tryParseAddress(addrParam, 0x80)
	ret = rc.ReadVersion(rcAddr)
	if ret[0]==1:
		versionText = ret[1]
		return render_template("root_menu.html", version=versionText)
	else:
		flash("No Roboclaw responded at address " + str(rcAddr) + " (" + hex(rcAddr) + ")")
		return redirect(url_for('root_menu'))


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
		portName = request.form['port']
		newrc = Roboclaw(portName,115200)
		ret = newrc.Open()
		if ret == 1:
			global rc
			rc = newrc
			flash("Roboclaw API connected to " + portName)
			return redirect(url_for('root_menu', address="0x81"))
		else:
			flash("Roboclaw API could not open " + portName)
			return redirect(url_for('connect_menu'))
	else:
		return "Unexpected method on connect"
