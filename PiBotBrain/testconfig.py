# App to configure Roboclaw and test PID values

from flask import Flask, flash, g, redirect, render_template, request, session, url_for
import os
from roboclaw import Roboclaw

defaultAccelDecel = 2400
defaultSpeed = 240
errorPrefix = "ERROR: "
successPrefix = "SUCCESS: "

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
		flash(errorPrefix + "Roboclaw API not initialized")
		raise ValueError

	# Do we have a Roboclaw address?
	rcAddr = tryParseAddress(request.args.get('address'), default=None)
	if rcAddr is None:
		flash(errorPrefix + "Valid address parameter required")
		raise ValueError

	# Is there a Roboclaw at that address?
	versionQuery = rc.ReadVersion(rcAddr)
	if versionQuery[0] == 0:
		flash(errorPrefix + "No Roboclaw response at {0} ({0:#x})".format(rcAddr))
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
			flash(errorPrefix + "{} {}".format(flashMessage, str(resultTuple)))
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
			flash(errorPrefix + flashMessage)
		raise ValueError
	elif flashMessage is not None:
		flash(successPrefix + flashMessage)

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
			flash(successPrefix + "Roboclaw API connected to " + portName)
			return redirect(url_for('root_menu', address="0x80"))
		else:
			flash(errorPrefix + "Roboclaw API could not open " + portName)
			return redirect(url_for('connect_menu'))
	else:
		flash(errorPrefix + "Unexpected request method on connect")
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
			return render_template("config_menu.html", rcVersion=rcVersion, rcAddr=rcAddr, 
				VmainMin=VmainMin, VmainMax=VmainMax, AmaxM1=AmaxM1, AmaxM2=AmaxM2, 
				pwmMode=pwmMode, encModeM1=encModeM1, encModeM2=encModeM2,
				s3=s3, s4=s4, s5=s5, rcConfig=rcConfig)
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

			configUpdated = False

			if fVmainMin != VmainMin or fVmainMax != VmainMax:
				writeResult(rc.SetMainVoltages(rcAddr, fVmainMin, fVmainMax), "Update Main voltage limits")
				configUpdated = True

			if fAmaxM1 != AmaxM1:
				writeResult(rc.SetM1MaxCurrent(rcAddr, fAmaxM1), "Update M1 max current")
				configUpdated = True

			if fAmaxM2 != AmaxM2:
				writeResult(rc.SetM2MaxCurrent(rcAddr, fAmaxM2), "Update M2 max current")
				configUpdated = True

			if fpwmMode != pwmMode:
				writeResult(rc.SetPWMMode(rcAddr, fpwmMode), "Update PWM mode")
				configUpdated = True

			if fencModeM1 != encModeM1:
				writeResult(rc.SetM1EncoderMode(rcAddr, fencModeM1), "Update M1 encoder mode")
				configUpdated = True

			if fencModeM2 != encModeM2:
				writeResult(rc.SetM2EncoderMode(rcAddr, fencModeM2), "Update M2 encoder mode")
				configUpdated = True

			if fs3 != s3 or fs4 != s4 or fs5 != s5:
				writeResult(rc.SetPinFunctions(rcAddr, fs3, fs4, fs5), "Update S3/S4/S5 functions")
				configUpdated = True

			if frcConfig != int(rcConfig,16):
				writeResult(rc.SetConfig(rcAddr, frcConfig), "Update config flags")
				configUpdated = True

			if configUpdated:
				writeResult(rc.WriteNVM(rcAddr), "Write to non-volatile memory")
				writeResult(rc.SetM1VelocityPID(0x80, 15000, 1000, 500, 3000), "Update M1 velocity PID")
				writeResult(rc.SetM2VelocityPID(0x80, 15000, 1000, 500, 3000), "Update M2 velocity PID")

			return redirect(url_for('config_menu',address=rcAddr))
		else:
			flash(errorPrefix + "Unexpected request.method on config")
			return redirect(url_for('config_menu',address=rcAddr))
	except ValueError as ve:
		return redirect(url_for('root_menu'))

# Software option to stop both motors connected to a Roboclaw at the
# specified address. This is not a substitute for a hardware E-stop, which
# would be faster and more reliable.

@app.route('/stop')
def stop():
	try:
		rc,rcAddr = checkRoboclawAddress()

		writeResult(rc.ForwardM1(rcAddr, 0), "Stop motor 1")
		writeResult(rc.ForwardM2(rcAddr, 0), "Stop motor 2")

		return render_template("stop.html", rcAddr=rcAddr)
	except ValueError as ve:
		return redirect(url_for('root_menu'))

