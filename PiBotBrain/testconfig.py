# App to configure Roboclaw and test PID values

from flask import Flask, flash, g, jsonify, redirect, render_template, request, session, url_for
import os
from subprocess import call
from roboclaw import Roboclaw
from roboclaw_stub import Roboclaw_stub

defaultAccelDecel = 2400
defaultSpeed = 240
errorCategory = "error"
successCategory = "success"

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
		msg = "Roboclaw API not initialized"
		flash(msg, errorCategory)
		raise ValueError(msg)

	# Do we have a Roboclaw address?
	rcAddr = tryParseAddress(request.args.get('address'), default=None)
	if rcAddr is None:
		msg = "Valid address parameter required"
		flash(msg, errorCategory)
		raise ValueError(msg)

	# Is there a Roboclaw at that address?
	versionQuery = rc.ReadVersion(rcAddr)
	if versionQuery[0] == 0:
		msg = "No Roboclaw response at {0} ({0:#x})".format(rcAddr)
		flash(msg, errorCategory)
		raise ValueError(msg)

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
		msg = str(resultTuple)
		if flashMessage is not None:
			msg = "{} {}".format(flashMessage, str(resultTuple))
			flash(msg, errorCategory)
		raise ValueError(msg)

	if len(resultTuple) == 2:
		return resultTuple[1]
	else:
		return resultTuple[1:]

# Every write operation returns True if successful. This helper looks for a
# False and raises an exception when it happens. Optional flash message is 
# placed in flash with error or success category as appropriate.
def writeResult(result, flashMessage=None):
	if not result:
		if flashMessage is not None:
			flash(flashMessage, errorCategory)
		raise ValueError(flashMessage)
	elif flashMessage is not None:
		flash(flashMessage, successCategory)

# Roboclaw directly connected on USB usually show up as /dev/ttyACM0
# and sometimes /dev/ttyACM1 on Raspberry Pi & PC. On MacOS it has
# shown up as /dev/ttyusbmodem. In both cases USB serial bridges
# announce themselves as ttyUSB. Put all the possibilities in a list
def potentialDevices():
	return [dev for dev in os.listdir("/dev") if dev.startswith(("ttyACM", "ttyUSB", "tty.usbmodem"))]

# Root menu
@app.route('/')
def root_menu():
	global rc
	if rc is None:
		for device in potentialDevices():
			newrc = Roboclaw("/dev/"+device, 115200, 0.01, 3)
			if newrc.Open():
				rc = newrc
				break
		# Failed to connect to USB, fall back to test stub.
		if rc is None:
			rc = Roboclaw_stub()

	rcAddr = tryParseAddress(request.args.get('address'), default=128)

	displayMenu = False
	if rcAddr is not None:
		try:
			verString = readResult(rc.ReadVersion(rcAddr))
			flash("Roboclaw at address {0} ({0:#x}) version: {1}".format(rcAddr, verString), successCategory)
			displayMenu = True
		except ValueError as ve:
			flash("No Roboclaw response from address {0} ({0:#x})".format(rcAddr), errorCategory)

	else:
		roboResponse = None

	return render_template("root_menu.html", display=displayMenu, address=rcAddr)

# Connect menu lets the user specify serial port parameters for creating
# a Roboclaw object
@app.route('/connect', methods=['GET', 'POST'])
def connect_menu():
	global rc
	if request.method == 'GET':
		return render_template("connect_menu.html", potentialDevices=potentialDevices())
	elif request.method == 'POST':
		# TODO sanity validation of these values from the HTML form
		portName = request.form['port']
		baudrate = int(request.form['baudrate'])
		interCharTimeout = float(request.form['interCharTimeout'])
		retries = int(request.form['retries'])

		if portName == 'Test_Stub':
			# No RoboClaw - use the test stub.
			newrc = Roboclaw_stub()
		else:	
			# Create the Roboclaw object against the specified serial port
			newrc = Roboclaw(portName,baudrate,interCharTimeout,retries)

		if newrc.Open():
			rc = newrc
			flash("Roboclaw API connected to " + portName, successCategory)
			return redirect(url_for('root_menu', address="0x80"))
		else:
			flash("Roboclaw API could not open " + portName, errorCategory)
			return redirect(url_for('connect_menu'))
	else:
		flash("Unexpected request method on connect", errorCategory)
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
			flash("Unexpected request.method on config", errorCategory)
			return redirect(url_for('config_menu',address=rcAddr))
	except ValueError as ve:
		return redirect(url_for('root_menu'))

