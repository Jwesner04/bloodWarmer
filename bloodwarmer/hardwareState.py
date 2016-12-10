
#imports
import math
import struct
from PyQt4 import QtCore
from arduinoComm import arduinoComm

NACK = 0x15 #No acknowledge packet

#--------------------Commands--------------------#
STATUS_REQUEST = 0x07 #Returns status of all hardware

#The following commands issue a status request in
#addition to their particular function

"""
Sets motor duty cycle
Accepted values: 0-255
D = MOTOR_DUTY_SET_VALUE/255
"""
MOTOR_DUTY_SET = 0x08

"""
Sets fan duty cycle
Accepted values: 0-255
D = FAN_DUTY_SET_VALUE/255
"""
FAN_DUTY_SET = 0x09

"""
Turns fan on/off (Active low)
On = 0
Off = 1
"""
FAN_POWER_SET = 0x0A

""""
Sets heater duty cycle
Accepted values: 0-255
D = HEATER_DUTY_SET_VALUE/255
"""
HEATER_DUTY_SET = 0x0B

"""
Sets frequency of pwm pins
Accepted values: 11-15
Command values correspond to the following frequencies:
11 => 31.250kHz
12 => 3.906kHz
13 => 488Hz
14 => 122Hz
15 => 30.5Hz
"""
FREQ_SET = 0x0C

#--------Temp Sensor calibration offsets---------#
BAG11_CAL = -0.1
BAG12_CAL = -0.2
BAG21_CAL = -0.1
BAG22_CAL = -0.2
#------------------------------------------------#



"""----------------------------------------------------------------------------
 Class Description: Model of blood warmer hardware, provides status of IO and
                    interrupts controller/gui on update
 Last Edited: 11/28/2016
 Last Edited By: Pete Wirges
 Changelog: -1.0.0: Created properties, functions to send command to comm link,
                    parse updates from comm link, push temperatures to gui
            -1.0.1: Added temperature averaging, modified signal emitted to notify
                    controller rather than update gui, commented file
            -1.0.2: Updated to include fan power control/status
            -1.0.3: Updated timer callback function (sendCmd) to send all commands,
                    added setCmd slot that receives commands from controller thread
                    and sets the next cmd to send.  This way there won't be multiple
                    sendCmd requests and all commands will execute at a fixed interval,
                    fixed bug in commands
			-1.0.4: Reconfigured to run in controller
----------------------------------------------------------------------------"""
class hardwareState(QtCore.QObject):

    #Signal to notify controller of status update
    systemError = QtCore.pyqtSignal()
    
    def __init__(self, runCmd = 0, cmdType = STATUS_REQUEST, cmdValue = 0x00, checksum = 0x00, upSwitch = 0x00, downSwitch = 0x00, selectSwitch = 0x00, backSwitch = 0x00, pressureSwitch1 = 0x00, pressureSwitch2 = 0x00, doorSwitch = 0x00, bag1TempC = 0.0, bag2TempC = 0.0, bagTempAvg = 0.0, pwmFrequency = 0x00, motorDutyState = 0x00, fanPowerState = 0x01, fanDutyState = 0x00, heaterDutyState = 0x00):
        super(self.__class__, self).__init__()
        #Initialize hardware properties
        self._serial = arduinoComm()
        self._runCmd = runCmd
        self._cmdType = cmdType
        self._cmdValue = cmdValue
        self._checksum = checksum
        self._upSwitch = upSwitch
        self._downSwitch = downSwitch
        self._selectSwitch = selectSwitch
        self._backSwitch = backSwitch
        self._pressureSwitch1 = pressureSwitch1
        self._pressureSwitch2 = pressureSwitch2
        self._doorSwitch = doorSwitch
        self._bag1Readings = []
        self._bag2Readings = []
        self._bag1TempC = bag1TempC
        self._bag2TempC = bag2TempC
        self._bagTempAvg = bagTempAvg
        self._pwmFrequency = pwmFrequency
        self._motorDutyState = motorDutyState
        self._fanPowerState = fanPowerState
        self._fanDutyState = fanDutyState
        self._heaterDutyState = heaterDutyState


    """-------------------------------------------------------------------------------------------------------
    Description: Timer callback function, sends command to comm link, defaults to STATUS_REQUEST after transmission
         Inputs: cmdType, cmdValue
        Outputs: None
    -------------------------------------------------------------------------------------------------------"""
    def sendCmd(self,cmd):
        response = self._serial.sendCmd(cmd)
        return self.parseStatus(response,cmd)
        

    """-------------------------------------------------------------------------------------------------------
            Description: Parses received hardware status packet into hardware model, notifies controller about update
                 Inputs: Decoded hardware status packet
                Outputs: emits update
    -------------------------------------------------------------------------------------------------------"""
    def parseStatus(self, status,cmd):
        if status[0] == NACK:
            return 0;
        else:
            #Update user input
            self._upSwitch = status[1]
            self._downSwitch = status[2]
            self._selectSwitch = status[3]
            self._backSwitch = status[4]
            #Update safety switches
            self._pressureSwitch1 = status[5]
            self._pressureSwitch2 = status[6]
            self._doorSwitch = status[7]
            #Unpack and update temperatures
            newBag11TempC, = struct.unpack("f", bytearray([status[8], status[9], status[10], status[11]]))
            newBag12TempC, = struct.unpack("f", bytearray([status[12], status[13], status[14], status[15]]))
            newBag21TempC,= struct.unpack("f", bytearray([status[16], status[17], status[18], status[19]]))
            newBag22TempC, = struct.unpack("f", bytearray([status[20], status[21], status[22], status[23]]))

            if newBag11TempC < 0 or newBag12TempC < 0 or newBag21TempC < 0 or newBag22TempC < 0:
                self.systemError.emit("System Failure")
                return 2

            #Sensor Calibration
            newBag11TempC -= BAG11_CAL
            newBag12TempC -= BAG12_CAL
            newBag21TempC -= BAG21_CAL
            newBag22TempC -= BAG22_CAL
            #Get average reading for each bag
            newBag11TempC = (newBag11TempC + newBag12TempC)/2
            newBag21TempC = (newBag21TempC + newBag22TempC)/2
            #Get average of last 10 readings
            self._bag1TempC = self.avgTemp(self._bag1Readings, newBag11TempC)
            self._bag2TempC = self.avgTemp(self._bag2Readings, newBag21TempC)
            # Ensure both bags are in system ; if one is not included, take the lower temperature
            if self._bag1TempC - self._bag2TempC > 1:
                self._bagTempAvg = self._bag2TempC

            if self._bag2TempC - self._bag1TempC > 1:
                self._bagTempAvg = self._bag1TempC
            else:
                self._bagTempAvg = (self._bag1TempC + self._bag2TempC) / 2
            #Update output status
            self._motorDutyState = status[24]
            self._fanPowerState = status[25]
            self._fanDutyState = status[26]
            self._heaterDutyState = status[27]
            self._pwmFrequency = status[28]
            return 1;


    """-------------------------------------------------------------------------------------------------------
    Description: Calculates and returns a running average of the last ten temperature readings
         Inputs: tempReadings = List of last 10 readings, newTemp = Latest reading
        Outputs: avgTemp
    -------------------------------------------------------------------------------------------------------"""
    def avgTemp(self, tempReadings, newTemp):
        tempReadings.insert(0,newTemp)
        readings = len(tempReadings)
        avgTemp = 0
        if (readings > 10):
            tempReadings.remove(tempReadings[readings-1])
            readings -= 1
        for temp in tempReadings:
            avgTemp += temp
        avgTemp /= readings
        return avgTemp

