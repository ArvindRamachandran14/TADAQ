#! /usr/local/bin/python3 

from ctypes import c_int, c_double, c_byte, c_bool, Structure, sizeof #creates c type structures
from random import random #random numbers
import mmap #memory map
import os 
from datetime import datetime
import asyncio #timing to work right asychronous call - go and read the data and the meanwhile you can do other things
import serial
import xml.etree.ElementTree as ET

encoding = 'utf-8' # covers straight ascii 8 bit char codes 
loop = None #variable timeer uses
recCount = 21 #how many records are in the shared memory 

ser = serial.Serial('/dev/ttyUSB0', 9600, timeout=3)

class TAData(Structure) :
	_pack_ = 4
	_fields_ = [ \
		('recNum', c_int),
		('recTime', c_double),
		('SC_T1', c_double),
		('SC_T2', c_double),
		('CC_T1', c_double),
		('DPG_T1', c_double),
		('pH2O', c_double),
		('pCO2', c_double),
		('Dew_point_temp', c_double),
		('Sample_weight', c_double),
		('Status', c_int)
		]

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
				data_dict = self.getDataFromTA()

				# Get the time
				now = datetime.now()
				seconds = now.hour * 3600 + now.minute * 60 + now.second + now.microsecond / 1000000
				if self.startTime == None :
					self.startTime = seconds
				seconds = seconds - self.startTime

				tash.data[recIdx].recNum = self.recNum
				self.recNum += 1
				tash.data[recIdx].recTime = seconds
				tash.data[recIdx].SC_T1 = data_dict['SC_T1']
				tash.data[recIdx].SC_T2 = data_dict['SC_T2']
				tash.data[recIdx].CC_T1 = data_dict['CC_T1']
				tash.data[recIdx].DPG_T1 = data_dict['DPG_T1']
				tash.data[recIdx].pH2O = data_dict['pH2O']
				tash.data[recIdx].pCO2 = data_dict['pCO2']
				tash.data[recIdx].Dew_point_temp = data_dict['Dew_point_temp']
				tash.data[recIdx].Sample_weight = data_dict['Sample_weight']
				tash.data[recIdx].Status = data_dict['Status']
				tash.recIdx = recIdx
				print('P: {0:4d} {1:10.3f} {2:10.3f} {3:10.3f} {4:10.3f} {5:10.3f} {6:10.3f} {7:10.3f} {8:10.3f} {9:10.3f} {10:d}'.format( \
					tash.data[recIdx].recNum, tash.data[recIdx].recTime, \
					tash.data[recIdx].SC_T1, tash.data[recIdx].SC_T2, tash.data[recIdx].CC_T1, tash.data[recIdx].DPG_T1, \
					tash.data[recIdx].pH2O, tash.data[recIdx].pCO2, tash.data[recIdx].Dew_point_temp, \
					tash.data[recIdx].Sample_weight, tash.data[recIdx].Status))
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

		ser.write('g-all\n'.encode())

		Output_string = ser.readline().decode()
		
		root = ET.fromstring(Output_string)

		keys = 	['SC_T1','SC_T2','CC_T1','DPG_T1','pH2O','pCO2','Dew_point_temp','Sample_weight','Status']

		data_dict = {}

		for i in range(len(keys)):
			
			if i < 8:

				data_dict[keys[i]] = float(ET.fromstring(Output_string).find(keys[i])[0].text)

			else:
				
				data_dict[keys[i]] = int(ET.fromstring(Output_string).find(keys[i])[0].text)


		return(data_dict)

# main program
prod = producer(5)
loop = asyncio.get_event_loop()
loop.run_until_complete(prod.produce())
loop.close()
