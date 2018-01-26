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

# Parse the given address parameter which may be normal integer or hexadecimal.
# Returns only if value falls in the range of valid Roboclaw addresses.
def tryParseAddress(addressString, default):
	if addressString is None:
		return default

	retVal = None
	try:
		retVal = int(addressString)
	except ValueError:
		try:
			retVal = int(addressString,16)
		except ValueError:
			retVal = None

	if retVal is None or retVal < 128 or retVal > 135:
		return default

	return retVal

# Helper function to be called before each of the user menu is displayed.
# Verifies that a global Roboclaw API object is available and that there
# is a Roboclaw responding at the address parameter.
# If successful, returns a tuple of the Roboclaw API object (which is 
# currently global but that's a bug to be fixed later) and the validated
# address.
# In case of failure, an error message is placed into flash and an exception
# is raised. (ValueError for now, possibly a custom RoboclawError later.)
def checkRoboclawAddress():
	global rc
	# Do we have Roboclaw API object?
	if rc is None:
		flash("Roboclaw API not initialized")
		raise ValueError

	# Do we have a Roboclaw address?
	rcAddr = tryParseAddress(request.args.get('address'), default=None)
	if rcAddr is None:
		flash("Valid address parameter required")
		raise ValueError

	# Is there a Roboclaw at that address?
	versionQuery = rc.ReadVersion(rcAddr)
	if versionQuery[0] == 0:
		flash("No Roboclaw response at {0} ({0:#x})".format(rcAddr))
		raise ValueError

	return (rc, rcAddr)

# Every read operation from the Roboclaw API returns a tuple: index zero
# is 1 for success and 0 for failure. This helper looks for that zero and
# raises an exception if one is seen. If an optional error message was 
# provided, it is put into the flash before exception is raised.
# In the normal case of success, if there was only one other element in
# the resultTuple, that element is returned by itself (not a single
# element tuple) If there are more tha one, the result is a tuple.
def readResult(resultTuple, flashError=None):
	if resultTuple[0] == 0:
		if flashError is not None:
			flash(flashError + " " + str(resultTuple))
		raise ValueError

	if len(resultTuple) == 2:
		return resultTuple[1]
	else:
		return resultTuple[1:]

# Root menu
@app.route('/')
def root_menu():
	if rc is None:
		return redirect(url_for('connect_menu'))
	rcAddr = tryParseAddress(request.args.get('address'), default=None)

	displayMenu = False
	if rcAddr is not None:
		try:
			verString = readResult(rc.ReadVersion(rcAddr))
			roboResponse = "Roboclaw at address {0} ({0:#x}) version: {1}".format(rcAddr, verString)
			displayMenu = True
		except ValueError as ve:
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
		# TODO sanity validation of these values from the HTML form
		portName = request.form['port']
		baudrate = int(request.form['baudrate'])
		interCharTimeout = float(request.form['interCharTimeout'])
		retries = int(request.form['retries'])

		# Create the Roboclaw object against the specified serial port
		newrc = Roboclaw(portName,baudrate,interCharTimeout,retries)
		if newrc.Open():
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
	try:
		rcAndAddr = checkRoboclawAddress()

		# We have Roboclaw API object pointing to a Roboclaw that responds.
		# Delegate further action to the appropriate helper method.
		if request.method == 'GET':
			return config_read(*rcAndAddr)
		elif request.method == 'POST':
			return config_update(*rcAndAddr)
		else:
			flash("Unexpected request method on config")
			return redirect(url_for('config_menu'))
	except ValueError as ve:
		return redirect(url_for('root_menu'))

# Retrieve all the settings so we can show them in the rendered template.
def config_read(rc, rcAddr):
	try:
		rcVersion = readResult(rc.ReadVersion(rcAddr), "Version string")
		VmainMin,VmainMax = readResult(rc.ReadMinMaxMainVoltages(rcAddr), "Main voltage min/max")
		AmaxM1 = readResult(rc.ReadM1MaxCurrent(rcAddr), "Current max motor 1")
		AmaxM2 = readResult(rc.ReadM2MaxCurrent(rcAddr), "Current max motor 2")
		pwmMode = readResult(rc.ReadPWMMode(rcAddr), "PWM mode")
		encModeM1,encModeM2 = readResult(rc.ReadEncoderModes(rcAddr),"Encoder mode")
		s3, s4, s5 = readResult(rc.ReadPinFunctions(rcAddr),"Pin functions")

		# Convert config bitfield to binary representation
		rcConfig = "{0:#b}".format(readResult(rc.GetConfig(rcAddr), "Config"))

		return render_template("config_menu.html", rcVersion=rcVersion, 
			VmainMin=VmainMin, VmainMax=VmainMax, AmaxM1=AmaxM1, AmaxM2=AmaxM2, 
			pwmMode=pwmMode, encModeM1=encModeM1, encModeM2=encModeM2,
			s3=s3, s4=s4, s5=s5, rcConfig=rcConfig, rcAddr=rcAddr)

	except ValueError as ve:
		return redirect(url_for('root_menu'))
	

# Send values to Roboclaw
def config_update(rc, rcAddr):
	return redirect(url_for('config_menu'))