##----------------------Hardware properties for state access------------------------ 
    @property
    def cmdType(self):  
        return self._cmdType

    @cmdType.setter
    def cmdType(self, value):
        self._cmdType = value
        
    @property
    def cmdValue(self):
        return self._cmdValue

    @cmdValue.setter
    def cmdValue(self, value):
        self._cmdValue = value
    
    @property
    def checksum(self): 
        return self._checksum

    @checksum.setter
    def checksum(self, value):
        self._checksum = value
    
    @property
    def upSwitch(self): 
        return self._upSwitch

    @upSwitch.setter
    def upSwitch(self, value):
        self._upSwitch = value
    
    @property
    def downSwitch(self):    
        return self._downSwitch

    @downSwitch.setter
    def downSwitch(self, value):
        self._downSwitch = value
    
    @property
    def selectSwitch(self):  
        return self._selectSwitch

    @selectSwitch.setter
    def selectSwitch(self, value):
        self._selectSwitch = value
    
    @property
    def backSwitch(self): 
        return self._backSwitch

    @backSwitch.setter
    def backSwitch(self, value):
        self._backSwitch = value
    
    @property
    def pressureSwitch1(self):  
        return self._pressureSwitch1

    @pressureSwitch1.setter
    def pressureSwitch1(self, value):
        self._pressureSwitch1 = value
        
    @property
    def pressureSwitch2(self):   
        return self._pressureSwitch2

    @pressureSwitch2.setter
    def pressureSwitch2(self, value):
        self._pressureSwitch2 = value
    
    @property
    def doorSwitch(self):  
        return self._doorSwitch

    @doorSwitch.setter
    def doorSwitch(self, value):
        self._doorSwitch = value
    
    @property
    def bag1TempC(self):
        return self._bag1TempC

    @bag1TempC.setter
    def bag1TempC(self, value):
        self._bag1TempC = value
        
    @property
    def bag2TempC(self): 
        return self._bag2TempC

    @bag2TempC.setter
    def bag2TempC(self, value):
        self._bag2TempC = value

    @property
    def bagTempAvg(self):
        return self._bagTempAvg

    @bagTempAvg.setter
    def bagTempAvg(self, value):
        self._bagTempAvg = value
        
    @property
    def pwmFrequency(self): 
        return self._pwmFrequency

    @pwmFrequency.setter
    def pwmFrequency(self, value):
        self._pwmFrequency = value
        
    @property
    def motorDutyState(self): 
        return self._motorDutyState

    @motorDutyState.setter
    def motorDutyState(self, value):
        self._motorDutyState = value
        
    @property
    def fanDutyState(self): 
        return self._fanDutyState

    @fanDutyState.setter
    def fanDutyState(self, value):
        self._fanDutyState = value
        
    @property
    def heaterDutyState(self):
        return self._heaterDutyState

    @heaterDutyState.setter
    def heaterDutyState(self, value):
        self._heaterDutyState = value
##---------------------------------------------------------------------------- 
