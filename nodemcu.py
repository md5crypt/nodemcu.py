import os,thread,threading,serial,sys,cmd,re,time,clipboard,base64,binascii,subprocess

boudrate = 9600
stop_command = True

use_readline = True
if sys.platform == 'win32':
	use_readline = False
else:
	try:
		import readline
	except ImportError:
		use_readline = False

LUAC_PATH = "luac.cross"
LUAC_ARGS = "-cci 32 -cce little  -ccn int 32 -s"

sem = None

def luac_compile(buff):
	p = subprocess.Popen(
		"{0} -o tmp.lc {1} -".format(LUAC_PATH,LUAC_ARGS),
		stdin=subprocess.PIPE,
		shell=True
	)
	p.communicate(buff)
	if p.returncode != 0:
		return None
	with open('tmp.lc','rb') as f:
		out = f.read()
	try:
		os.remove('tmp.lc')
	except:
		pass
	return out

class Repl(cmd.Cmd):
	prompt = ''
	use_rawinput = use_readline	
	def do_help(self, line):
		print(
			":uart [boudrate]          - dynamic boudrate change\n"
			":load src                 - evaluate file content\n"
			":file dst src             - write local file src to dst\n"
			":paste [file]             - evaluate clipboard content\n"
			"                            or write it to file if given\n"
			":cross-compile dst [file] - compile file or clipboard using\n"
			"                            luac-cross and save to dst\n"
			":execute [file]           - cross-compile and execute clipboard or\n"
			"                            file content without saving to flash\n"
			":soft-compile dst [file]  - compile file or clipboard on device\n"
			"                            and save do dst. This call should handle\n"
			"                            lager files than file.compile")
		sys.stdout.write(reader_prompt)
	def default(self, line):
		if line[0] == ':':
			if command(line) is not None:
				sys.stdout.write(reader_prompt)
			return
		tty.write(line+"\r\n")
		sem.acquire()
	def emptyline(self):
		tty.write("\r\n")
		sem.acquire()
	def do_EOF(self,line):
		return True
replcmd = Repl(None)

def kill_tty():
	global reader_quit
	reader_quit = True
	tty.flush()
	tty.close()
	while reader_quit:
		time.sleep(0.01)
		
def open_tty(boud):
	global tty,sem
	sem = threading.Semaphore(0)
	try:
		tty = serial.Serial(sys.argv[1],boud,timeout=0.5)
	except serial.serialutil.SerialException as e:
		print(e)
		os._exit(1)
	thread.start_new_thread(reader,(tty,))
	sys.stdout.write("\r")
	sys.stdout.flush()
	tty.write("\r\n")
	sem.acquire()
	
def tty_send(cmd):
	print(cmd)
	tty.write(cmd+"\r\n")

#base64 decode and crc32 file check, wrote to be small, not fast
lualib_crc = [
	'function __c32__(f,v) local crc,aku=function(s,c) local n,x,r,p=bit.bnot,bit.bxor,bit.rshift,0xEDB88320 c=n(c) for i=1,s:len() do c=x(c,s:byte(i,i))',
	'for j=0,7 do if bit.band(c,1)~=0 then c=x(r(c,1),p) else c=r(c,1) end end end return n(c) end,0 file.open(f,"r") local l=file.read(128) while l~=nil',
	'do tmr.wdclr() aku=crc(l,aku) l=file.read(128) end if aku==v then print("CRC OK") else print("CRC MISSMATCH!") end file.close() end'
]
lualib_b64 = [
	'function __dec__(d) local b,ban,rsh,l,out="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/",bit.band,bit.rshift,0,"" for i=1,d:len()',
	'do l=l+b:find(d:sub(i,i))-1 if i%4==0 then out=out..string.char(rsh(l,16),ban(rsh(l,8),255),ban(l,255)) l=0 end l=bit.lshift(l,6) end return out end'
]

cmd_list = ['uart','paste','help','file','cross-compile','soft-compile','load','execute']
	
def find_cmd(cmd):
	cnt = 0
	m = 0
	for k in cmd_list:
		if k.find(cmd) == 0:
			cnt += 1;
			m = k;
	return m if cnt==1 else None;
	
def base64_split(buff):
	out = []
	for i in xrange(0,len(buff),126):
		if i+125 < len(buff):
			out.append('__dec__("{0}")'.format(base64.b64encode(buff[i:i+126])))
		else:
			tail = buff[i:]
			r = 3-(len(tail)%3)
			sub = ''
			if r!=3:
				tail += ' '*r
				sub = ':sub(1,-{0})'.format(r+1)
			out.append('__dec__("{0}"){1}'.format(base64.b64encode(tail),sub))
	return out

