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
qtMyPopUpFile = "/home/pi/Documents/BloodWarmer/myPopUp.ui"
Ui_PopUpWindow, QtSubClass = uic.loadUiType(qtMyPopUpFile)

class myPopup(QtGui.QWidget, Ui_PopUpWindow):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        Ui_PopUpWindow.__init__(self)
        self.setupUi(self)

        # ---------------------------------------------------#
        # User Interface Property changes
        # ---------------------------------------------------#
        self.errorButton.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.errorButton.setFixedWidth(50)

        # ---------------------------------------------------#
        # Call appropriate function on user actions
        # ---------------------------------------------------#
        # Connects to startSystem() function
        self.errorButton.clicked.connect(self.close)

    def setError(self, errorText):
        self.errorMessage.setText(errorText)
        # Freezes the Main Window till a response is made by the user for MyPopup()
        self.errorPopup.setWindowModality(QtCore.Qt.ApplicationModal)
        self.errorPopup.show()