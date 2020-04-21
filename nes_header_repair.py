#!/bin/python2

# Header fixing script by Kitrinx

# Uses NES 2.0 XML database by NewRisingSun
# https://forums.nesdev.com/viewtopic.php?f=3&t=19940&p=248796

# For NES 2.0 header reference see:
# https://wiki.nesdev.com/w/index.php/NES_2.0

import xml.etree.ElementTree as ET
import hashlib
import binascii
import struct
import os
import errno
import sys
from math import log

# Starting path for directory navigation. Set to /media/fat/games/NES for most MiSTer setups
START_PATH = '.'

# Use NES 2.0 headers. Set to 0 for NES 1.0 header
NES_20 = 1

# Set to 1 to prevent altering any files
TRIAL_RUN = 1

# Set to 1 to enable moving all unrecognised roms to ../unsupported
SORT_UNKNOWN = 1

# Converts unrecognised UNIF roms to unheadered, and adds .unh to all unheadered roms
MARK_UNHEADERED = 1

##### BELOW HERE IS CODE #####

def make_rom_byte(romsize, divis, nes2):
	rombyte = 0
	# logic borrowed from NRS
	if (romsize > 64 * 1024 * 1024 or romsize % divis != 0) and nes2: #exponent notation
		multi = 1
		if romsize % 3 == 0:
			multi = 3
		elif romsize % 5 == 0:
			multi = 5
		elif romsize % 7 == 0:
			multi = 7

		exponent = int(log(romsize / multi, 2))

		rombyte = (exponent << 2 | ((multi - 1) >> 1))
	else:
		rombyte = (int((romsize / divis)) & 0xFF)

	return rombyte

def make_rom_nibble(romsize, divis):
	romnibble = 0
	if romsize > 64 * 1024 * 1024 or romsize % divis != 0: #exponent notation
		romnibble = 0xF
	else:
		romnibble = (int((romsize / divis)) & 0xF00) >> 16

	return romnibble

def find_power_of_two(base10):
	return (int(log(base10 / 64, 2) if base10 > 0 else 0) & 0xF)

def make_header(prgrom, prgram, prgnvram, chrrom, chrram, chrnvram, miscrom, consoleType, consoleRegion, expansion, vsHardware, vsPpu, pcbMirroring, pcbMapper, pcbSubMapper, pcbBattery, nes2):

	mirrornibble = 0
	if pcbMirroring == 'V':
		mirrornibble = 0x1
	elif pcbMirroring == '4':
		mirrornibble = 0x8

	header = bytearray(16)
	header[0] = 0x4E
	header[1] = 0x45
	header[2] = 0x53
	header[3] = 0x1A
	header[4] = make_rom_byte(prgrom, 16384, nes2)
	header[5] = make_rom_byte(chrrom, 8192, nes2)
	header[6] = ((pcbBattery << 1) | mirrornibble | ((pcbMapper & 0xF) << 4))
	header[7] = ((0x8 if nes2 else 0) | (3 if consoleType >= 3 else consoleType) | (pcbMapper & 0xF0))
	if nes2:
		header[8] = (((pcbMapper & 0xF00) >> 8) | ((pcbSubMapper & 0xF) << 4))
		header[9] = (make_rom_nibble(prgrom, 16384) | (make_rom_nibble(chrrom, 8192) << 4))
		header[10] = find_power_of_two(prgram) | ((find_power_of_two(prgnvram)) << 4)
		header[11] = find_power_of_two(chrram) | ((find_power_of_two(chrnvram)) << 4)
		header[12] = (consoleRegion & 0x03)
		header[13] = (((vsHardware & 0x0F) << 4) | (vsPpu & 0x0F)) if (header[7] & 0x3) == 0x1 else (consoleType & 0xF)
		header[14] = (miscrom & 0x3)
		header[15] = (expansion & 0x3F)

	return header

def populate_dict(nes2):
	try:
		tree = ET.parse('nes20db.xml')
	except:
		print("nes20db.xml is missing. Please place it in the same folder as this script.")
		raise
	root = tree.getroot()

	headers = {}

	for child in root:
		sha1 = ''
		prgram = 0
		prgrom = 0
		prgnvram = 0
		chrram = 0
		chrrom = 0
		chrnvram = 0
		miscrom = 0
		consoleType = 0
		consoleRegion = 0
		expansion = 0
		vsHardware = 0
		vsPpu = 0
		pcbMirroring = 'H'
		pcbMapper = 0
		pcbSubMapper = 0
		pcbBattery = 0

		for pet in child:
			if pet.tag == 'rom':
				sha1 = pet.get('sha1')
			elif pet.tag == 'prgrom':
				prgrom = int(pet.get('size'))
			elif pet.tag == 'prgram':
				prgram = int(pet.get('size'))
			elif pet.tag == 'prgnvram':
				prgnvram = int(pet.get('size'))
			elif pet.tag == 'chrrom':
				chrrom = int(pet.get('size'))
			elif pet.tag == 'chrram':
				chrram = int(pet.get('size'))
			elif pet.tag == 'chrnvram':
				chrnvram = int(pet.get('size'))
			elif pet.tag == 'miscrom':
				miscrom = int(pet.get('number'))
			elif pet.tag == 'console':
				consoleType = int(pet.get('type'))
				consoleRegion = int(pet.get('region'))
			elif pet.tag == 'expansion':
				expansion = int(pet.get('type'))
			elif pet.tag == 'pcb':
				pcbMapper = int(pet.get('mapper'))
				pcbSubMapper = int(pet.get('submapper'))
				pcbMirroring = pet.get('mirroring')
				pcbBattery = int(pet.get('battery'))
			elif pet.tag == 'vs':
				vsHardware = int(pet.get('hardware'))
				vsPpu = int(pet.get('ppu'))


		headers[sha1.upper()] = make_header(prgrom, prgram, prgnvram, chrrom, chrram, chrnvram, miscrom, consoleType, consoleRegion, expansion, vsHardware, vsPpu, pcbMirroring, pcbMapper, pcbSubMapper, pcbBattery, nes2)

	return headers

