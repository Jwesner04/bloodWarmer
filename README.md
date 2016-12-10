# bloodWarmer
Used for prototype of a blood warmer system that incubates two blood bags for an hour on IV pole. 

	Following electrical componenets were used in project:
		1.  2 heaters
		2.  2 Fans
		3.	1 door switch - used for safety measures
		3.  LCD touchscreen from adafruit
		4.  4 buttons - safety measure if touchscreen goes out
		5.  4 Temperature sensors - includes I2C enabling all sensors to be connected onto one bus
		6.  2 pressure sensors - were not used in project due to sensitivity criteria
		7.  Raspberry Pi 3 - handled the output to touchscreen and outputs from microboard
		8.  Custom microboard - handled all sensor inputs and output to Raspberry Pi
		9.  Switch board - controlled duty cycle to heaters and fans, as well as, saftey 
						   measures for all electrical components. All componenets ran to
						   the switch board before going anywhere else.
		10. Power supply - handled a power switch in the back of system and power to system as a 
						   whole. Had 5v, 8v,12v outputs.

This README is used for project discription only and does not include setup. This is a prototype
only, and is not currently used by others for referencing. 