# Retrieves the current error code from Roboclaw. Zero means no
# error, decoding nonzero value for the user is a future feature.

@app.route('/rc_error')
def rc_error():
	try:
		rc,rcAddr = checkRoboclawAddress()

		errorCode = readResult(rc.ReadError(rcAddr), "Retrieve error code")

		return render_template("rc_error.html", rcAddr=rcAddr, errorCode=errorCode)
	except ValueError as ve:
		return redirect(url_for('root_menu'))

# Velocity menu deals with the parameters involved in moving at a target velocity.
# Usually in terms of quadrature encoder pulses per second.

@app.route('/velocity', methods=['GET','POST'])
def velocity_menu():
	try:
		rc,rcAddr = checkRoboclawAddress()

		m1P, m1I, m1D, m1qpps = readResult(ReadM1VelocityPID(rcAddr))
		m2P, m2I, m2D, m2qpps = readResult(ReadM2VelocityPID(rcAddr))

		# Roboclaw API returns P/I/D as floating point even though it only accepts integers.
		# To remain consistent even when the API is not, turn them to integers.
		m1P = int(m1P)
		m2P = int(m2P)
		m1I = int(m1I)
		m2I = int(m2I)
		m1D = int(m1D)
		m2D = int(m2D)

		m1enc, m1encStatus = readResult(rc.ReadEncM1(rcAddr), "Read M1 Encoder")
		m2enc, m2encStatus = readResult(rc.ReadEncM2(rcAddr), "Read M2 encoder")

		if request.method == 'GET':
			return("Velocity menu  not yet implemented, placeholder only.")
		elif request.method == 'POST':
			flash(errorPrefix + "Velocity POST not yet implemented, placeholder only.")
			return redirect(url_for('velocity_menu',address=rcAddr))
		else:
			flash(errorPrefix + "Unexpected request.method on velocity")
			return redirect(url_for('velocity_menu',address=rcAddr))
	except ValueError as ve:
		return redirect(url_for('root_menu'))


# Position menu deals with the parameters involved in moving to a target position.
# With min/max values, it implies positional application like a RC servo motor.

