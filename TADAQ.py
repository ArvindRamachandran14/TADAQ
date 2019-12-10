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
		('SC_T_Set', c_double),
		('CC_T_Set', c_double),
		('DPG_T_Set', c_double),
		('SC_P', c_double),
		('CC_P', c_double),
		('DPG_P', c_double),
		('SC_I', c_double),
		('CC_I', c_double),
		('DPG_I', c_double),
		('SC_D', c_double),
		('CC_D', c_double),
		('DPG_D', c_double),
		('SC_State', c_double),
		('CC_State', c_double),
		('DPG_State', c_double),
		('SC_Output', c_double),
		('CC_Output', c_double),
		('DPG_Output', c_double),
		('Cell_pressure', c_double),
		('Cell_temp', c_double),
		('IVOLT', c_double),
		('pH2O', c_double),
		('pCO2', c_double),
		('Dew_point_temp', c_double),
		('Sample weight', c_double),
		('V_state', c_double),
		('Run', c_int),
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
		self.taShare = Noneedq
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
				tash.data[recIdx].SC_T_Set = data_dict['SC_T_Set']
				tash.data[recIdx].CC_T_Set = data_dict['CC_T_Set']
				tash.data[recIdx].DPG_T_Set = data_dict['DPG_T_Set']
				tash.data[recIdx].SC_P = data_dict['SC_P']
				tash.data[recIdx].CC_P = data_dict['CC_P']
				tash.data[recIdx].DPG_P = data_dict['DPG_P']
				tash.data[recIdx].SC_I = data_dict['SC_I']
				tash.data[recIdx].CC_I = data_dict['CC_I']
				tash.data[recIdx].DPG_I = data_dict['DPG_I']
				tash.data[recIdx].SC_D = data_dict['SC_D'] 
				tash.data[recIdx].CC_D = data_dict['CC_D']
				tash.data[recIdx].DPG_D = data_dict['DPG_D']
				tash.data[recIdx].SC_State = data_dict['SC_State']
				tash.data[recIdx].CC_State = data_dict['CC_State']
				tash.data[recIdx].DPG_State = data_dict['DPG_State']
				tash.data[recIdx].SC_Output = data_dict['SC_Output']
				tash.data[recIdx].CC_Output = data_dict['CC_Output']
				tash.data[recIdx].DPG_Output = data_dict['DPG_Output']
				tash.data[recIdx].Cell_pressure = data_dict['Cell_pressure']
				tash.data[recIdx].Cell_temp = data_dict['Cell_temp']
				tash.data[recIdx].IVOLT = data_dict['IVOLT']
				tash.data[recIdx].pH2O = data_dict['pH2O']
				tash.data[recIdx].pCO2 = data_dict['pCO2']
				tash.data[recIdx].Dew_point_temp = data_dict['Dew_point_temp']
				tash.data[recIdx].Sample weight = data_dict['Sampleweight']
				tash.data[recIdx].V_state = data_dict['V_state']
				tash.data[recIdx].Run = data_dict['Run']
				tash.data[recIdx].Status = data_dict['Status']
				tash.recIdx = recIdx
				print('P: {0:4d} {1:10.3f} {2:10.3f} {3:10.3f} {4:10.3f} {5:10.3f} {6:10.3f} {7:10.3f} {8:10.3f} {9:10.3f} {10:10.3f} {11:10.3f} {12:10.3f} {13:10.3f} {14:10.3f} {15:10.3f} {16:10.3f} {17:10.3f} {18:10.3f} {19:10.3f} {20:10.3f} {21:10.3f} {22:10.3f} {23:10.3f} {24:10.3f} {25:10.3f} {26:10.3f} {27:10.3f} {28:10.3f} {29:10.3f} {30:10.3f} {31:d}, {32:d}'.format( \
					tash.data[recIdx].recNum, tash.data[recIdx].recTime, \
							tash.data[recIdx].recNum, tash.data[recIdx].recTime, tash.data[recIdx].SC_T1, \
							tash.data[recIdx].SC_T2, tash.data[recIdx].CC_T1, tash.data[recIdx].DPG_T1, \
							tash.data[recIdx].SC_T_Set, tash.data[recIdx].CC_T_Set, tash.data[recIdx].DPG_T_Set, \
							tash.data[recIdx].SC_P, tash.data[recIdx].CC_P, tash.data[recIdx].DPG_P, tash.data[recIdx].SC_I, \
							tash.data[recIdx].CC_I, tash.data[recIdx].DPG_I, tash.data[recIdx].SC_D, tash.data[recIdx].CC_D, \
							tash.data[recIdx].DPG_D, tash.data[recIdx].SC_State, tash.data[recIdx].CC_State, tash.data[recIdx].DPG_State, \
							tash.data[recIdx].SC_Output, tash.data[recIdx].CC_Output, tash.data[recIdx].DPG_Output, \
							tash.data[recIdx].Cell_pressure, tash.data[recIdx].Cell_temp, tash.data[recIdx].IVOLT, \
							tash.data[recIdx].pH2O, tash.data[recIdx].pCO2, tash.data[recIdx].Dew_point_temp, \
							tash.data[recIdx].Sample_weight, tash.data[recIdx].V_state, tash.data[recIdx].Run, tash.data[recIdx].Status))
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

		keys = 	['SC_T1','SC_T2','CC_T1','DPG_T1','SC_T_Set','CC_T_Set','DPG_T_Set','SC_P','CC_P','DPG_P','SC_I','CC_I','DPG_I','SC_D','CC_D','DPG_D','SC_State','CC_State','DPG_State','SC_Output','CC_Output','DPG_Output','Cell_pressure','Cell_temp','IVOLT','pH2O','pCO2','Dew_point_temp','Sampleweight','V_state','Run','Status']

		data_dict = {}

		for key in keys:

			data_dict[key] = float(ET.fromstring(Output_string).find(key)[0].text)

		return(data_dict)

# main program
prod = producer(5)
loop = asyncio.get_event_loop()
loop.run_until_complete(prod.produce())
loop.close()