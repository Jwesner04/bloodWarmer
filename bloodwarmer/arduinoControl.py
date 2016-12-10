import serial
import math
import time
import struct
import binascii
import logging
from PyQt4 import QtGui, uic, QtCore

#Communication control characters
BEGIN = 0x02 #Start transmission
END = 0x03 #End transmission
ACK = 0x06 #Acknowledge packet
NACK = 0x15 #No acknowledge packet
ESC = 0x1B #Escape character: indicates control characters within packet

#--------------------Commands--------------------#
STATUS_REQUEST = 0x07 #Returns status of all hardware

#The following commands issue a status request in 
#addition to their particular function

"""
Sets motor duty cycle
Accepted values: 0-255
D = MOTOR_SET_VALUE/255
"""
MOTOR_SET = 0x08 

"""
Sets fan duty cycle
Accepted values: 0-255
D = FAN_SET_VALUE/255
"""
FAN_SET = 0x09

""""
Sets heater duty cycle
Accepted values: 0-255
D = HEATER_SET_VALUE/255
"""
HEATER_SET = 0x0A

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
FREQ_SET = 0x0B 
#------------------------------------------------#


#-----------Serial port config values------------#
SERIALPORT = '/dev/serial0'
BAUD_RATE = 9600

#Time to wait for response after send
RECEIVE_DELAY = 0.15
#------------------------------------------------#



#--------Temp Sensor calibration offsets---------#
BAG1_CAL = 0.1
BAG2_CAL = 0.3
INLET_CAL = 0.2
OUTLET_CAL = 0.4
#------------------------------------------------#

#debug file
LOGFILE = '/home/pi/Downloads/comm.log'

