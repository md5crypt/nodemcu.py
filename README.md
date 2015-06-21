
## nodemcu.py

this script can:
* send and read data to and from the device 
* paste command seq. from clipboard
* paste any file (binary) to the device filesystem from clipboard or file
* has a working command history and arrow keys

if needs the following python modules
* pyserial
* clipboard

script command line help:
```
usage: nodemcu.py device [boudrate]

  device should be COM(\d+) for windows
  and full device path fo unix

  boudrate if ommited is set to 9600
  can be any number or 'fast' for 460800
```

when the scirpt starts and connectes with nodemcu, it will show the lua intereter promp. You can send any lua command or use one of the build in commands:


```
:uart [boudrate]        : dynamic boudrate change
:file dst src           : write local file dst to src (tranfer will be binary)
:paste [file]           : execute clipboard content
                          or write it to file if filename given (tranfer will be binary)
```

##### By default nodemcu has uart echo turned on. File transfers will NOT work with echo on. Run the ":uart" command to turn it off. You have to do it every nodemcu restart or put "uart.setup(0,9600,8,0,1,0)" to init.lua

notice that the commands start with a ':'

you can use command prefixes (like ':p' or ':u')

the :uart parameter defaults to 9600 and can be 'fast' for 460800

to exit just hit ctrl-C

and I'll say it again: THE ARROW KEYS F*** WORK
