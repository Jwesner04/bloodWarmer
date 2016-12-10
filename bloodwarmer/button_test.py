import sys, time, os, pyautogui
from PyQt4 import QtCore, QtGui, uic


# Include user interface files
qtMainWindowFile = "interface.ui"
qtMyPopUpFile = "myPopUp.ui"

Ui_MainWindow, QtBaseClass = uic.loadUiType(qtMainWindowFile)
Ui_PopUpWindow, QtSubClass = uic.loadUiType(qtMyPopUpFile)


# ----------------------------------------------------------------------------#
#
# Class Description: This class is used for the main window.
# Last Edited: 10/13/2016
# Last Edited By: Jonathan Wesner
# Last Changes Made: ...
#
# ----------------------------------------------------------------------------#
class MainWindow(QtGui.QMainWindow, Ui_MainWindow):
    sendTemp = QtCore.pyqtSignal(float)
    startSystem = QtCore.pyqtSignal()

    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)
        self.setupUi(self)

        # ---------------------------------------------------#
        # Local Variables
        # ---------------------------------------------------#
        self.hours = 0
        self.minutes = 0
        self.seconds = 0
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.outputTime)
        self.timer.start(1000)
        self.systemIsRunning = False
        self.targetedTemperature = 0
        self.focusedProperty = self.startButton.setFocus()
        self.propertyTable = [self.startButton, self.saveButton, self.shutdownButton, self.helpButton, self.adjustTemp]
        self.startButton.clicked.connect(self.enterKey)
        # ---------------------------------------------------#
        # User Interface Property changes
        # ---------------------------------------------------#
        # Fills whole screen depending on screen size
        # self.showFullScreen()
        # Change mouse cursor when hovering over button
        self.startButton.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        # Set minimum and maximum values for adjusted temperature
        self.adjustTemp.setRange(37, 41)
        self.adjustTemp.setDecimals(1)
        self.adjustTemp.setSingleStep(.1)
        self.adjustTemp.setSuffix("C")
        pyautogui.press('/n')
        
    def enterKey(self) :
        self.systemIsRunning = True
        
    # Start Timer
    def outputTime(self) :
        if self.systemIsRunning is False :
            return
        self.seconds = self.seconds + 1
        if self.seconds == 60:
            self.seconds = 0
            self.minutes = self.minutes + 1
        if (self.minutes == 60):
            self.minutes = 0
            self.hours = self.hours + 1
        if self.hours == 2:
            self.stopTime()
            self.stopSystem()
            self.displayError("System has stopped as bags have been heated for too long")

        # Output time to Label
        self.bagTimer.setText(
            '{:02.0f}'.format(self.hours) + ":" + '{:02.0f}'.format(self.minutes) + ":" + '{:02.0f}'.format(
                self.seconds))
        self.bagTimer.setText(
            '{:02.0f}'.format(self.hours) + ":" + '{:02.0f}'.format(self.minutes) + ":" + '{:02.0f}'.format(
                self.seconds))

if __name__ == "__main__":
    #TODO Move all initialization into one function
    app = QtGui.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