"""----------------------------------------------------------------------------
 Class Description: For sending commands/receiving status from AtMega
 Last Edited: 10/24/2016
 Last Edited By: Pete Wirges
 Changelog: -1.0.0: Established protocol to send commands to arduino and receive
                    status updates and store them as properties
            -1.0.1: Added threading support, removed properties, added stopOutput 
                    function to reset hardware, improved documentation, added
                    handling for case when checksum is invalid
----------------------------------------------------------------------------"""
"""
Hardware state values fetched by this class:
    Command(See list of available commands at top of file):
        cmdType
        cmdValue

    Tactile Input (1 = ON, 0 = OFF):
        upSwitch
        downSwitch
        selectSwitch
        backSwitch

    Safety Switches (1 = ON, 0 = OFF):
        pressureSwitch1
        pressureSwitch2
        doorSwitch

    Temperature Sensors (in degrees Celcius):
        bag1TempC
        bag2TempC
        inletTempC
        outletTempC

    Output States(indicated by corresponding command value (see above)):
        motorState
        fanState
        heaterState
        pwmFrequency
"""
class arduinoComm(QtCore.QObject):
    'Class for sending commands to and receiving status from arduino'

    #To send hardware status to another thread
    hardwareStatusUpdate = QtCore.pyqtSignal(bytearray, float, float, float, float)

    def __init__(self, parent = None, runCmd = 0, cmdType = STATUS_REQUEST, cmdValue = 0x00, checksum = 0x00, upSwitch = 0x00, downSwitch = 0x00, selectSwitch = 0x00, backSwitch = 0x00, pressureSwitch1 = 0x00, pressureSwitch2 = 0x00, doorSwitch = 0x00, bag1TempC = 0.0, bag2TempC = 0.0, inletTempC = 0.0, outletTempC = 0.0, pwmFrequency = 0x00, motorState = 0x00, fanState = 0x00, heaterState = 0x00):
        
        super(self.__class__, self).__init__(parent)
        #Initialize serial port
        self.ser=serial.Serial(port=SERIALPORT, baudrate=BAUD_RATE, bytesize=8, parity = 'N', stopbits = 1)
        self.ser.close()
        self.ser.open()

        #Initialize debug logger
        self.logger = logging.getLogger('arduinoComm')
        hdlr = logging.FileHandler(LOGFILE)
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        hdlr.setFormatter(formatter)
        self.logger.addHandler(hdlr) 
        self.logger.setLevel(logging.DEBUG)
        self.logger.debug('initializing communications')

        #Initialize hardware properties
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
        self._bag1TempC = bag1TempC
        self._bag2TempC = bag2TempC
        self._inletTempC = inletTempC
        self._outletTempC = outletTempC
        self._pwmFrequency = pwmFrequency
        self._motorState = motorState
        self._fanState = fanState
        self._heaterState = heaterState
        #Initialize outputs as zero
        self.stopOutput()


    #--------------------Interface Functions--------------------#

    """-------------------------------------------------------------------------------------------------------
    Description: Receives and executes command from another thread
         Inputs: cmd (bytearray) - [cmdType,cmdValue] must be from list of acceptable commands at top of file
        Outputs: Returns status update to thread after pinging arduino with command
    -------------------------------------------------------------------------------------------------------"""
    @QtCore.pyqtSlot(bytearray)
    def Run(self, cmd = (bytearray([STATUS_REQUEST, 0x00]))):
        self._cmdType = cmd[0]
        self._cmdValue = cmd[1]
        self.sendCmd(self._cmdType, self._cmdValue)
    #-----------------------------------------------------------#


    #--------------------Private Functions----------------------#

        
    """----------------------------------------------------------------------------------------------------    
    Description: Sends command to arduino and receives response
         Inputs: cmdType (byte), cmdValue (byte) - must be from list of acceptable commands at top of file
        Outputs: emits status of all hardware to a slot in another thread
    ----------------------------------------------------------------------------------------------------"""
    def sendCmd(self, cmdType, cmdValue):
        self.logger.debug('sending command')
        #Put command into packet
        cmd = bytearray([cmdType,cmdValue])
        cmd = self.encodeCmd(cmd)
        #Calculate checksum for packet
        crc = self.CRC8(cmd)
        #Clear serial buffers
        self.ser.flushInput()
        self.ser.flushOutput()
        #Frame packet and send
        cmd = bytearray([BEGIN]) + cmd + bytearray([crc]) + bytearray([END])
        self.ser.write(cmd)
        #Wait and receive response
        time.sleep(RECEIVE_DELAY)
        resp = self.readRsp()
        self.parseRsp(resp)
        self.emitStatus()

    """-------------------------------------------------------------------------------------------------------
    Description: Encodes for control characters contained within packet
         Inputs: cmd (bytearray) - Unencoded command with checksum and control characters
        Outputs: Returns command encoded for control characters
    -------------------------------------------------------------------------------------------------------"""
    def encodeCmd(self,cmd):
        encodedCmd = bytearray([])
        #Checks each byte for control character,
        #If found, sets bit 7 high and inserts ESC before it
        for i in cmd:
            if (i == BEGIN) or (i == END) or (i == ESC):
                encodedCmd = encodedCmd + bytearray([ESC]) + bytearray([(i | (1 << 7))])
            else:
                encodedCmd = encodedCmd + bytearray([i])
        return encodedCmd

    """-------------------------------------------------------------------------------------------------------
    Description: Calculates 8-bit CRC Maxim/Dallas Checksum of data packet
         Inputs: data (bytearray) - encoded command or encoded response with control characters removed
        Outputs: Returns checksum for data
    -------------------------------------------------------------------------------------------------------"""
    def CRC8(self, data):
        crc = 0x00
        for e in data:   
            for i in range(8):
                s = (crc^e) & 0x01
                crc >>= 1
                if (s):
                    crc ^= 0x8C
                e >>= 1
        return crc
    
    """-------------------------------------------------------------------------------------------------------
    Description: Sets all output hardware to defaults
         Inputs: Nothing
        Outputs: Motor, fan, and heater duty cycles set to 0. Pwm frequency set to 30Hz
    -------------------------------------------------------------------------------------------------------"""
    def stopOutput(self):
        self.sendCmd(MOTOR_SET, 0x00)
        self.sendCmd(FAN_SET, 0x00)
        self.sendCmd(HEATER_SET, 0x00)
        self.sendCmd(FREQ_SET, 0x11)

    """-------------------------------------------------------------------------------------------------------
    Description: Reads response from arduino
         Inputs: Data on serial port if present
        Outputs: Response from arduino given that it is framed by a BEGIN and END byte
    -------------------------------------------------------------------------------------------------------"""
    def readRsp(self):
        resp = bytearray()
        trans = False
        #Wait for response
        self.logger.debug('Waiting for response')
        while self.ser.inWaiting > 0:
            c = self.ser.read(1)
            #Wait for BEGIN to read response, stop reading after END
            if c == bytearray([BEGIN]):
                trans = True
            elif trans:
                if c == bytearray([END]):
                    break
                else:
                    resp += c
        return resp

    """-------------------------------------------------------------------------------------------------------
    Description: Parse packet to update status
         Inputs: Response packet with BEGIN and END bytes removed
        Outputs: If packet is valid, hardware state variables updated. If not sets NACK.
    -------------------------------------------------------------------------------------------------------"""
    def parseRsp(self, resp):
        #Check if packet is valid and if so extract it
        resp = self.extractPacket(resp)
        if (resp != None):
            #Decode packet if valid
            if (len(resp) > 0):
                resp = self.decodeCtrlChar(resp)
                #Update status
                if (resp[0] == NACK):
                    self.logger.debug('Command not acknowledged')
                    self.cmdType = resp[0]
                else:
                    self.updateStatus(resp)
        else:
            self._cmdType = NACK

    """-------------------------------------------------------------------------------------------------------
    Description: Sends status update to another thread
         Inputs: Nothing
        Outputs: status (bytearray), bag1TempC, bag2TempC, inletTempC, outletTempC (floats)
    -------------------------------------------------------------------------------------------------------"""
    def emitStatus(self):
        status = bytearray([self._cmdType, self._cmdValue, self._upSwitch, self._downSwitch, self._backSwitch, self._selectSwitch, self._pressureSwitch1, self._pressureSwitch2, self._doorSwitch, self._pwmFrequency, self._motorState, self._fanState, self._heaterState])
        self.hardwareStatusUpdate.emit(status, self._bag1TempC, self._bag2TempC, self._inletTempC, self._outletTempC) 
        
    """-------------------------------------------------------------------------------------------------------
    Description: Extracts valid packet from received transmission
         Inputs: Received packet with BEGIN and END removed
        Outputs: If checksum is valid, returns packet with checksum removed.  Otherwise returns None.
    -------------------------------------------------------------------------------------------------------"""
    def extractPacket(self,resp):
        self.logger.debug('Checking Packet')
        lenresp = len(resp)
        status = bytearray()
        #Get received checksum
        self._checksum = resp[lenresp-1]
        #Extract packet from received transmission
        for i in range(lenresp-1):
                status += bytearray([resp[i]])
        #Calculate checksum and compare it with received 
        if (self._checksum == self.CRC8(status)):
            self.logger.debug('Valid status')
            return status
        else:
            self.logger.debug('Invalid Checksum')
            return None
        

    """-------------------------------------------------------------------------------------------------------
    Description: Decode control characters from received packet
         Inputs: Valid packet with frame completely removed
        Outputs: Received packet decoded for control characters
    -------------------------------------------------------------------------------------------------------"""
    def decodeCtrlChar(self, status):
        self.logger.debug('Decoding Control Characters')
        decodedStatus = bytearray([])
        #If ESC found, ignore and decode next character by setting bit 8 LOW
        for i in range(len(status)):
            if (status[i] == ESC):
                if ((i > 0) and (status[i-1] == ESC)):
                    decodedStatus= decodedStatus + bytearray([status[i]])
                elif (i < len(status)-1):
                        status[i+1]  = status[i+1] & 0x7F
            else:
                decodedStatus = decodedStatus + bytearray([status[i]])
        return decodedStatus
        
    """-------------------------------------------------------------------------------------------------------
    Description: Update hardware properties with new status
         Inputs: Valid, decoded packet
        Outputs: Updates hardware states
    -------------------------------------------------------------------------------------------------------"""
    def updateStatus(self, status):
        self.logger.debug('Parsing Status')
        self._cmdType = status[0]
        self._upSwitch = status[1]
        self._downSwitch = status[2]
        self._selectSwitch = status[3]
        self._backSwitch = status[4]
        self._pressureSwitch1 = status[5]
        self._pressureSwitch2 = status[6]
        self._doorSwitch = status[7]
        bag1TempCBytes = bytearray([status[8], status[9], status[10], status[11]])
        self._bag1TempC, = struct.unpack("f", bag1TempCBytes)
        bag2TempCBytes = bytearray([status[12], status[13], status[14], status[15]])
        self._bag2TempC, = struct.unpack("f", bag2TempCBytes)
        inletTempCBytes = bytearray([status[16], status[17], status[18], status[19]])
        self._inletTempC,= struct.unpack("f", inletTempCBytes)
        outletTempCBytes = bytearray([status[20], status[21], status[22], status[23]])
        self._outletTempC, = struct.unpack("f", outletTempCBytes)
        #Sensor Calibration
        self._bag1TempC -= BAG1_CAL
        self._bag2TempC -= BAG2_CAL
        self._inletTempC -= INLET_CAL
        self._outletTempC -= OUTLET_CAL
        
        self._motorState = status[24]
        self._fanState = status[25]
        self._heaterState = status[26]
        self._pwmFrequency = status[27]

