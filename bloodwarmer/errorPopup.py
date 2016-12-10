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
qtMyPopUpFile = "/home/pi/Documents/BloodWarmer/errorPopUp.ui"
Ui_PopUpWindow, QtSubClass = uic.loadUiType(qtMyPopUpFile)

class errorPopup(QtGui.QWidget, Ui_PopUpWindow):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        Ui_PopUpWindow.__init__(self)
        self.setupUi(self)
        self.errorButton.clicked.connect(self.close)



    @QtCore.pyqtSlot(str)
    def setError(self, errorText):
        self.setText(errorText)
        # Freezes the Main Window till a response is made by the user for MyPopup()
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.show()
