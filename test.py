from pyc.reactor import start, spawn, listen

def main():
	serv = yield listen("0.0.0.0", 1250)
	while True:
		newsock = yield serv.accept()
		spawn(submain, newsock)

def submain(sock):
	while True:
		data = yield sock.readAny()
		if data == None: break
		sock.write(data)

spawn(main)
start()