# Write the current settings to non-volatile memory

@app.route('/writenvm')
def writenvm():
	try:
		rc, rcAddr = checkRoboclawAddress()

		writeResult(rc.WriteNVM(rcAddr), "Write to non-volatile memory")

		return redirect(url_for('root_menu', address=rcAddr))
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

# Allows user to set quadrature encoder count to specified values

@app.route('/encoder', methods=['GET', 'POST'])
def encoder():
	try:
		rc,rcAddr = checkRoboclawAddress()

		m1enc, m1encStatus = readResult(rc.ReadEncM1(rcAddr), "Read M1 encoder")
		m2enc, m2encStatus = readResult(rc.ReadEncM2(rcAddr), "Read M2 encoder")

		if request.method == 'GET':
			return render_template("encoder.html", rcAddr=rcAddr,
				m1enc=m1enc, m1encStatus=m1encStatus,
				m2enc=m2enc, m2encStatus=m2encStatus )
		elif request.method == 'POST':
			# TODO sanity validation of these values from the HTML form
			fm1enc = int(request.form['m1enc'])
			fm2enc = int(request.form['m2enc'])

			if fm1enc != m1enc:
				writeResult(rc.SetEncM1(rcAddr, fm1enc), "Set M1 quadrature encoder count")

			if fm2enc != m2enc:
				writeResult(rc.SetEncM2(rcAddr, fm2enc), "Set M2 quadrature encoder count")

			return redirect(url_for('root_menu', address=rcAddr))
		else:
			flash("Unexpected request.method on encoder", errorCategory)
			return redirect(url_for('encoder',address=rcAddr))

	except ValueError as ve:
		return redirect(url_for('root_menu'))

# Low overhead method to retrieve encoder values as JSON. For the sake of
# simple client, ensure the output JSON is always the same format regardless
# of success or error.

@app.route('/encoder_json', methods=['GET'])
def encoder_json():
	try:
		rc,rcAddr = checkRoboclawAddress()

		m1enc, m1encStatus = readResult(rc.ReadEncM1(rcAddr), "Read M1 encoder")
		m2enc, m2encStatus = readResult(rc.ReadEncM2(rcAddr), "Read M2 encoder")

		return jsonify(m1enc=m1enc, m2enc=m2enc, m1encStatus=m1encStatus, m2encStatus=m2encStatus, result="success")
	except ValueError as ve:
		return jsonify(m1enc=0, m2enc=0, m1encStatus=0, m2encStatus=0, result=str(ve))

# Velocity menu deals with the parameters involved in moving at a target velocity.
# Usually in terms of quadrature encoder pulses per second.