#-----------------------------------------------------------------------#

##-------------OBSOLETE/FOR DEBUG ONLY-----------------
##Hardware properties for state access     
##    @property
##    def cmdType(self):  
##        return self._cmdType
##
##    @cmdType.setter
##    def cmdType(self, value):
##        self._cmdType = value
##        
##    @property
##    def cmdValue(self):
##        return self._cmdValue
##
##    @cmdValue.setter
##    def cmdValue(self, value):
##        self._cmdValue = value
##    
##    @property
##    def checksum(self): 
##        return self._checksum
##
##    @checksum.setter
##    def checksum(self, value):
##        self._checksum = value
##    
##    @property
##    def upSwitch(self): 
##        return self._upSwitch
##
##    @upSwitch.setter
##    def upSwitch(self, value):
##        self._upSwitch = value
##    
##    @property
##    def downSwitch(self):    
##        return self._downSwitch
##
##    @downSwitch.setter
##    def downSwitch(self, value):
##        self._downSwitch = value
##    
##    @property
##    def selectSwitch(self):  
##        return self._selectSwitch
##
##    @selectSwitch.setter
##    def selectSwitch(self, value):
##        self._selectSwitch = value
##    
##    @property
##    def backSwitch(self): 
##        return self._backSwitch
##
##    @backSwitch.setter
##    def backSwitch(self, value):
##        self._backSwitch = value
##    
##    @property
##    def pressureSwitch1(self):  
##        return self._pressureSwitch1
##
##    @pressureSwitch1.setter
##    def pressureSwitch1(self, value):
##        self._pressureSwitch1 = value
##        
##    @property
##    def pressureSwitch2(self):   
##        return self._pressureSwitch2
##
##    @pressureSwitch2.setter
##    def pressureSwitch2(self, value):
##        self._pressureSwitch2 = value
##    
##    @property
##    def doorSwitch(self):  
##        return self._doorSwitch
##
##    @doorSwitch.setter
##    def doorSwitch(self, value):
##        self._doorSwitch = value
##    
##    @property
##    def bag1TempC(self):
##        return self._bag1TempC
##
##    @bag1TempC.setter
##    def bag1TempC(self, value):
##        self.bag1TempC = value
##        
##    @property
##    def bag2TempC(self): 
##        return self._bag2TempC
##
##    @bag2TempC.setter
##    def bag2TempC(self, value):
##        self.bag2TempC = value
##        
##    @property
##    def inletTempC(self): 
##        return self._inletTempC
##
##    @inletTempC.setter
##    def inletTempC(self, value):
##        self.inletTempC = value
##        
##    @property
##    def outletTempC(self):
##        return self._outletTempC
##
##    @outletTempC.setter
##    def outletTempC(self, value):
##        self.outletTempC = value
##        
##    @property
##    def pwmFrequency(self): 
##        return self._pwmFrequency
##
##    @pwmFrequency.setter
##    def pwmFrequency(self, value):
##        self.pwmFrequency = value
##        
##    @property
##    def motorState(self): 
##        return self._motorState
##
##    @motorState.setter
##    def motorState(self, value):
##        self.motorState = value
##        
##    @property
##    def fanState(self): 
##        return self._fanState
##
##    @fanState.setter
##    def fanState(self, value):
##        self.fanState = value
##        
##    @property
##    def heaterState(self):
##        return self._heaterState
##
##    @heaterState.setter
##    def heaterState(self, value):
##        self.heaterState = value
##--------------------------------------------------        
    
        
