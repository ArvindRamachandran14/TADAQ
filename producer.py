#! /usr/local/bin/python3 

from ctypes import c_int, c_double, c_byte, c_bool, Structure, sizeof #creates c type structures
from random import random #random numbers
import mmap #memory map
import os 
from datetime import datetime
import asyncio #timing to work right asychronous call - go and read the data and the meanwhile you can do other things

encoding = 'utf-8' # covers straight ascii 8 bit char codes 
loop = None #variable timeer uses
recCount = 21 #how many records are in the shared memory 

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
			('command', c_byte * 80), # 80 byte buffer
			('reply', c_byte * 80),
			('recCount', c_int),
			('recIdx', c_int),
			('data', TAData * recCount)]

class producer() :
	def __init__(self, interval) :
		self.startTime = None
		self.bDone = False
		self.interval = interval
		#self.bForked = False
		self.recNum = 0
		self.taShare = None
		self.taData = None
		self.mmShare = None
		self.mmfd = None
		self.startTime = None
		self.initialize()

	@asyncio.coroutine
	def produce(self) :
		temp1 = temp2 = temp3 = pH2O = pCO2 = 0.0
		status = 0
		tash = TAShare.from_buffer(self.mmShare)
		while not self.bDone :
			command = bytearray(tash.command).decode(encoding).rstrip('\x00')
			if command == '%EXIT' :
				self.mmfd.close()
				self.bDone = True
			else :
				recIdx = tash.recIdx + 1
				if recIdx >= tash.recCount :
					recIdx = 0

				# Get some data
				(temp1, temp2, temp3, pH2O, pCO2, status) = self.getDataFromTA()

				# Get the time
				now = datetime.now()
				seconds = now.hour * 3600 + now.minute * 60 + now.second + now.microsecond / 1000000
				if self.startTime == None :
					self.startTime = seconds
				seconds = seconds - self.startTime

				tash.data[recIdx].recNum = self.recNum
				self.recNum += 1
				tash.data[recIdx].recTime = seconds
				tash.data[recIdx].temp1 = temp1
				tash.data[recIdx].temp2 = temp2
				tash.data[recIdx].temp3 = temp3
				tash.data[recIdx].pH2O = pH2O
				tash.data[recIdx].pCO2 = pCO2
				tash.data[recIdx].status = status

				tash.recIdx = recIdx
				print('P: {0:4d} {1:10.3f} {2:10.3f} {3:10.3f} {4:10.3f} {5:10.3f} {6:10.3f} {7:d}'.format( \
					tash.data[recIdx].recNum, tash.data[recIdx].recTime, \
					tash.data[recIdx].temp1, tash.data[recIdx].temp2, tash.data[recIdx].temp3, \
					tash.data[recIdx].pH2O, tash.data[recIdx].pCO2, tash.data[recIdx].status))
				yield from asyncio.sleep(self.interval)

		return 0
		
	def initialize(self) :
		tempTASH = TAShare()
		tempTASH.command[0:80] = [0] * 80
		tempTASH.reply[0:80] = [0] * 80
		tempTASH.recCount = recCount
		tempTASH.recIdx = -1
		self.mmfd = open('taShare', 'w+b') # read and write, binary file memory mapped file descriptor
		L = self.mmfd.write(tempTASH) #size of the files
		self.mmfd.flush() #
		print('Mapped size: ', L)
		self.mmShare = \
			mmap.mmap(self.mmfd.fileno(), sizeof(tempTASH), \
				mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE)

	def getDataFromTA(self) :
		temp1 = 25 + 2 * (random() - 0.5)
		temp2 = 15 + 2 * (random() - 0.5)
		temp3 = 40 + 2 * (random() - 0.5)
		pH2O = 3000 + 10 * (random() - 0.5)
		pCO2 = 40 + 0.5 * (random() - 0.5)
		status = 0
		return (temp1, temp2, temp3, pCO2, pH2O, status)

# main program
prod = producer(5)
loop = asyncio.get_event_loop()
loop.run_until_complete(prod.produce())
loop.close()