#sometimes file.open(_,"w") kept on returning nil until the first read operation on it. So I wrote a little hack:
OPEN_SEQ = 'file.close() if file.open("{0}","r") then file.read(0) file.seek("set") file.close() end file.open("{0}","w")'
def command(line,reku=False):
	global stop_command
	args = re.split('\s+',line[1:])
	cmd = find_cmd(args[0])
	if cmd == None:
		print("Unknown command "+args[0])
		return False
	if cmd == 'uart':
		if len(args) == 1:
			b = 9600
		elif args[1] == 'fast':
			b = 460800
		else:
			b = args[1]
		sys.stdout.write(reader_prompt)
		tty_send("uart.setup(0,{0},8,0,1,0)".format(b))
		time.sleep(0.5)
		kill_tty()
		open_tty(b)
	elif cmd == 'help':
		replcmd.do_help('')
	elif cmd == 'paste' or cmd == 'file' or cmd.find('compile') or cmd == 'load':
		if cmd == 'file' or cmd == 'load' or (cmd == 'execute' and len(args) == 2) or (cmd.find('compile') and len(args) == 3):
			if cmd == 'load' or cmd == 'execute':
				if len(args)==1:
					print("bad args, should be ':load src'")
					return False
				args.append(args[1])
			if len(args) != 3:
				print("bad args, should be ':file dst src'")
				return False
			try:
				with open(args[2],"rb") as f:
					buff = f.read()
			except IOError:
				print("file {0} not found".format(args[2]))
				return False
		else:
			try:
				buff = bytes(clipboard.paste())
			except UnicodeEncodeError:
				print("invalid clipboard content")
				return False
		if cmd == 'cross-compile' or cmd == 'execute':
			buff = luac_compile(buff)
			if buff == None:
				return False
		if cmd == 'soft-compile':
			head = ["collectgarbage() function __wrapper__()"]
			head += re.split("[\r\n]+",buff)
			head.append("end")
			head.append(OPEN_SEQ.format(args[1]))
			head.append("file.write(string.dump(__wrapper__)) file.close() __wrapper__=nil collectgarbage()")
		elif cmd == 'execute':
			head = ['collectgarbage() __backup__ = c c = {}']
			head += lualib_b64
			for x in reversed(base64_split(buff)):
				head.append('table.insert(c,{0})'.format(x))
			head.append('__code__=c c=__backup__ __backup__=nil')
			head.append('local r,e=load(function() collectgarbage() tmr.wdclr() return table.remove(__code__,#__code__) end) if r==nil then print(e) else r() end __code__= nil')
		elif len(args) > 1 and cmd != 'load':
			head = ['collectgarbage()']
			head += lualib_b64
			head += lualib_crc
			head.append(OPEN_SEQ.format(args[1]))
			for x in base64_split(buff):
				head.append('file.write({0})'.format(x))
			head.append('file.close() __c32__("{0}",{1}) __c32__=nil __dec__=nil collectgarbage()'.format(args[1],binascii.crc32(buff)))
		else:
			head = re.split("[\r\n]+",buff)
		sys.stdout.write(reader_prompt)
		if not reku:
			stop_command = False
		for x in head:
			if stop_command:
				print("aborted")
				break
			if x[0]==':' and (cmd=='load' or cmd=='paste'):
				command(x,True)
			else:
				tty_send(bytes(x))
				sem.acquire()
		if not reku:
			stop_command = True

reader_quit = False
reader_prompt = ''
def reader(tty):
	global reader_quit,reader_prompt
	buff = ""
	regex = re.compile("[>]+ ")
	while not reader_quit:
		sem_inc = 0
		try:
			data = tty.read(1)
			n = tty.inWaiting()
			if n:
				data = data + tty.read(n)
		except:
			if reader_quit:
				break
			raise
		if not data:
			continue
		sys.stdout.write(data)
		buff += data
		end = 0
		for x in regex.finditer(buff):
			reader_prompt = x.group(0)
			if use_readline:
				replcmd.prompt = x.group(0)
			end = x.end(0)
			sem.release()
		if end > 0:
			buff = buff[end:]
			if use_readline:
				sys.stdout.write("\r")
	reader_quit = False

def run():
	global reader_prompt
	print("waiting for prompt...")
	open_tty(boudrate)
	print("\rprompt ok.")
	sys.stdout.write(reader_prompt)
	replcmd.cmdloop()
	
if __name__ == '__main__':
	if len(sys.argv)==1:
		print(
			"usage: nodemcu.py device [boudrate]\n\n"
			"  device should be COM(\d+) for windows\n"
			"  and full device path fo unix\n\n"
			"  boudrate if ommited is set to 9600\n"
			"  can be any number or 'fast' for 460800"
		)
		exit(0)
	if len(sys.argv)>2:
		if 'fast'.find(sys.argv[2])==0:
			boudrate = 460800
		else:
			boudrate = int(sys.argv[2])
	thread.start_new_thread(run,())
	while True:
		try:
			time.sleep(0.1)
		except KeyboardInterrupt:
			if not stop_command:
				stop_command = True
			else:
				if use_readline:
					os.system('stty sane')
				exit(0)