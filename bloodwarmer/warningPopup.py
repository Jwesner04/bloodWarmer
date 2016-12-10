# This is a template class for any popup errors that need to be made
# ----------------------------------------------------------------------------#
#
# Class Description: This class is used for error checking and messages
#                    to user.
# Last Edited: 10/13/2016
# Last Edited By: Jonathan Wesner
# Last Changes Made: ...
#
# ----------------------------------------------------------------------------#

#-----------------------------------------------------------#
# INCLUDES
#-----------------------------------------------------------#
from PyQt4 import QtCore, QtGui, uic

#-----------------------------------------------------------#
# LOAD GUI FILE
#-----------------------------------------------------------#
qtMyPopUpFile = "/home/pi/Documents/BloodWarmer/warningPopUp.ui"
Ui_PopUpWindow, QtSubClass = uic.loadUiType(qtMyPopUpFile)

class warningPopup(QtGui.QWidget, Ui_PopUpWindow):

    runSystem = QtCore.pyqtSignal(bool, bool)

    def __init__(self):
        QtGui.QWidget.__init__(self)
        Ui_PopUpWindow.__init__(self)
        self.setupUi(self)

        # ---------------------------------------------------#
        # User Interface Property changes
        # ---------------------------------------------------#
	
		
        # ---------------------------------------------------#
        # Call appropriate function on user actions
        # ---------------------------------------------------#
        # Connects to startSystem() function
        #self.continueButton.clicked.connect(self.close)
		#self.restartButton.clicked.connect(self.close)

    @QtCore.pyqtSlot()
    def setWarning(self):
        # Freezes the Main Window till a response is made by the user for MyPopup()
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.show()

    @QtCore.pyqtSlot()
    def chooseResume(self):
        self.runSystem.emit(True, False)
        self.close()

    @QtCore.pyqtSlot()
    def chooseRestart(self):
        self.runSystem.emit(True, True)
        self.close()
