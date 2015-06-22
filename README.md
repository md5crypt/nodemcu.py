## nodemcu.py

this script can:
* send and read data to and from the device 
* paste command sequence from clipboard
* paste any file (binary) to the device filesystem from clipboard or file
* has a working command history and arrow keys
* cross-compile to bytecode using luac-cross (windows binary included in this repo)
* compile to bytecode using string.dump on the device (survives larger files then file.compile)

it needs the following python modules
* pyserial
* clipboard

I'm writing this script on windows, and just occasionally check if it still works under linux.

script command line help:
```
usage: nodemcu.py device [boudrate]

  device should be COM(\d+) for windows
  and full device path fo unix

  boudrate if omitted is set to 9600
  can be any number or 'fast' for 460800
```

when the script starts and connects with nodemcu, it will show the lua interpreter prompt. You can send any lua command or use one of the build in commands:


```
:uart [boudrate]          - dynamic boudrate change
:load src                 - evaluate file content
:file dst src             - write local file src to dst
:paste [file]             - evaluate clipboard content
                            or write it to file if given
:cross-compile dst [file] - compile file or clipboard using
                            luac-cross and save to dst
:execute [file]           - cross-compile and execute clipboard or
                            file content without saving to flash
:soft-compile dst [file]  - compile file or clipboard on device
                            and save do dst. This call can handle
                            lager files than file.compile
```

##### By default nodemcu has uart echo turned on. This application will NOT work with echo on. Run the ":uart" command to turn it off. You have to do it every nodemcu restart or put "uart.setup(0,9600,8,0,1,0)" to init.lua

notice that the commands start with a ':'

you can use command prefixes (like ':p' or ':u')

the :uart parameter defaults to 9600 and can be 'fast' for 460800

:load and :paste evaluates commands so when you will use :p with clipboard content "print(1)\n:p" you get a beautiful loop

##### in the beginning of the script there is a constant LUAC_PATH. Set to point to your luac-cross binary

here are instruction how to compile luac-cross (http://www.esp8266.com/viewtopic.php?f=24&t=1305)

to exit just hit ctrl-c