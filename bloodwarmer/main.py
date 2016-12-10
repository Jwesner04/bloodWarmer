# -*- coding: cp1252 -*-
#-----------------------------------------------------------#
#
# Program Description: Used to control a blood warmer system
# Date Last Modified: December 05, 2016
# File name: main.py -- includes all dependencies
#
#-----------------------------------------------------------#

#-----------------------------------------------------------#
# INCLUDES
#-----------------------------------------------------------#

import sys, time, os
import RPi.GPIO as GPIO 
from PyQt4 import QtCore, QtGui, uic
from arduinoComm import arduinoComm
from hardwareState import hardwareState
from controller import controller
from mainWindow import mainWindow
from warningPopup import warningPopup
from errorPopup import errorPopup
from messagePopup import messagePopup




"""-------------------------------------------------------------------------------------------------------
   Description: Shutdown event handler, deletes objects, quits app, and shuts os down
        Inputs: None
       Outputs: None
   -------------------------------------------------------------------------------------------------------"""
@QtCore.pyqtSlot()
def shutdown():
    #Close save file
    try:
        controller.saveFile.close()
    except:
        pass
    controller.stopSystem()
    #Clean up objects
    GPIO.cleanup()
    controller.deleteLater()
    window.deleteLater()
    #Exit threads
    controllerThread.exit()
    #Quit app and shutdown raspbian
    app.quit()
    os.system('shutdown now -h')

"""-------------------------------------------------------------------------------------------------------
   Description: Connects signals to slots for event handling and relaying information across threads
        Inputs: None
       Outputs: None
   -------------------------------------------------------------------------------------------------------"""
def signalHandler():
    #Allows controller to send updated, averaged temp values to gui
    controller.tempUpdate.connect(window.setTemps)
    #Connect start button to its event handler
    window.startButton.clicked.connect(window.startClicked)
    #Connect set temp adjustment to its event handler
    window.adjustTemp.valueChanged.connect(window.setTempUpdate)
    #Sends new set temp to controller when changed
    window.sendTemp.connect(controller.updateSetTemp)
    #Notifies the controller whether to run or not
    window.systemState.connect(controller.systemHandler)
    #Triggers tactile input event handlers
    controller.upPressed.connect(window.upButtonHandler)
    controller.downPressed.connect(window.downButtonHandler)
    controller.backPressed.connect(window.backButtonHandler)
    controller.selectPressed.connect(window.selectButtonHandler)
	#popup event handlers
    controller.doorSafetyWarning.connect(warning.setWarning)
    controller.arduino.systemError.connect(error.setError)
    controller.incubationFinishedMessage.connect(message.displayMessage)
	# Warning Connections
    warning.continueButton.clicked.connect(warning.chooseResume)
    warning.restartButton.clicked.connect(warning.chooseRestart)
    warning.continueButton.pressed.connect(warning.chooseResume)
    warning.restartButton.pressed.connect(warning.chooseRestart)
    warning.runSystem.connect(controller.systemHandler)
	#system display update
    controller.systemUpdate.connect(window.updateStatus)
	#display timer connections
    controller.startGuiTimer.connect(window.setGuiTimer)
    controller.stopGuiTimer.connect(window.stopGuiTimer)
    #save button
    window.saveButton.clicked.connect(controller.enableSaving)
    # Connect shutdown button to its event handler
    window.shutdownButton.clicked.connect(shutdown)
    window.shutdownPressed.connect(shutdown)



##############################################################################
#
# Function Description: Main function, runs program
# Last Edited: 11/13/2016
# Last Edited By: Pete Wirges
# Last Changes Made: 1.0.1:  Added signal connectivity for controller setCmd
#                    1.0.2:  Moved to own file, organized signal connections in
#                           one function, added some comments, generalized
#                           systemStart signal to systemState, added connections
##                           for button event handlers
#
##############################################################################
if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    #Create controller, serial link, and main window objects
    controller = controller()
    window = mainWindow()
    warning = warningPopup()
    error = errorPopup()
    message = messagePopup()
    
    #------------------------------------------------------------------------#
    # CREATE THREADS FOR CONTROLLER & SERIAL LINK
    #------------------------------------------------------------------------#
    controllerThread = QtCore.QThread()

    #------------------------------------------------------------------------#
    # SERIAL LINK AND CONTROLLER SET TO THREADS
    #------------------------------------------------------------------------#
    controller.moveToThread(controllerThread)

    #------------------------------------------------------------------------#
    # SIGNAL CONNECTIONS
    #------------------------------------------------------------------------#
    signalHandler()

    #------------------------------------------------------------------------#
    # START HARDWARE AND CONTROLLER THREADS
    #------------------------------------------------------------------------#
    controllerThread.start()

    #------------------------------------------------------------------------#
    # GUI OUTPUT
    #------------------------------------------------------------------------#
    window.show()
    sys.exit(app.exec_())
