MARS MS-DMT and MARS-ALE serial port mux

use VSP Manager by K5FR to create 2 COM port pairs
configure MS-DMT to point at one side of one pair
configure MARS-ALE to point at one side of the other pair

app will create dmtalemux.ini upon first launch.  .ini file is editable directly if so desired.

Launch with .bat file if applicaion errors and closes before you can see output (batch file will pause and let you see error messages)


example:
COM 14 <-> COM 15 
COM 16 <-> COM 17 
Radio is on COM7  at 19200 baud

MS-DMT is configured to COM 14
MARS-ALE is configured to COM 16

