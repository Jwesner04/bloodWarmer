- Open Designer
- Design file.ui
- When file.ui is finished, run the following command in command line in the same folder file.ui is saved in:
	pyuic4.bat -x file.ui -o file.py 
- file.py can now be opened in IDLE. 


- To save images, include all images into a resource_file.qrc
- The structure of this file is shown below, and is an example that can be followed:
	<RCC>
  	   <qresource prefix="/">
    		<file>img/zimmer.jpg</file>
    		<file>img/1050_7.png</file>
  	   </qresource>
	</RCC>
- resource_file.qrc should be saved in the same folder as file.py from above. 
- Run the following command in command line in the same folder file.py is saved in:
	pyrcc4.exe -o images.py resource_file.qrc  --windows
	pyrcc4 -o images_rc.py images.qrc  -- raspberry pi
- Then add images into file.py at the top with the command below:
	import images
- This will now import the images that are being used in the compiled file.py code. This is important to do so that you know if your resource files are being properly uploaded with the ui. Once your ui is how you want it both within designer and IDLE, move on to the next step.

- Now that we have done the above, we do not want to change the actual ui created. So create a new file called "myapp.py" or what ever name you want. Then input the following skeleton:

1	import sys
2	from PyQt4 import QtCore, QtGui, uic
3 
4	qtCreatorFile = "test.ui" # Enter file here.
5
6	Ui_MainWindow, QtBaseClass = uic.loadUiType(qtCreatorFile)
7 
8	class MyApp(QtGui.QMainWindow, Ui_MainWindow):
9   	    def __init__(self):
10          QtGui.QMainWindow.__init__(self)
11          Ui_MainWindow.__init__(self)
12          self.setupUi(self)
13
14	    self.leftTempInput.setText("40 degrees")
15 
16	if __name__ == "__main__":
17	    app = QtGui.QApplication(sys.argv)
18	    window = MyApp()
19	    window.show()
20	    sys.exit(app.exec_())

- The key information to note in the code above is line 4, which allows us to connect the user interface file with a     controller app. Change line 4 to the name of your user interface file within the quotes



