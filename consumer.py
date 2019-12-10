#! /usr/local/bin/python3 

# This is a conumer example.

from ctypes import c_int, c_double, c_byte, c_bool, Structure, sizeof
from random import random
import mmap
import os
from datetime import datetime
import asyncio

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
	def __init__(self, interval, recsToGet) :
		self.startTime = None
		self.bDone = False
		self.interval = interval
		self.recNum = 0
		self.taShare = None
		self.taData = None
		self.mmShare = None
		self.mmfd = None
		self.lastIdx = -1
		self.recsToGet = recsToGet
		self.recsGot = 0
		self.initialize()

	@asyncio.coroutine
	def consume(self) :
		while not self.bDone :
			tash = TAShare.from_buffer(self.mmShare)
			while not self.lastIdx == tash.recIdx :
				self.lastIdx += 1
				if self.lastIdx == recCount :
					self.lastIdx = 0
				tad = TAData.from_buffer(tash.data[self.lastIdx])
				print('C: {0:4d} {1:10.3f} {2:10.3f} {3:10.3f} {4:10.3f} {5:10.3f} {6:10.3f} {7:d}'.format( \
					tad.recNum, tad.recTime, \
					tad.temp1, tad.temp2, tad.temp3, \
					tad.pH2O, tad.pCO2, tad.status))

				self.recsGot += 1

			if self.recsGot == self.recsToGet :
				cmdBuf = bytearray('%EXIT', encoding)
				cmdBuf.extend([0] * (80 - len(cmdBuf)))
				tash.command[0:80] = cmdBuf
				self.mmfd.close()
				self.bDone = True
			yield from asyncio.sleep(self.interval)

		return 0
		
	def initialize(self) :
		self.mmfd = open('taShare', 'r+b')
		self.mmShare = \
			mmap.mmap(self.mmfd.fileno(), sizeof(TAShare), \
				mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE)

# main program
cons = consumer(2, 10)
loop = asyncio.get_event_loop()
loop.run_until_complete(cons.consume())
loop.close()
