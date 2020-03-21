#! /usr/local/bin/python3 

# This is a conumer example.

from ctypes import c_int, c_double, c_byte, c_bool, Structure, sizeof
from random import random
import mmap
import os
from datetime import datetime
import asyncio
import pykbhit as pykb


encoding = 'utf-8'
loop = None
recCount = 21

class TAData(Structure) :
	_pack_ = 4
	_fields_ = [ \
		('recNum', c_int),
		('recTime', c_double),
		('status', c_int),
		('temp1', c_double),
		('temp2', c_double),
		('temp3', c_double),
		('pH2O', c_double),
		('pCO2', c_double)]

class TAShare(Structure) :
	_pack_ = 4
	_fields_ = [ \
			('command', c_byte * 80),
			('reply', c_byte * 80),
			('recCount', c_int),
			('recIdx', c_int),
			('data', TAData * recCount)]

class consumer() :
	def __init__(self, interval) :
		self.startTime = None
		self.bDone = False
		self.interval = interval
		self.recNum = 0
		self.taShare = None
		self.taData = None
		self.mmShare = None
		self.mmfd = None
		self.lastIdx = -1
		self.recsGot = 0
		self.initialize()
		self.kb = pykb.KBHit()

	# consume
	# This function gets unread data from the shared memory circular
	# buffer at the specified interval.
	async def consume(self) :
		while not self.bDone :
			tash = TAShare.from_buffer(self.mmShare)
			while not self.lastIdx == tash.recIdx :
				self.lastIdx += 1
				if self.lastIdx == recCount :
					self.lastIdx = 0
				tad = TAData.from_buffer(tash.data[self.lastIdx])

				# The only thing done with the data is to print it here.
				print('C: {0:4d} {1:10.3f} {2:10.3f} {3:10.3f} {4:10.3f} {5:10.3f} {6:10.3f} {7:d}'.format( \
					tad.recNum, tad.recTime, \
					tad.temp1, tad.temp2, tad.temp3, \
					tad.pH2O, tad.pCO2, tad.status))

				self.recsGot += 1

			await asyncio.sleep(self.interval)
		return 0

	# getCmd
	# A command is collected, one character at a time, from the keyboard input.
	# Then, the command is tested and modified if needed as below:
	# Exit -> @{EXIT}
	# c <port <baud> -> @{CONNECT} <port> <baud>
	# d -> @{DISCONNECT}
	# The 'Exit', 'c', or 'd' can be in any case.  No translation is done on
	# any other strings, so 'g temp1' will be handled as is.
	async def getCmd(self) :
		line = ''
		bNeedReply = False
		bGotExitCmd = False
		bCmdError = False
		while not self.bDone :
			tash = TAShare.from_buffer(self.mmShare)
			if not bNeedReply :
				if self.kb.kbhit() :
					ch = self.kb.getch()
					if ord(ch) == 10 :      # Carriage return
						cmdParts = line.split(' ')
						cmd = cmdParts[0].upper()
						cmdBuf = []
						if cmd == 'EXIT' :
							cmdBuf = bytearray('@{EXIT}', encoding)
							bGotExitCmd = True
						elif cmd == 'C' :
							if len(cmdParts) == 3:
								cmdBuf = \
									bytearray('@{{CONNECT}} {0} {1}'. \
										format(cmdParts[1], cmdParts[2]), \
										encoding)
							else:
								bCmdError = True
						elif cmd == 'D' :
							cmdBuf = bytearray('@{DISCONNECT}', encoding)
						else :
							cmdBuf = bytearray(line, encoding)
						if not bCmdError :
							tash.command[0:len(cmdBuf)] = cmdBuf
							sCmd = cmdBuf.decode(encoding).rstrip('\x00')
							print(f'Command: {sCmd}')
							bNeedReply = True
						else :
							print('Command error.')
							bCmdError = False
						line = ''
					else :
						line = line + ch
			else :
				rBuf = bytearray(tash.reply)
				sRep = rBuf.decode(encoding).rstrip('\x00')
				if len(sRep) > 0 :
					print(f'Reply: {sRep}')
					bNeedReply = False
					if bGotExitCmd :
						self.bDone = True

			await asyncio.sleep(0.050)
		
	def initialize(self) :
		self.mmfd = open('taShare', 'r+b')
		self.mmShare = mmap.mmap(self.mmfd.fileno(), sizeof(TAShare))

# main program
async def main() :
	cons = consumer(2)

	print('Type \"Exit\" when ready to quit...')
	task1 = asyncio.create_task(cons.consume())
	task2 = asyncio.create_task(cons.getCmd())
	await task1
	await task2

if __name__ == '__main__':
    asyncio.run(main())