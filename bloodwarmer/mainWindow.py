# -*- coding: cp1252 -*-
#-----------------------------------------------------------#
# INCLUDES
#-----------------------------------------------------------#

import sys, time, os, pyautogui
from PyQt4 import QtCore, QtGui, uic


#-----------------------------------------------------------#
# LOAD GUI FILE
#-----------------------------------------------------------#
qtMainWindowFile = "/home/pi/Documents/BloodWarmer/interface.ui"
Ui_MainWindow, QtBaseClass = uic.loadUiType(qtMainWindowFile)


# -----------------------------------------------------------------------------------------------#
#
# Class Description: This class is used for the main window.
# Last Edited: 11/17/2016
# Last Edited By: Jon Wesner
# Last Changes Made:  1.0.1:Pete - implemented slot to receive and display temp update
#                           implemented slots for startButton.clicked and adjustTemp.valueChanged,
#                           functions signal controller for appropriate action, moved to own file
#                           added signaling and templates for button event handlers
#                     1.0.2:Jon - implemented a start,stop,reset gui timer functions and handled within
#                            the startClicked slot. Removed cluttered code unneeded in order to
#                            help read code better. Implemented the button slots using pyautogui
#                            library, which fires off appropriate key strokes based on buttons
#                            pressed.
#
# -----------------------------------------------------------------------------------------------#
class mainWindow(QtGui.QMainWindow, Ui_MainWindow):

    sendTemp = QtCore.pyqtSignal(float)
    systemState = QtCore.pyqtSignal(bool, bool)
    shutdownPressed = QtCore.pyqtSignal()

    guiTimer = QtCore.QTimer()

    def __init__(self):
        os.system("xinput set-prop 'Microchip Technology Inc. AR1100 HID-MOUSE' 'Evdev Axis Inversion' 1 1")
        QtGui.QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)
        self.setupUi(self)
        self.guiTimer.timeout.connect(self.runGuiTimer)
        # ---------------------------------------------------#
        # Local Variables
        # ---------------------------------------------------#
        self._time = 0
        self.systemIsRunning = False
        self.targetedTemperature = 0
        self.focusedProperty = self.startButton.setFocus()
        self.propertyTable = [self.startButton,self.saveButton, self.shutdownButton,self.adjustTemp]

        # ---------------------------------------------------#
        # User Interface Property changes
        # ---------------------------------------------------#
        # Fills whole screen depending on screen size
        self.showFullScreen()
        # Change mouse cursor when hovering over button
        self.startButton.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        # Set minimum and maximum values for adjusted temperature
        self.adjustTemp.setRange(37, 41)
        self.adjustTemp.setDecimals(1)
        self.adjustTemp.setSingleStep(.1)
        self.adjustTemp.setSuffix("°C")


    @QtCore.pyqtSlot(bool)
    def setGuiTimer(self,restart):
        if restart:
            self._time = 0
        self.guiTimer.start(1000)


    @QtCore.pyqtSlot()
    def stopGuiTimer(self):
        self.guiTimer.stop()

    @QtCore.pyqtSlot()
    def runGuiTimer(self):
        self._time += 1
        hours = self._time / 3600
        minutes = (self._time % 3600) / 60
        seconds = self._time % 60
        # Output time to Label
        self.bagTimer.setText(
            '{:02.0f}'.format(hours) + ":" + '{:02.0f}'.format(minutes) + ":" + '{:02.0f}'.format(seconds))
        self.bagTimer.setText(
            '{:02.0f}'.format(hours) + ":" + '{:02.0f}'.format(minutes) + ":" + '{:02.0f}'.format(seconds))





    """-------------------------------------------------------------------------------------------------------
           Description: Event handler for start/stop button. Relays set temp and signals controller to start/stop system
                Inputs: None
               Outputs: systemState - whether control should run or not, setTemp - controller reference temperature
           -------------------------------------------------------------------------------------------------------"""
    @QtCore.pyqtSlot()
    def startClicked(self):
        if not self.systemIsRunning:
            setTemp = self.adjustTemp.text()
            setTemp = setTemp[0:3]
            setTemp = float(setTemp)
            self.sendTemp.emit(setTemp)
            self.startButton.setText("Stop")
            self.systemIsRunning = True
        else:
            self.startButton.setText("Start")
            self.systemIsRunning = False
        self.systemState.emit(self.systemIsRunning, True)

    """-------------------------------------------------------------------------------------------------------
           Description: Event handler for set temp adjustment, sends set temp to controller
                Inputs: None
               Outputs: emits new set temp
           -------------------------------------------------------------------------------------------------------"""
    @QtCore.pyqtSlot()
    def setTempUpdate(self):
        newSetTemp = self.adjustTemp.value()
        self.sendTemp.emit(newSetTemp)



    @QtCore.pyqtSlot(int)
    def updateStatus(self,status):
        if status is 0:
            self.timerDescription.setText("Idle")
        elif status is 1:
            self.timerDescription.setText("Heating")
        elif status is 2:
            self.timerDescription.setText("Incubating")
        elif status is 3:
            self.timerDescription.setText("Complete")


    ##############################################################################
    #
    # Function Description: This function is used to send updated data to gui
    # Last Edited: 10/13/2016
    # Last Edited By: Jonathan Wesner
    # Last Changes Made: ...
    #
    ############################################################################
    @QtCore.pyqtSlot(float)
    def setTemps(self, bagTempAvg):
        self.bagTemp.setText("%.1f" % bagTempAvg)
	
	

    ##############################################################################
    #
    # Function Description: returns the property which has focus and changes the
    #                       focus based on direction given
    # Last Edited: 11/15/2016
    # Last Edited By: Jonathan Wesner
    # Last Changes Made: ...
    #
    ##############################################################################
    def getButtonFocus(self):
        # length of property table
        lengthOfTable = len(self.propertyTable)
        count = 0
        for propertyInTable in self.propertyTable :
            if propertyInTable.hasFocus() == True :
                self.focusedProperty = propertyInTable
                break
            count = count + 1


    ##############################################################################
    #
    # Function Description: This function is called whenever an error message
    #                       needs to be displayed to the screen.
    # Last Edited: 10/17/2016
    # Last Edited By: Jonathan Wesner
    # Last Changes Made: ...
    #
    ##############################################################################
    def displayError(self, errorText):
        self.errorPopup.errorMessage.setText(errorText)
        # Freezes the Main Window till a response is made by the user for MyPopup()
        self.errorPopup.setWindowModality(QtCore.Qt.ApplicationModal)
        self.errorPopup.show()

    #----------------------------------------------------------------------------------------------------------#
    #                            INSTRUCTIONS TO GET KEYSTROKES FOR RASPBERRY PI
    # sudo pip install python2.7 - xlib, sudo apt - get install scrot, sudo apt - get install python2.7 - tk, and
    # sudo apt - get install python2.7 - dev
    # pip install pyautogui
    #----------------------------------------------------------------------------------------------------------#

    """-------------------------------------------------------------------------------------------------------
   Description: Event handler for up button, down button, back button, and select button
        Inputs: None
       Outputs: None
   -------------------------------------------------------------------------------------------------------"""
    @QtCore.pyqtSlot()
    def upButtonHandler(self):
        pyautogui.press('up')

    @QtCore.pyqtSlot()
    def downButtonHandler(self):
        pyautogui.press('down')

    @QtCore.pyqtSlot()
    def backButtonHandler(self):
        pyautogui.press('tab')

    @QtCore.pyqtSlot()
    def selectButtonHandler(self):
        pyautogui.press('enter')
##        self.getButtonFocus()
##        if self.focusedProperty is self.startButton :
##            self.startClicked()
##            return
##        if self.focusedProperty is self.saveButton :
##            return
##        #if self.focusedProperty is self.shutdownButton :
##        #    self.shutdownPressed.emit()
##        #    return
##        if self.focusedProperty is self.errorPopup.errorButton :
##            self.errorPopup.close()
##            return

