PyC
---
A little coroutine experiment in Python 3.

API
---
`listen(host, port)` -- return a Socket which is listening on `host`, `port`
`Socket.accept()` -- wait until a new socket connects, then return it
`connect(host, port)` -- returns a Socket, connected to the specified `host` and `port`

`Socket.readAny()` -- wait until there is data available and return it
`Socket.readUntil(seq)` -- wait until `seq` received, then return the buffer
`Socket.write(data)` -- put `data` in the write buffer

`spawn(f)` -- spawns `f` as a coroutine

`start()` -- start the reactor

Example
-------
Look at test.py for an example echo server.

License
-------
Public domain, do whatever you'd like.
