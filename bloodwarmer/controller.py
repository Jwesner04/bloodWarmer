#!/usr/bin/env python
# -*- coding: cp1252 -*-

#Imports
import struct, time, math, csv
from PyQt4 import QtCore, QtGui, uic
from hardwareState import hardwareState

#-------------------------Constants----------------------------------#
#Controller proportional constant
#TODO test system to determine these heating constants
KP_HEAT = 0xFF
FAN_HEAT_SPEED = 0xFF
MOTOR_SPEED = 0xC0
ON = 0x01
OFF = 0x00

#-----------Control Timing-------------#
#Control loop update period
CONTROL_PERIOD = 30
#Time to incubate
INCUBATION_TIME_SECONDS = 3600.0

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
#----------------------------------------------------------------------------#
#
# Class Description: Runs control system, handles all error conditions, updates
#                    GUI
# Last Edited: 12/4/2016
# Last Edited By: Pete Wirges
# Last Changes Made:
#                   1.0.1:  Moved class to its own file, added updateHandler
#                   1.0.2:  Added incubationTimer, finishIncubation, stopSystem
#
#                   1.0.3:  set updateHandler to check door and pressure
#                           switches, implemented controller functionality inside
#                           run function
#                   1.0.4: Made control loop timer based, added startControlTimer,
#                          stopControlTimer, systemHandler to handle user input on
#                           which should be run, added signaling for buttons
#					1.1:  Added save functionality, updated incubation configuration,
#						  added safety catches, added system completion functionality
#
#----------------------------------------------------------------------------#