@app.route('/position', methods=['GET','POST'])
def position_menu():
	try:
		rc,rcAddr = checkRoboclawAddress()

		rcVersion = readResult(rc.ReadVersion(rcAddr), "Read version string")
		m1P, m1I, m1D, m1maxI, m1deadZone, m1minPos, m1maxPos = readResult(rc.ReadM1PositionPID(rcAddr), "Read M1 position PID")
		m2P, m2I, m2D, m2maxI, m2deadZone, m2minPos, m2maxPos = readResult(rc.ReadM2PositionPID(rcAddr), "Read M2 position PID")

		# Roboclaw API returns P/I/D as floating point even though it only accepts integers.
		# To remain consistent even when the API is not, turn them to integers.
		m1P = int(m1P)
		m2P = int(m2P)
		m1I = int(m1I)
		m2I = int(m2I)
		m1D = int(m1D)
		m2D = int(m2D)

		m1enc, m1encStatus = readResult(rc.ReadEncM1(rcAddr), "Read M1 Encoder")
		m2enc, m2encStatus = readResult(rc.ReadEncM2(rcAddr), "Read M2 encoder")
		m1accel = session.get('m1accel', defaultAccelDecel)
		m2accel = session.get('m2accel', defaultAccelDecel)
		m1speed = session.get('m1speed', defaultSpeed)
		m2speed = session.get('m2speed', defaultSpeed)
		m1decel = session.get('m1decel', defaultAccelDecel)
		m2decel = session.get('m2decel', defaultAccelDecel)
		m1posA = session.get('m1posA', 0)
		m1posB = session.get('m1posB', 0)
		m2posA = session.get('m2posA', 0)
		m2posB = session.get('m2posB', 0)

		if request.method == 'GET':
			return render_template("position_menu.html", rcVersion=rcVersion, rcAddr=rcAddr,
				m1P=m1P, m1I=m1I, m1D=m1D, m1maxI=m1maxI, 
				m1deadZone=m1deadZone, m1minPos=m1minPos, m1maxPos=m1maxPos,
				m2P=m2P, m2I=m2I, m2D=m2D, m2maxI=m2maxI, 
				m2deadZone=m2deadZone, m2minPos=m2minPos, m2maxPos=m2maxPos,
				m1enc=m1enc, m1encStatus=m1encStatus,
				m2enc=m2enc, m2encStatus=m2encStatus,
				m1accel=m1accel, m1decel=m1decel, m1speed=m1speed,
				m2accel=m2accel, m2decel=m2decel, m2speed=m2speed,
				m1posA=m1posA, m1posB=m1posB,
				m2posA=m2posA, m2posB=m2posB)
		elif request.method == 'POST':
			# TODO sanity validation of these values from the HTML form
			fm1P = int(request.form['m1P'])
			fm1I = int(request.form['m1I'])
			fm1D = int(request.form['m1D'])
			fm1maxI = int(request.form['m1maxI'])
			fm1deadZone = int(request.form['m1deadZone'])
			fm1minPos = int(request.form['m1minPos'])
			fm1maxPos = int(request.form['m1maxPos'])

			if request.form['m2values']=="copym1":
				fm2P = fm1P
				fm2I = fm1I
				fm2D = fm1D
				fm2maxI = fm1maxI
				fm2deadZone = fm1deadZone
				fm2minPos = fm1minPos
				fm2maxPos = fm1maxPos
			else:
				fm2P = int(request.form['m2P'])
				fm2I = int(request.form['m2I'])
				fm2D = int(request.form['m2D'])
				fm2maxI = int(request.form['m2maxI'])
				fm2deadZone = int(request.form['m2deadZone'])
				fm2minPos = int(request.form['m2minPos'])
				fm2maxPos = int(request.form['m2maxPos'])

			if fm1P != m1P or fm1I != m1I or fm1D != m1D or fm1maxI != m1maxI or fm1deadZone != m1deadZone or fm1minPos != m1minPos or fm1maxPos != m1maxPos:
			   writeResult(rc.SetM1PositionPID(rcAddr, fm1P, fm1I, fm1D, fm1maxI, 
			   	fm1deadZone, fm1minPos, fm1maxPos), "Update M1 Position PID")

			if fm2P != m2P or fm2I != m2I or fm2D != m2D or fm2maxI != m2maxI or fm2deadZone != m2deadZone or fm2minPos != m2minPos or fm2maxPos != m2maxPos:
			   writeResult(rc.SetM2PositionPID(rcAddr, fm2P, fm2I, fm2D, fm2maxI, 
			   	fm2deadZone, fm2minPos, fm2maxPos), "Update M2 Position PID")

			return redirect(url_for('position_menu',address=rcAddr))
		else:
			flash(errorPrefix + "Unexpected request.method on position")
			return redirect(url_for('position_menu',address=rcAddr))
	except ValueError as ve:
		return redirect(url_for('root_menu'))

# Tell Roboclaw to move with the given acceleration, deceleration, and position.
@app.route('/to_position', methods=['POST'])
def to_position():
	try:
		rc,rcAddr = checkRoboclawAddress()

		# TODO sanity validation of these values from the HTML form
		# Pull values from form, update them in session dictionary.
		session['m1accel'] = m1accel = int(request.form['m1accel'])		
		session['m2accel'] = m2accel = int(request.form['m2accel'])
		session['m1speed'] = m1speed = int(request.form['m1speed'])
		session['m2speed'] = m2speed = int(request.form['m2speed'])
		session['m1decel'] = m1decel = int(request.form['m1decel'])
		session['m2decel'] = m2decel = int(request.form['m2decel'])

		target = request.form['target']

		if target == 'a':
			session['m1posA'] = m1pos = int(request.form['m1posA'])
			session['m2posA'] = m2pos = int(request.form['m2posA'])
		elif target == 'b':
			session['m1posB'] = m1pos = int(request.form['m1posB'])
			session['m2posB'] = m2pos = int(request.form['m2posB'])
		else:
			flash(errorPrefix + "Invalid target")
			raise ValueError

		writeResult(rc.SpeedAccelDeccelPositionM1M2(rcAddr, 
			m1accel, m1speed, m1decel, m1pos, 
			m2accel, m2speed, m2decel, m2pos, 1),
			"Moving to position (M1 {0} {1} {2} {3}) (M2 {4} {5} {6} {7})".format(
				m1accel, m1speed, m1decel, m1pos, 
				m2accel, m2speed, m2decel, m2pos))

		return redirect(url_for('position_menu',address=rcAddr))
	except ValueError as ve:
		return redirect(url_for('root_menu'))