@app.route('/velocity', methods=['GET','POST'])
def velocity_menu():
	try:
		rc,rcAddr = checkRoboclawAddress()

		rcVersion = readResult(rc.ReadVersion(rcAddr), "Read version string")

		m1P, m1I, m1D, m1qpps = readResult(rc.ReadM1VelocityPID(rcAddr), "Read M1 velocity PID")
		m2P, m2I, m2D, m2qpps = readResult(rc.ReadM2VelocityPID(rcAddr), "Read M2 velocity PID")

		# Roboclaw API returns P/I/D as floating point even though it only accepts integers.
		# To remain consistent even when the API is not, turn them to integers.
		m1P = int(m1P)
		m2P = int(m2P)
		m1I = int(m1I)
		m2I = int(m2I)
		m1D = int(m1D)
		m2D = int(m2D)

		m1enc, m1encStatus = readResult(rc.ReadEncM1(rcAddr), "Read M1 encoder")
		m2enc, m2encStatus = readResult(rc.ReadEncM2(rcAddr), "Read M2 encoder")

		m1speed = session.get('m1speed', 0)
		m2speed = session.get('m2speed', 0)

		if request.method == 'GET':
			return render_template("velocity_menu.html", rcVersion=rcVersion, rcAddr=rcAddr,
				m1P=m1P, m1I=m1I, m1D=m1D, m1qpps=m1qpps,
				m2P=m2P, m2I=m2I, m2D=m2D, m2qpps=m2qpps,
				m1enc=m1enc, m1encStatus=m1encStatus,
				m2enc=m2enc, m2encStatus=m2encStatus,
				m1speed=m1speed, m2speed=m2speed)
		elif request.method == 'POST':
			# TODO sanity validation of these values from the HTML form
			fm1P = int(request.form['m1P'])
			fm1I = int(request.form['m1I'])
			fm1D = int(request.form['m1D'])
			fm1qpps = int(request.form['m1qpps'])

			if request.form['m2values'] == 'copym1':
				fm2P = fm1P
				fm2I = fm1I
				fm2D = fm1D
				fm2qpps = fm1qpps
			else:
				fm2P = int(request.form['m2P'])
				fm2I = int(request.form['m2I'])
				fm2D = int(request.form['m2D'])
				fm2qpps = int(request.form['m2qpps'])

			if fm1P != m1P or fm1I != m1I or fm1D != m1D or fm1qpps != m1qpps:
				writeResult(rc.SetM1VelocityPID(rcAddr, fm1P, fm1I, fm1D, fm1qpps), "Update M1 velocity PID")

			if fm2P != m2P or fm2I != m2I or fm2D != m2D or fm2qpps != m2qpps:
				writeResult(rc.SetM2VelocityPID(rcAddr, fm2P, fm2I, fm2D, fm2qpps), "Update M2 velocity PID")

			return redirect(url_for('velocity_menu',address=rcAddr))
		else:
			flash("Unexpected request.method on velocity", errorCategory)
			return redirect(url_for('velocity_menu',address=rcAddr))
	except ValueError as ve:
		return redirect(url_for('root_menu'))

@app.route('/run_velocity', methods=['POST'])
def run_velocity():
	try:
		rc,rcAddr = checkRoboclawAddress()

		session['m1speed'] = m1speed = int(request.form['m1speed'])
		session['m2speed'] = m2speed = int(request.form['m2speed'])

		writeResult(rc.SpeedM1M2(rcAddr, m1speed, m2speed), "Run M1+M2 at velocity")

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

		m1enc, m1encStatus = readResult(rc.ReadEncM1(rcAddr), "Read M1 encoder")
		m2enc, m2encStatus = readResult(rc.ReadEncM2(rcAddr), "Read M2 encoder")
		m1accel = session.get('m1accel', defaultAccelDecel)
		m2accel = session.get('m2accel', defaultAccelDecel)
		m1speed = session.get('m1speed', defaultSpeed)
		m2speed = session.get('m2speed', defaultSpeed)
		m1decel = session.get('m1decel', defaultAccelDecel)
		m2decel = session.get('m2decel', defaultAccelDecel)
		m1pos = session.get('m1pos', 0)
		m2pos = session.get('m2pos', 0)

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
				m1pos=m1pos, m2pos=m2pos)
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
			flash("Unexpected request.method on position", errorCategory)
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

		session['m1pos'] = m1pos = int(request.form['m1pos'])
		session['m2pos'] = m2pos = int(request.form['m2pos'])

		writeResult(rc.SpeedAccelDeccelPositionM1M2(rcAddr, 
			m1accel, m1speed, m1decel, m1pos, 
			m2accel, m2speed, m2decel, m2pos, 1),
			"Moving to position (M1 {0} {1} {2} {3}) (M2 {4} {5} {6} {7})".format(
				m1accel, m1speed, m1decel, m1pos, 
				m2accel, m2speed, m2decel, m2pos))

		return redirect(url_for('position_menu',address=rcAddr))
	except ValueError as ve:
		return redirect(url_for('root_menu'))

