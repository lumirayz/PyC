################################################################
# Imports
################################################################
import socket
import select
import time

################################################################
# Util
################################################################
from inspect import isgenerator

class FlattenedGenerator:
	def __init__(self, gen):
		self.genstack = [gen]
	
	def __iter__(self):
		try:
			while True:
				yield next(self)
		except StopIteration:
			pass
	
	def __next__(self):
		return self.send(None)
	
	def send(self, val):
		while True:
			try:
				n = self.genstack[-1].send(val)
				if isgenerator(n):
					self.genstack.append(n)
					return next(self)
				return n
			except StopIteration as e:
				self.genstack.pop(-1)
				if len(self.genstack) == 0:
					raise e

def _flatten(gen):
	return FlattenedGenerator(gen)

################################################################
# Instruction
################################################################
IN_WaitTime = 0 #until = target in epoch time

IN_WaitSocketConnect = 100 #host = host, port = port
IN_WaitSocketRead = 101 #sock = socket
IN_WaitSocketListen = 102 #host = host, port = port
IN_WaitSocketAccept = 103 #sock = socket

IN_Return = 200 #values = return values

class Instruction:
	def __init__(self, itype, **kw):
		self.itype = itype
		self.params = kw

def wait(ms):
	return Instruction(IN_WaitTime, until = time.time() + ms / 1000)

def connect(host, port):
	return Instruction(IN_WaitSocketConnect, host = host, port = port)

def listen(host, port):
	return Instruction(IN_WaitSocketListen, host = host, port = port)

################################################################
# Reactor
################################################################
sockets = list()
coroutines = list()

def start():
	while(True):
		if _checkAllDone():
			break
		rs, ws, es = select.select(
			[so._sock for so in sockets],
			[so._sock for so in filter(lambda so: len(so._wbuf) != 0, sockets)],
			[],
			0.05
		)
		for sock in ws:
			so = _s2s[sock]
			sent = sock.send(so._wbuf)
			so._wbuf = so._wbuf[sent:]
		for co in list(coroutines):
			instr = co.instr
			if not isinstance(instr, Instruction):
				co.step(instr)
				break
			if instr.itype == IN_WaitTime:
				if(instr.params["until"] <= time.time()):
					co.instr = None
					co.step(None)
			elif instr.itype == IN_WaitSocketConnect:
				s = socket.socket()
				s.connect((instr.params["host"], instr.params["port"]))
				s.setblocking(False)
				so = Socket(s)
				co.instr = None
				sockets.append(so)
				co.step(so)
			elif instr.itype == IN_WaitSocketRead:
				sock = instr.params["sock"]
				if sock in rs:
					so = _s2s[sock]
					try:
						data = sock.recv(1024)
						if len(data) > 0:
							co.step(data)
						else:
							sockets.remove(so)
							co.step(None)
					except socket.error:
						pass
			elif instr.itype == IN_WaitSocketAccept:
				sock = instr.params["sock"]
				if sock in rs:
					newsock, addr = sock.accept()
					newsock.setblocking(False)
					so = Socket(newsock)
					sockets.append(so)
					co.step(so)
			elif instr.itype == IN_Return:
				co.step(instr.params["value"])
			elif instr.itype == IN_WaitSocketListen:
				s = socket.socket()
				s.bind((instr.params["host"], instr.params["port"]))
				s.listen(5)
				s.setblocking(False)
				so = Socket(s)
				sockets.append(so)
				co.step(so)

def _checkAllDone():
	for co in coroutines:
		if not co.done:
			return False
	return True

def spawn(func, *args, **kw):
	gen = func(*args, **kw)
	co = Coroutine(gen)
	coroutines.append(co)
	co.instr = Instruction(IN_WaitTime, until = 0)

################################################################
# Coroutine
################################################################
class Coroutine:
	def __init__(self, gen):
		self.gen = _flatten(gen)
		self.instr = None
		self.done = False
	
	def step(self, val):
		try:
			self.instr = self.gen.send(val)
		except StopIteration:
			self.done = True
	
	def throw(exc, value = None, tb = None):
			self.gen.throw(exc, value, tb)

################################################################
# Socket
################################################################
_s2s = dict()
class Socket:
	def __init__(self, sock):
		_s2s[sock] = self
		self._sock = sock
		self._wbuf = b""
		self._rbuf = b""
	
	def readAny(self):
		return Instruction(IN_WaitSocketRead, sock = self._sock)
	
	def readUntil(self, seq):
		while True:
			data = yield self.readAny()
			if data == None:
				yield None
				return
			self._rbuf += data
			if self._rbuf.find(seq) != -1:
				d = self._rbuf.split(seq)
				self._rbuf = seq.join(d[1:])
				yield d[0]
				return
	
	def accept(self):
		return Instruction(IN_WaitSocketAccept, sock = self._sock)
	
	def write(self, data):
		self._wbuf += data
