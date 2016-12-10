#imports
import serial
import math
import time
import struct
import binascii
import logging
import RPi.GPIO as GPIO
from PyQt4 import QtCore

#----------------Constants-----------------------#

#Pi GPIO pin to reset Atmega
ATMEGA_RESET_PIN = 25

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
#------------------------------------------------#


#-----------Serial port config values------------#
SERIALPORT = '/dev/serial0'
BAUD_RATE = 19200


#debug file
LOGFILE = '/home/pi/Downloads/comm.log'

"""----------------------------------------------------------------------------
 Class Description: For sending commands/receiving status from AtMega
 Last Edited: 12/4/2016
 Last Edited By: Pete Wirges
 Changelog: -1.0.0: Established protocol to send commands to arduino and receive
                    status updates and store them as properties
            -1.0.1: Added threading support, removed properties, added stopOutput 
                    function to reset hardware, improved documentation, added
                    handling for case when checksum is invalid
            -1.0.1: Removed remnants of unused properties, adjusted packet size for
                    fan on/off control
            -1.0.1: Updated to include fan power control/status
			-1.0.2: Added reset of atmega at startup, removed receive delay to tune 
					comm time from 150ms to 26ms
----------------------------------------------------------------------------"""
"""
Hardware state values:
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
    hardwareStatusUpdate = QtCore.pyqtSignal(bytearray)

    def __init__(self, parent = None, runCmd = 0, cmdType = STATUS_REQUEST, cmdValue = 0x00, checksum = 0x00):
        
        super(self.__class__, self).__init__(parent)
        #TODO Add code here to hold atmega reset pin high for 2s before attempting serial communication
        #Initialize serial port
        self.ser=serial.Serial(port=SERIALPORT, baudrate=BAUD_RATE, bytesize=8, parity = 'N', stopbits = 1)
        self.ser.close()
        self.ser.open()
        #Configure Atmega reset pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(ATMEGA_RESET_PIN, GPIO.OUT)
        
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

        #Initialize outputs as zero
        self.stopOutput()


    #--------------------Interface Functions--------------------#

    """----------------------------------------------------------------------------------------------------
    Description: Sends command to arduino and receives response
         Inputs: cmd = [cmdType (byte), cmdValue (byte)] - must be from list of acceptable commands at top of file
        Outputs: emits status of all hardware to a slot in another thread
    ----------------------------------------------------------------------------------------------------"""
    def sendCmd(self, cmd):
        self.logger.debug('sending command')
        #Encode command for control characters
        cmd = self.encodeCmd(cmd)
        #Calculate checksum for packet
        crc = self.CRC8(cmd)
        #Clear serial buffers
        self.ser.flushInput()
        self.ser.flushOutput()
        #Frame packet and send
        cmd = bytearray([BEGIN]) + cmd + bytearray([crc]) + bytearray([END])
        self.ser.write(cmd)
		#Receive response
        resp = self.readRsp()
        return self.processRsp(resp)

    #--------------------Private Functions----------------------#

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
        GPIO.output(ATMEGA_RESET_PIN,GPIO.HIGH)
        time.sleep(2)
        GPIO.output(ATMEGA_RESET_PIN,GPIO.LOW)
        time.sleep(2)
        self.sendCmd(bytearray([MOTOR_DUTY_SET, 0x00]))
        self.sendCmd(bytearray([FAN_DUTY_SET, 0x00]))
        self.sendCmd(bytearray([FAN_POWER_SET, 0x00]))
        self.sendCmd(bytearray([HEATER_DUTY_SET, 0x00]))
        self.sendCmd(bytearray([FREQ_SET, 0x11]))

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
    Description: Determines if command was received, if it is emits status update
         Inputs: Response packet with BEGIN and END bytes removed
        Outputs: If packet is valid, hardware status emitted to controller thread. If not emits NACK.
    -------------------------------------------------------------------------------------------------------"""
    def processRsp(self, resp):
        #Check if packet is valid and if so extract it
        resp = self.extractPacket(resp)
        if (resp != None):
            #Decode packet if valid
            if (len(resp) > 0):
                resp = self.decodeCtrlChar(resp)
                #Update status
                if resp[0] == NACK:
                    self.logger.debug('Command not acknowledged')
                    return bytearray([NACK])
                else:
                    return resp
            else:
                return bytearray([NACK])
        else:
            return bytearray([NACK])

         
        
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

#-----------------------------------------------------------------------#
     
    
        
