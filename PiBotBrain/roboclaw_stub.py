# This class implements a subset of the full RoboClaw API as released by
# Ion Motion Control for testing purposes. It allows running our control
# app in the absence of an actual RoboClaw attached to the computer.

# The functional fidelity of this class only needs to be enough to 
# exercise features of the control application.

import random
import serial
import struct
import time

class Roboclaw_stub:
	'Stub of Roboclaw Interface Class'

	def __init__(self):
		# Values that would otherwise be stored in RoboClaw
		self.config = 0
		self.encoderM1 = 0
		self.encoderM2 = 0
		self.encoderModeM1 = 0
		self.encoderModeM2 = 0	
		self.minVoltage = 115
		self.maxVoltage = 360
		self.maxCurrentM1 = 500
		self.maxCurrentM2 = 500
		self.pwmMode = 0
		self.pinS3 = self.pinS4 = self.pinS5 = 0
		self.vpm1 = self.vim1 = self.vdm1 = self.vqppsm1 = 0
		self.vpm2 = self.vim2 = self.vdm2 = self.vqppsm2 = 0
		self.ppm1 = self.pim1 = self.pdm1 = self.pimaxm1 = self.pdeadm1 = self.pminm1 = self.pmaxm1 = 0
		self.ppm2 = self.pim2 = self.pdm2 = self.pimaxm2 = self.pdeadm2 = self.pminm2 = self.pmaxm2 = 0

		# Values used to simulate a virtual encoder that moves in response to
		# motor commands.
		self.m1move = None # None, "vel"ocity, "pos"ition
		self.m1target = None # When "vel" = encoder counts per second. When "pos" = destination encoder.
		self.m1timeStart = None # Value of time.time() when movement started.
		self.m1encStart = None # Value of encoder when movement started.

		self.m2move = None # None, "vel"ocity, "pos"ition
		self.m2target = None # When "vel" = encoder counts per second. When "pos" = destination encoder.
		self.m2timeStart = None # Value of time.time() when movement started.
		self.m2encStart = None # Value of encoder when movement started.

	def ForwardM1(self,address,val):
		if val == 0:
			self.m1move = None
		else:
			self.m1move = "vel"
			self.m1target = val
			self.m1start = time.time()
			self.m1encStart = self.encoderM1
		return True

	def BackwardM1(self,address,val):
		if val == 0:
			self.m1move = None
		else:
			self.m1move = "vel"
			self.m1target = -val
			self.m1start = time.time()
			self.m1encStart = self.encoderM1
		return True

	def ForwardM2(self,address,val):
		if val == 0:
			self.m2move = None
		else:
			self.m2move = "vel"
			self.m2target = val
			self.m2start = time.time()
			self.m2encStart = self.encoderM2
		return True

	def BackwardM2(self,address,val):
		if val == 0:
			self.m2move = None
		else:
			self.m2move = "vel"
			self.m2target = -val
			self.m2start = time.time()
			self.m2encStart = self.encoderM2
		return True

	def ReadEncM1(self,address):
		if self.m1move == "vel":
			self.encoderM1 = int(self.m1encStart + (time.time() - self.m1start)*self.m1target)
		elif self.m1move == "pos":
			# Placeholder - instantly move to target.
			self.encoderM1 = self.m1target
			self.m1move = None
		return (1, self.encoderM1, 0)

	def ReadEncM2(self,address):
		if self.m2move == "vel":
			self.encoderM2 = int(self.m2encStart + (time.time() - self.m2start)*self.m2target)
		elif self.m2move == "pos":
			# Placeholder - instantly move to target.
			self.encoderM2 = self.m2target
			self.m2move = None
		return (1, self.encoderM2, 0)

	def ReadVersion(self,address):
		return (1, "TEST STUB API")

	def SetEncM1(self,address,cnt):
		self.m1move = None
		self.encoderM1 = cnt
		return True

	def SetEncM2(self,address,cnt):
		self.m2move = None
		self.encoderM2 = cnt
		return True

	def SetM1VelocityPID(self,address,p,i,d,qpps):
		self.vpm1 = p, self.vim1 = i, self.vdm1 = d, self.vqppsm1 = qpps
		return True

	def SetM2VelocityPID(self,address,p,i,d,qpps):
		self.vpm2 = p, self.vim2 = i, self.vdm2 = d, self.vqppsm2 = qpps
		return True

	def SpeedM1M2(self,address,m1,m2):
		if m1 == 0:
			self.m1move = None
		else:
			self.m1move = "vel"
			self.m1target = m1
			self.m1start = time.time()
			self.m1encStart = self.encoderM1
		if m2 == 0:
			self.m2move = None
		else:
			self.m2move = "vel"
			self.m2target = m2
			self.m2start = time.time()
			self.m2encStart = self.encoderM2
		return True

	def ReadM1VelocityPID(self,address):
		return (1, self.vpm1, self.vim1, self.vdm1, self.vqppsm1)

	def ReadM2VelocityPID(self,address):
		return (1, self.vpm2, self.vim2, self.vdm2, self.vqppsm2)

	def SetMainVoltages(self,address,min, max):
		self.minVoltage = min
		self.maxVoltage = max
		return True
		
	def ReadMinMaxMainVoltages(self,address):
		return (1, self.minVoltage, self.maxVoltage)

	def SetM1PositionPID(self,address,kp,ki,kd,kimax,deadzone,min,max):
		self.ppm1, self.pim1, self.pdm1, self.pimaxm1, self.pdeadm1, self.pminm1, self.pmaxm1 = kp,ki,kd,kimax,deadzone,min,max
		return True

	def SetM2PositionPID(self,address,kp,ki,kd,kimax,deadzone,min,max):
		self.ppm2, self.pim2, self.pdm2, self.pimaxm2, self.pdeadm2, self.pminm2, self.pmaxm2 = kp,ki,kd,kimax,deadzone,min,max
		return True

	def ReadM1PositionPID(self,address):
		return (1, self.ppm1, self.pim1, self.pdm1, self.pimaxm1, self.pdeadm1, self.pminm1, self.pmaxm1)

	def ReadM2PositionPID(self,address):
		return (1, self.ppm2, self.pim2, self.pdm2, self.pimaxm2, self.pdeadm2, self.pminm2, self.pmaxm2)

	def SpeedAccelDeccelPositionM1M2(self,address,accel1,speed1,deccel1,position1,accel2,speed2,deccel2,position2,buffer):
		return True

	def SetPinFunctions(self,address,S3mode,S4mode,S5mode):
		self.pinS3, self.pinS4, self.pinS5 = S3mode, S4mode, S5mode
		return True

	def ReadPinFunctions(self,address):
		return (1,self.pinS3, self.pinS4, self.pinS5)

	def ReadError(self,address):
		return (1, 0)

	def ReadEncoderModes(self,address):
		return (1, self.encoderModeM1, self.encoderModeM2)
		
	def SetM1EncoderMode(self,address,mode):
		self.encoderModeM1 = mode
		return True

	def SetM2EncoderMode(self,address,mode):
		self.encoderModeM2 = mode
		return True

	def WriteNVM(self,address):
		return True

	def SetConfig(self,address,config):
		self.config = config
		return True

	def GetConfig(self,address):
		return (1, self.config)

	def SetM1MaxCurrent(self,address,max):
		self.maxCurrentM1 = max
		return True;

	def SetM2MaxCurrent(self,address,max):
		self.maxCurrentM2 = max
		return True;

	def ReadM1MaxCurrent(self,address):
		return (1,self.maxCurrentM1)

	def ReadM2MaxCurrent(self,address):
		return (1,self.maxCurrentM2)

	def SetPWMMode(self,address,mode):
		self.pwmMode = mode
		return True;

	def ReadPWMMode(self,address):
		return (1,self.pwmMode)

	def Open(self):
		return 1

