import thread,threading,serial,sys,cmd,re,time,clipboard,base64,binascii

sem = None

class Repl(cmd.Cmd):
	prompt = ''
	def do_help(self, line):
		print(
			":uart [boudrate]\t: dynamic boudrate change\n"
			":file dst src   \t: write local file dst to src\n"
			":paste [file]   \t: execute clipboard content\n"
			"                \t  or write it to file if given (tranfer will be binary)\n" )
		sys.stdout.write(reader_prompt)
	def do_EOF(self, line):
		return True
	def default(self, line):
		if line[0] == ':':
			if command(line) is not None:
				sys.stdout.write(reader_prompt)
			return
		sem.acquire()
		tty.write(line+"\r\n")
	def emptyline(self):
		sem.acquire()
		tty.write("\r\n")
replcmd = Repl()

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
	tty = serial.Serial(sys.argv[1],boud,timeout=None)
	thread.start_new_thread(reader,(tty,))
	sys.stdout.write("\r")
	sys.stdout.flush()
	tty.write("\r\n")
	
def tty_send(cmd):
	print(cmd)
	tty.write(cmd+"\r\n")

#base64 decode and crc32 file check, wrote to be small, not fast
lualib = [
	'function __c32__(f,v) local crc,aku=function(s,c) local n,x,r,p=bit.bnot,bit.bxor,bit.rshift,0xEDB88320 c=n(c) for i=1,s:len() do c=x(c,s:byte(i,i)) for j=0,7 do if bit.band(c,1)~=0',
	'then c=x(r(c,1),p) else c=r(c,1) end end end return n(c) end,0 file.open(f,"r") local l=file.read(128) while l~=nil do tmr.wdclr() aku=crc(l,aku) l=file.read(128) end if aku==v then',
	'print("CRC OK") else print("CRC MISSMATCH!") end file.close() end function __dec__(d) local b,ban,rsh,l,out="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/",bit.band',
	',bit.rshift,0,"" for i=1,d:len() do l=l+b:find(d:sub(i,i))-1 if i%4==0 then out=out..string.char(rsh(l,16),ban(rsh(l,8),255),ban(l,255)) l=0 end l=bit.lshift(l,6) end return out end'
]
cmd_list = ['uart','paste','help','file']
	
def find_cmd(cmd):
	cnt = 0
	m = 0
	for k in cmd_list:
		if k.find(cmd) == 0:
			cnt += 1;
			m = k;
	return m if cnt==1 else None;

def command(line):
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
	elif cmd == 'paste' or cmd == 'file':
		if cmd == 'file':
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
			buff = clipboard.paste()
		if len(args) > 1:
			head = []
			head += lualib
			#sometimes file.open(_,"w") kept on returning nil until the first read operation on it. So I wrote a little hack:
			head.append('file.close() if file.open("{0}","r") then file.read(0) file.seek("set") file.close() end file.open("{0}","w")'.format(args[1]))
			for i in xrange(0,len(buff),126):
				if i+125 < len(buff):
					head.append('file.write(__dec__("{0}"))'.format(base64.b64encode(buff[i:i+126])))
				else:
					tail = buff[i:]
					r = 3-(len(tail)%3)
					sub = ''
					if r!=3:
						tail += ' '*r
						sub = ':sub(1,-{0})'.format(r+1)
					head.append('file.write(__dec__("{0}"){1})'.format(base64.b64encode(tail),sub))
			head.append('file.close() __c32__("{0}",{1}) __c32__=nil __dec__=nil collectgarbage()'.format(args[1],binascii.crc32(buff)))
		else:
			head = re.split("[\r\n]+",buff)
		sys.stdout.write(reader_prompt)
		for x in head:
			sem.acquire()
			tty_send(bytes(x))

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
			sem.release()
			reader_prompt = x.group(0)
			end = x.end(0)
		if end > 0:
			buff = buff[end:]
	reader_quit = False

def run():
	global reader_prompt
	print("waiting for prompt...")
	sem.acquire()
	sem.release()
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
			b = 460800
		else:
			b = int(sys.argv[2])
	else:
		b = 9600
	open_tty(b)
	thread.start_new_thread(run,())
	while True:
		try:
			time.sleep(0.1)
		except KeyboardInterrupt:
			exit(0)