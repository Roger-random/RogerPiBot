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
def readResult(resultTuple, flashMessage=None):
	if resultTuple[0] == 0:
		if flashMessage is not None:
			flash("ERROR: {} {}".format(flashMessage, str(resultTuple)))
		raise ValueError

	if len(resultTuple) == 2:
		return resultTuple[1]
	else:
		return resultTuple[1:]

# Every write operation returns True if successful. This helper looks for a
# False and raises an exception when it happens. Optional flash message is 
# placed in flash prepended with ERROR or SUCCESS depending on condition.
def writeResult(result, flashMessage=None):
	if not result:
		if flashMessage is not None:
			flash("ERROR: {}".format(flashMessage))
		raise ValueError
	elif flashMessage is not None:
		flash("SUCCESS: {}".format(flashMessage))

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
		rc, rcAddr = checkRoboclawAddress()

		rcVersion = readResult(rc.ReadVersion(rcAddr), "Read version string")
		VmainMin,VmainMax = readResult(rc.ReadMinMaxMainVoltages(rcAddr), "Read main voltage limits")
		AmaxM1 = readResult(rc.ReadM1MaxCurrent(rcAddr), "Read motor 1 max current")
		AmaxM2 = readResult(rc.ReadM2MaxCurrent(rcAddr), "Read motor 2 max current")
		pwmMode = readResult(rc.ReadPWMMode(rcAddr), "Read PWM mode")
		encModeM1,encModeM2 = readResult(rc.ReadEncoderModes(rcAddr),"Read encoder mode")
		s3, s4, s5 = readResult(rc.ReadPinFunctions(rcAddr),"Read pin functions")

		# Convert config bitfield to hex representation
		rcConfig = "{0:#x}".format(readResult(rc.GetConfig(rcAddr), "Read config"))

		if request.method == 'GET':
			return render_template("config_menu.html", rcVersion=rcVersion, 
				VmainMin=VmainMin, VmainMax=VmainMax, AmaxM1=AmaxM1, AmaxM2=AmaxM2, 
				pwmMode=pwmMode, encModeM1=encModeM1, encModeM2=encModeM2,
				s3=s3, s4=s4, s5=s5, rcConfig=rcConfig, rcAddr=rcAddr)
		elif request.method == 'POST':
			# TODO sanity validation of these values from the HTML form
			fVmainMin = int(request.form['VmainMin'])
			fVmainMax = int(request.form['VmainMax'])
			fAmaxM1 = int(request.form['AmaxM1'])
			fAmaxM2 = int(request.form['AmaxM2'])
			fpwmMode = int(request.form['pwmMode'])
			fencModeM1 = int(request.form['encModeM1'])
			fencModeM2 = int(request.form['encModeM2'])
			fs3 = int(request.form['s3'])
			fs4 = int(request.form['s4'])
			fs5 = int(request.form['s5'])
			frcConfig = int(request.form['rcConfig'],16)

			if fVmainMin != VmainMin or fVmainMax != VmainMax:
				writeResult(rc.SetMainVoltages(rcAddr, fVmainMin, fVmainMax), "Update Main voltage limits")

			if fAmaxM1 != AmaxM1:
				writeResult(rc.SetM1MaxCurrent(rcAddr, fAmaxM1), "Update M1 max current")

			if fAmaxM2 != AmaxM2:
				writeResult(rc.SetM2MaxCurrent(rcAddr, fAmaxM2), "Update M2 max current")

			if fpwmMode != pwmMode:
				writeResult(rc.SetPWMMode(rcAddr, fpwmMode), "Update PWM mode")

			if fencModeM1 != encModeM1:
				writeResult(rc.SetM1EncoderMode(rcAddr, fencModeM1), "Update M1 encoder mode")

			if fencModeM2 != encModeM2:
				writeResult(rc.SetM2EncoderMode(rcAddr, fencModeM2), "Update M2 encoder mode")

			if fs3 != s3 or fs4 != s4 or fs5 != s5:
				writeResult(rc.SetPinFunctions(rcAddr, fs3, fs4, fs5), "Update S3/S4/S5 functions")

			if frcConfig != int(rcConfig,16):
				writeResult(rc.SetConfig(rcAddr, frcConfig), "Update config flags")

			return redirect(url_for('config_menu',address=rcAddr))
		else:
			flash("Unexpected request method on config")
			return redirect(url_for('config_menu'))
	except ValueError as ve:
		return redirect(url_for('root_menu'))