# "Drive" presents a more user-friendly way to drive the robot around,
# not the big table of numerical inputs of the config/velocity/position menus.

@app.route('/drive_control', methods=['GET','POST'])
def drive_control():
	try:
		rc,rcAddr = checkRoboclawAddress()

		speed = session.get('speed', 300)
		eppr = session.get('eppr', 6200)

		if request.method == 'GET':
			return render_template("drive_control.html", rcAddr=rcAddr,
				speed=speed, eppr=eppr)
		elif request.method == 'POST':
			encoderSet = 250000
			m1delta = m2delta = 0
			session['speed'] = speed = int(request.form['speed'])
			if request.form['movement'] == "linear":
				distance = int(request.form['distanceNumber'])
				m1delta = m2delta = distance * 7200
			elif request.form['movement'] == "rotation":
				session['eppr'] = eppr = int(request.form['rotationPulses'])
				rotation = int(request.form['rotationNumber'])
				m1delta = int(rotation * eppr / 360)
				m2delta = -m1delta
			else:
				flash("Unknown movement type", errorCategory)

			m1accel = session.get('m1accel', defaultAccelDecel)
			m2accel = session.get('m2accel', defaultAccelDecel)
			m1decel = session.get('m1decel', defaultAccelDecel)
			m2decel = session.get('m2decel', defaultAccelDecel)

			writeResult(rc.SetEncM1(rcAddr, encoderSet), "Set M1 quadrature encoder count")
			writeResult(rc.SetEncM2(rcAddr, encoderSet), "Set M2 quadrature encoder count")

			m1pos = encoderSet + m1delta
			m2pos = encoderSet + m2delta

			writeResult(rc.SpeedAccelDeccelPositionM1M2(rcAddr, 
				m1accel, speed, m1decel, m1pos, 
				m2accel, speed, m2decel, m2pos, 1),
				"Moving to position (M1 {0} {1} {2} {3}) (M2 {4} {5} {6} {7})".format(
					m1accel, speed, m1decel, m1pos, 
					m2accel, speed, m2decel, m2pos))

			return redirect(url_for('drive_control',address=rcAddr))
		else:
			flash("Unexpected request.method on drive_control", errorCategory)
			return redirect(url_for('drive_control',address=rcAddr))
	except ValueError as ve:
		return redirect(url_for('root_menu'))


@app.route('/basic_motor', methods=['GET','POST'])
def basic_motor():
	try:
		rc,rcAddr = checkRoboclawAddress()

		m1enc, m1encStatus = readResult(rc.ReadEncM1(rcAddr), "Read M1 encoder")
		m2enc, m2encStatus = readResult(rc.ReadEncM2(rcAddr), "Read M2 encoder")

		if request.method == 'GET':
			return render_template("basic_motor.html", rcAddr=rcAddr,
				m1enc=m1enc, m2enc=m2enc, m1encStatus=m1encStatus, m2encStatus=m2encStatus)
		elif request.method == 'POST':
			motor = int(request.form['motor'])
			direction = request.form['direction']

			if motor == 1:
				if direction == '+':
					rc.ForwardM1(rcAddr, 50)
				elif direction == '-':
					rc.BackwardM1(rcAddr, 50)
				else:
					rc.ForwardM1(rcAddr, 0)
			else:
				if direction == '+':
					rc.ForwardM2(rcAddr, 50)
				elif direction == '-':
					rc.BackwardM2(rcAddr, 50)
				else:
					rc.ForwardM2(rcAddr, 0)

			return redirect(url_for('basic_motor',address=rcAddr))
		else:
			flash("Unexpected request.method on drive_control", errorCategory)
			return redirect(url_for('basic_motor',address=rcAddr))
	except ValueError as ve:
		return redirect(url_for('root_menu'))

@app.route('/shutdown')
def call_shutdown():
	r = call("systemctl poweroff", shell=True)
	if r == 0:
		flash("Shutting down...", successCategory)
	else:
		flash("Shutdown attempt failed with error {0}".format(r), errorCategory)
	return redirect(url_for('root_menu'))