class controller(QtCore.QObject):
    #signal to send updated temperatures to gui
    tempUpdate = QtCore.pyqtSignal(float)
    #signals for messages to user
    doorSafetyWarning = QtCore.pyqtSignal()
    incubationFinishedMessage = QtCore.pyqtSignal()
    #System state update: 0 = Idle, 1 = Heating, 2 = Incubating, 3 = Complete
    systemUpdate = QtCore.pyqtSignal(int)

    #Tactile input updates
    upPressed = QtCore.pyqtSignal()
    downPressed = QtCore.pyqtSignal()
    backPressed = QtCore.pyqtSignal()
    selectPressed = QtCore.pyqtSignal()

	#Display timer signals
    startGuiTimer = QtCore.pyqtSignal(bool)  #bool = 
    stopGuiTimer = QtCore.pyqtSignal()

    #Timer for updating hardware status/sending commands
    updateTimer = QtCore.QTimer()

	
	#Define format for writing to csv
    csv.register_dialect(
        'bloodWarmerDialect',
        delimiter = '\t',
        quotechar = '"',
        doublequote = True,
        skipinitialspace = True,
        lineterminator = '\r\n',
        quoting = csv.QUOTE_MINIMAL)
        
    def __init__(self):
        super(self.__class__, self).__init__()
        #Initialize hardware model
        self.arduino = hardwareState()
        #Initialize controller variables
        self._lastHeaterDutyByte = 0
	self._kp = KP_HEAT
        self._setTemp = 37.0
        self._tempAvg = 0.0
        #Initialize status flags
        self._running = False
        self._incubating = False
        self._ready = False
		#Initialize time tracking variables
        self._incStartTime = 0
        self._incTime = 0
        self._heatTime = 0
        self._heatStartTime = 0
		#Initialize save file
        self.saveFile = None
        #Configure controller timer
        self.updateTimer.timeout.connect(self.runSystem,QtCore.Qt.QueuedConnection)
        self.startUpdateTimer()

    """-------------------------------------------------------------------------------------------------------
       Description: Runs system based on user input
            Inputs: systemState - if the system should be running or not
					restart - If the system is resuming (0), or restarting (1)
           Outputs: None
       -------------------------------------------------------------------------------------------------------"""
    @QtCore.pyqtSlot(bool, bool)
    def systemHandler(self, systemState, restart):
		#Stop control loop and sleep until last callback made
        self.stopUpdateTimer()
        time.sleep(1)
		#Configure display timer on restart
        self.startGuiTimer.emit(restart)
		#Configure heating time on restart
        if restart:
            self._heatStartTime = time.time() - self._heatTime
		#If returning from door safety fault, start system only if door is closed, otherwise repeat fault
        if systemState and self.arduino.doorSwitch:
            self.startSystem()
        elif not systemState and self.arduino.doorSwitch:
            self.stopSystem()
        else:
            self.stopSystem()
            self.doorSafetyWarning.emit()
		#Restart control loop timer 
        self.startUpdateTimer()
        

		
	"""-------------------------------------------------------------------------------------------------------
       Description: Enables logging of temperature over time
            Inputs: None
           Outputs: None
       -------------------------------------------------------------------------------------------------------"""
    @QtCore.pyqtSlot()
    def enableSaving(self):
        try:
            self.saveFile = open('/media/pi/USB/bloodwarmerData.csv', 'a')
        except:
            self.saveFile = None
			
        
    """-------------------------------------------------------------------------------------------------------
   Description: Configures and starts control timer
        Inputs: None
       Outputs: None
   -------------------------------------------------------------------------------------------------------"""
    def startUpdateTimer(self):
        self.updateTimer.start(CONTROL_PERIOD)

		
	"""-------------------------------------------------------------------------------------------------------
   Description: Stops control timer
        Inputs: None
       Outputs: None
   -------------------------------------------------------------------------------------------------------"""
    def stopUpdateTimer(self):
        self.updateTimer.stop()
		

    """-------------------------------------------------------------------------------------------------------
   Description: On status update, checks for any condition that needs action (button press, door open, etc)
        Inputs: None
       Outputs: None
   -------------------------------------------------------------------------------------------------------"""
    def updateHandler(self):
		#Set temperature to be controlled
        self._tempAvg = self.arduino.bagTempAvg
		#Send average temperature to gui
        self.tempUpdate.emit(self._tempAvg)
		
        #Call tactile input event handlers
        if self.arduino.upSwitch:
            self.upPressed.emit()
        if self.arduino.downSwitch:
            self.downPressed.emit()
        if self.arduino.backSwitch:
            self.backPressed.emit()
        if self.arduino.selectSwitch:
            self.selectPressed.emit()
        #Checks if door is open and sets safety warning if not
        if self._running and not self.arduino.doorSwitch:
                self.stopSystem()
                self.doorSafetyWarning.emit()
	
	"""-------------------------------------------------------------------------------------------------------
   Description: Starts control system
        Inputs: None
       Outputs: None
   -------------------------------------------------------------------------------------------------------"""
    def startSystem(self):
		#Set control loop running flag
        self._running = 1
		#Save time and average temperature to flash drive if save button has been pressed
        if self.saveFile:
            try:
                self.saveFile = open('/media/pi/USB/bloodwarmerData.csv', 'a')
                dataWriter = csv.writer(self.saveFile, dialect = "bloodWarmerDialect")
                dataWriter.writerow(("Date/Time",'            ',"Average Bag Temperature (C)"))
            except:
                pass
        #Initialize motor and fan
        self.sendCmd(bytearray([MOTOR_DUTY_SET, MOTOR_SPEED]))
        self.sendCmd(bytearray([FAN_POWER_SET, ON]))
        self.sendCmd(bytearray([FAN_DUTY_SET, FAN_HEAT_SPEED]))
        #Determine system state starting in, configure controller and display appropriately
        error = self._setTemp - self._tempAvg
        if error <= 0.5 and ~self._incubating:
            self._incubating = True
            self._incStartTime = time.time()
            self.startGuiTimer.emit(True)
            self.systemUpdate.emit(2)
        elif self._incubating:
            self.systemUpdate.emit(2)
        else:
            self.systemUpdate.emit(1)

    """-------------------------------------------------------------------------------------------------------
   Description: Sends command to stop control system hardware
        Inputs: None
       Outputs: Off commands to arduino
   -------------------------------------------------------------------------------------------------------"""
    def stopSystem(self):
		#Set control loop running flag to 0
        self._running = 0
		#Stops motor, fan, and heater
        self.sendCmd(bytearray([MOTOR_DUTY_SET, OFF]))
        self.sendCmd(bytearray([FAN_POWER_SET, OFF]))
        self.sendCmd(bytearray([HEATER_DUTY_SET, OFF]))
		#Stops display timer and updates system state displayed
        self.stopGuiTimer.emit()
        self.systemUpdate.emit(0)
		#Closes save file if open
        try:
            self.saveFile.close()
        except:
            pass
        

    """-------------------------------------------------------------------------------------------------------
       Description: Updates the set reference temperature used in control loops
            Inputs: newSetTemp - user specified set temp between 37.0-41.0C
           Outputs: None
       -------------------------------------------------------------------------------------------------------"""
    QtCore.pyqtSlot(float)
    def updateSetTemp(self,newSetTemp):
        self._setTemp = newSetTemp


	"""-------------------------------------------------------------------------------------------------------
       Description: Sends command to atmega controller, stops system on temp sensor fault
            Inputs: cmd - command to send to arduino
           Outputs: None
       -------------------------------------------------------------------------------------------------------"""
    def sendCmd(self, cmd):
		#Send command
        update = self.arduino.sendCmd(cmd)
		#Handle model update
        if update == 1:
            self.updateHandler()
		#Stop system on temp sensor fault
        if update == 2:
            self.stopSystem()

    """-------------------------------------------------------------------------------------------------------
   Description: Control system run function, signaled by start button,
        Inputs: None
       Outputs: Commands to arduino
   -------------------------------------------------------------------------------------------------------"""
    QtCore.pyqtSlot()
    def runSystem(self):
        #Run control loop
        if self._running:
			
			#If save button has been pressed, save time and average temperature to file
            if self.saveFile:
                try:
                    logTime = time.asctime(time.localtime(time.time()))
                    dataWriter = csv.writer(self.saveFile, dialect = "bloodWarmerDialect")
                    dataWriter.writerow((logTime,"%.2f" % self._tempAvg))
                except:
                    pass
					
			#Calculate the time spent heating
            self._heatTime = time.time() - self._heatStartTime
            #Get error for controller
            error= self._setTemp - self._tempAvg
			#Floor negative error values to 0
            if error < 0:
                error = 0
            #Check and configure for system state (heating/incubation) 
			#start incubating
            if error <= 0.5 and not self._incubating:
				#set incubation flag
                self._incubating = True
				#Get incubation time
                self._incStartTime = time.time() - self._incTime
				#Restart gui timer and update system state to incubating
                self.startGuiTimer.emit(True)
                self.systemUpdate.emit(2)
			#Stop incubating
            elif error > 0.5 and self._incubating:
				#Set incubation flag
                self._incubating = False
				#Reset incubation time and switch system state to heating
                self._incStartTime = 0
                self._incTime = 0
                self.systemUpdate.emit(1)
            else:
                #Calculate heater duty signal to send based on constant
                duty = error*self._kp
                #Ceiling function for duty value
                if duty > 255:
                    duty = 255
                #Convert duty value from float to byte
                dutyByte = struct.pack("B",duty)
                #Set duty cycle of heater
                if dutyByte is not self._lastHeaterDutyByte:
                    self.sendCmd(bytearray([HEATER_DUTY_SET,dutyByte]))
                self._lastHeaterDutyByte = dutyByte
				#Update incubation time
                if self._incubating:
                    self._incTime = time.time() - self._incStartTime
					#Check for incubation completion and signal to display
                    if self._incTime >= INCUBATION_TIME_SECONDS and not self._ready:
                        self.systemUpdate.emit(3)
                        self.incubationFinishedMessage.emit()
                        self._ready = True
        else:
			#Get hardware update only if controller not running
            self.sendCmd(bytearray([STATUS_REQUEST,0x00]))









  