# Python 2 vs 3 compatibility schenanigans
def version_safe_str(buf):
	return buf[0] + buf[1] + buf[2] if isinstance(buf, str) else chr(buf[0]) + chr(buf[1]) + chr(buf[2])

def from_bytes (data, big_endian = False):
	if isinstance(data, str):
		data = bytearray(data)
	if big_endian:
		data = reversed(data)
	num = 0
	for offset, byte in enumerate(data):
		num += byte << (offset * 8)
	return num

def mirror_paths(sort_dir):
	try:
		os.makedirs(sort_dir)
	except OSError as e:
		if e.errno != errno.EEXIST:
			raise

def walk_dirs(rom_headers, start_path):
	for root, dirs, files in os.walk(start_path):
		unknown_sort_dir = root.replace(start_path, os.path.join('..', 'nes_unknown'), 1)

		if SORT_UNKNOWN and not TRIAL_RUN:
			mirror_paths(unknown_sort_dir)

		for file in files:
			fullname = os.path.join(root, file)
			full_sort_name = os.path.join(unknown_sort_dir, file)
			if file.lower().rfind('.nes') > 0:
				sha = hashlib.sha1()
				header = '0'
				unif = 0
				unh = 0
				prgrom = bytearray()
				chrrom = bytearray()
				buf = 0

				with open(fullname, 'rb') as romfile:
					buf = romfile.read(16)
					header_id = version_safe_str(buf)

					if header_id == 'NES':
						header = buf
					elif header_id == "UNI":
						# F**K UNIF ROMS.
						unif = 1

						buf = romfile.read(16)
						buf = romfile.read(4)
						command = version_safe_str(buf)
						while len(buf) > 0:
							buf = romfile.read(4)
							readlength = 0
							if isinstance(buf[0], str):
								readlength = from_bytes(buf)
							else:
								readlength = int.from_bytes(buf, byteorder='little')
							buf = romfile.read(readlength)
							if command == 'PRG':
								prgrom.extend(buf)
								print(command + ' size ' + str(readlength))
								sha.update(buf)
							elif command == 'CHR':
								chrrom.extend(buf)
								print(command + ' size ' + str(readlength))
								sha.update(buf)
							buf = romfile.read(4)
							if (len(buf) > 0):
								command = version_safe_str(buf)

						print('UNIF file detected, attempting to convert: ' + file)
					else:
						print('Attempting to evaluate unheadered ROM: ' + file)
						unh = 1
						prgrom.extend(buf)
						sha.update(buf)

					while len(buf) > 0:
						buf = romfile.read(65536)
						prgrom.extend(buf)
						if len(buf) > 0:
							sha.update(buf)

				shastr = sha.hexdigest().upper()

				try:
					hstring = rom_headers[shastr]

					if header != hstring:
						print('Updating header for SHA1:' + shastr + ' File: ' + file)
						if (header != '0'):
							print(" ".join(["{:02x}".format(ord(x) if isinstance(x, str) else x) for x in header]) + ' (old)')
						print(" ".join(["{:02x}".format(ord(x) if isinstance(x, str) else x) for x in bytes(hstring)]) + ' (new)\n')
						if not TRIAL_RUN:
							if unif:
								with open(fullname, 'wb') as fixedfile:
									fixedfile.write(hstring)
									fixedfile.write(prgrom)
									fixedfile.write(chrrom)
							else:
								with open(fullname, 'wb') as fixedfile:
									fixedfile.write(hstring)
									fixedfile.write(prgrom)
				except:
					print('ROM not found in database. SHA1: ' + shastr + ' File: ' + file + '\n')
					if MARK_UNHEADERED and not TRIAL_RUN:
						if unif or unh:
							if (fullname[len(fullname) - 4:].lower() != '.unh'):
								os.rename(fullname, fullname + '.unh')
								fullname = fullname + '.unh'
								full_sort_name = full_sort_name + '.unh'

							if unif:
								with open(fullname, 'wb') as fixedfile:
									fixedfile.write(prgrom)
									fixedfile.write(chrrom)

					if SORT_UNKNOWN and not TRIAL_RUN:
						os.rename(fullname, full_sort_name)

			elif file.lower().rfind('.fds') > 0:
				diskdata = bytearray()
				buf = 0
				with open(fullname, 'rb') as romfile:
					buf = romfile.read(16)
					header_id = version_safe_str(buf)
					if header_id != 'FDS' and header_id != 'NES':
						continue
					while len(buf) > 0:
						buf = romfile.read(65536)
						diskdata.extend(buf)
				if not TRIAL_RUN:
					with open(fullname, 'wb') as fixedfile:
						print("Trimming FDS header from " + file + '\n')
						fixedfile.write(diskdata)


print('Reading XML, please wait...')
rom_headers = populate_dict(NES_20) #populate with argument 0 for iNES 1.0 headers
print('Evaluating files...')
walk_dirs(rom_headers, START_PATH)
