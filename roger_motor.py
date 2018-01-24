from roboclaw import Roboclaw

rc = Roboclaw("/dev/ttyS3", 115200)
rc.Open()
rc.ReadVersion(0x80)

# This is the old API, use the new one below. rc.SetMinVoltageMainBattery(0x80, 110) # 11 Volts
rc.ReadMinMaxMainVoltages(0x80)
rc.SetMainVoltages(0x80, 110, 340) # Allowed range: 11 V - 34 V
rc.SetM1MaxCurrent(0x80, 500) # 5 Amps
rc.SetPWMMode(0x80, 0) # Locked Antiphase
#rc.ReadPWMMode(0x80)
rc.SetM1EncoderMode(0x80, 0) # No RC/Analog support + Quadrature encoder
#rc.ReadEncoderModes(0x80)

getConfig = rc.GetConfig(0x80)
config = getConfig[1] # index zero is 1 for success, 0 for failure.
config = config | 0x0003 # Packet serial mode
config = config | 0x8000 # Multi-Unit mode
rc.SetConfig(0x80, config)

rc.WriteNVM(0x80)

rc.ReadEncM1(0x80)
rc.ResetEncoders(0x80)
rc.ReadEncM1(0x80)

p = 15000
i = 1000
d = 500
qpps = 3000

rc.SetM1VelocityPID(0x80, p, i, d, qpps)
rc.ReadM1VelocityPID(0x80)

rc.SpeedM1(0x80, 250)

rc.ReadM1MaxCurrent(0x80)
rc.ReadCurrents(0x80)


error = rc.ReadError(0x80)[1]
format(error,"08b")

# "Position" API appears to be for times when we want to act like
# a servo motor. Probably not applicable here.
"""
P = 600
I = 0
D = 400

maxI = ?
deadZone = 10
minPos = 0
maxPos = 50000

rc.SetM1PositionPID(0x80, p, i, d, maxI, deadZone, minPos, maxPos)
rc.ReadM1PositionPID(0x80)

accel = 100
speed = 250 #quadrature pulses/sec ?
deccel = 100
position = 1800

rc.SpeedAccelDeccelPositionM1(0x80, accel, speed, deccel, position, 1)

"""

