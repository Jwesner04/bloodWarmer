# This is a template class for any popup errors that need to be made
# ----------------------------------------------------------------------------#
#
# Class Description: This class is used for messages to user.
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
qtMyPopUpFile = "/home/pi/Documents/BloodWarmer/messagePopUp.ui"
Ui_PopUpWindow, QtSubClass = uic.loadUiType(qtMyPopUpFile)

class messagePopup(QtGui.QWidget, Ui_PopUpWindow):

    runSystem = QtCore.pyqtSignal(bool)
    restartTimer = QtCore.pyqtSignal(bool)
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
        self.okButton.clicked.connect(self.closeMessage)

    @QtCore.pyqtSlot()
    def displayMessage(self):
        # Freezes the Main Window till a response is made by the user for MyPopup()
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.show()
	
    @QtCore.pyqtSlot()
    def closeMessage(self):
	self.close()
