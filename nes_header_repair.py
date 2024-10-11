#!/usr/bin/env python3

# Header fixing script by Kitrinx

# Uses NES 2.0 XML database by NewRisingSun
# https://forums.nesdev.com/viewtopic.php?f=3&t=19940&p=248796

# For NES 2.0 header reference see:
# https://wiki.nesdev.com/w/index.php/NES_2.0

# Starting path for directory navigation. Set to /media/fat/games/NES for most MiSTer setups
START_PATH = '.'

# Use NES 2.0 headers. Set to 0 for NES 1.0 header. As not all roms can be properly represented
# with iNES 1.0 headers, it is suggested to stay with 2.0.
NES_20 = 1

# Set to 1 to prevent altering any files
TRIAL_RUN = 0

# Set to 1 to enable moving all unrecognised roms to ../nes_unknown
SORT_UNKNOWN = 1

# Converts unrecognised UNIF roms to unheadered, and adds .unh to all unheadered roms
MARK_UNHEADERED = 1

# Trims any extra junk bytes that may be at the end of files from bad dumps, etc
TRIM_UNKNOWN_DATA = 1

# Level of verbosity for output. 0 is none, 1 is errors, 2 is important info, 3 is normal output, 4 is verbose
VERBOSITY = 4


##### BELOW HERE IS CODE #####


import xml.etree.ElementTree as ET
import hashlib
import os
import errno
from math import log
from math import pow

def print_log(message, level):
	if (level <= VERBOSITY):
		print(message)

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
		romnibble = (int((romsize / divis)) & 0xF00) >> 8

	return romnibble

def find_power_of_two(base10):
	return (int(log(base10 / 64, 2) if base10 > 0 else 0) & 0xF)

def make_header(prgrom, prgram, prgnvram, chrrom, chrram, chrnvram, miscrom, consoleType,
	consoleRegion, expansion, vsHardware, vsPpu, pcbMirroring, pcbMapper, pcbSubMapper, pcbBattery,
	trainer, nes2):

	#default to 'H' for anything invalid
	mirrornibble = 0

	if pcbMapper == 30:
		if pcbMirroring == 'V':
			mirrornibble = 0x1
		elif pcbMirroring == '1':
			mirrornibble = 0x8
		elif pcbMirroring == '4':
			mirrornibble = 0x9
	elif pcbMapper == 218:
		if pcbMirroring == 'V':
			mirrornibble = 0x1
		elif pcbMirroring == '0':
			mirrornibble = 0x8
		elif pcbMirroring == '1':
			mirrornibble = 0x9
	else:
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
	header[6] = ((pcbBattery << 1) | mirrornibble | (0x4 if trainer > 0 else 0) | ((pcbMapper & 0xF) << 4))
	header[7] = ((0x8 if nes2 else 0) | (3 if consoleType >= 3 else consoleType) | (pcbMapper & 0xF0))
	if nes2:
		header[8] = (((pcbMapper & 0xF00) >> 8) | ((pcbSubMapper & 0xF) << 4))
		header[9] = (make_rom_nibble(prgrom, 16384) | (make_rom_nibble(chrrom, 8192) << 4))
		header[10] = find_power_of_two(prgram) | ((find_power_of_two(prgnvram)) << 4)
		header[11] = find_power_of_two(chrram) | ((find_power_of_two(chrnvram)) << 4)
		header[12] = (consoleRegion & 0x03)
		header[13] = (((vsHardware & 0x0F) << 4) | (vsPpu & 0x0F)) if (header[7] & 0x3) == 0x1 else (
			(consoleType & 0xF) if (header[7] & 0x3) == 0x3 else 0)
		header[14] = (miscrom & 0x3)
		header[15] = (expansion & 0x3F)

	return header

def populate_dict(nes2):
	xml_filename = os.path.dirname(__file__) + "nes20db.xml"
	try:
		tree = ET.parse(xml_filename)
	except:
		print_log("nes20db.xml is missing. Please place it in the same folder as this script.", 1)
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
		trainer = 0

		try:
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
				elif pet.tag == 'trainer':
					trainer = int(pet.get('size'))
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
		except Exception as e:
			print_log(e, 1)
			continue

		headers[sha1.upper()] = make_header(prgrom, prgram, prgnvram, chrrom, chrram, chrnvram,
			miscrom, consoleType, consoleRegion, expansion, vsHardware, vsPpu, pcbMirroring,
			pcbMapper, pcbSubMapper, pcbBattery, trainer, nes2)

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
	if not TRIAL_RUN:
		try:
			os.makedirs(sort_dir)
		except OSError as e:
			if e.errno != errno.EEXIST:
				print_log(e, 1)
				raise

def rename_file(original, new):
	if not TRIAL_RUN:
		try:
			os.rename(original, new)
		except Exception as e:
			print_log(e, 1)

def write_new_file(header, romdata, file, write_size = 0):
	if not TRIAL_RUN:
		if write_size == 0 or TRIM_UNKNOWN_DATA == 0:
			write_size = len(romdata)
		else:
			print_log('Trimming unknown data for ' + file, 3)

		try:
			with open(file, 'wb') as fixedfile:
				if len(header) > 0:
					fixedfile.write(header)
				if len(romdata) > 0:
					fixedfile.write(romdata[0:write_size])

		except Exception as e:
			print_log(e, 1)

def calc_rom_size(header):
	size = 512 if (header[6] & 0x4) else 0

	if (header[7] & 0xc) == 0x8:
		if (header[9] & 0x0F) == 0x0F:
			size += pow(2, ((header[4] & 0xFC) >> 2)) * (((header[4] & 0x3) * 2) + 1)
		else:
			size += (16384 * (((header[9] & 0xf) << 8) | header[4]))

		if (header[9] & 0xF0) == 0xF0:
			size += pow(2, ((header[5] & 0xFC) >> 2)) * (((header[5] & 0x3) * 2) + 1)
		else:
			size += (8192 * (((header[9] & 0xf0) << 4) | header[5]))
	else:
		size += 8192 * header[5]
		size += 16384 * header[4]

	return size

def calc_rom_mapper(header):
	calc_mapper = (header[7] & 0xf0) | ((header[6] & 0xF0) >> 4)
	if (header[7] & 0xc) == 0x8:
		calc_mapper = calc_mapper | ((header[8] & 0x0F) << 8)

	return calc_mapper

def parse_rom_data(fullname, file):
	prgrom = bytearray()
	chrrom = bytearray()
	buf = 0
	header = '0'
	unif = 0
	unheadered = 0

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
				if buf[0] ==0x00 and buf[1] ==0x44 and buf[2] ==0x49 and buf[3] ==0x4E:
					print('Bad UNIF: DINF chunk off by one')
					romfile.seek(-3, 1)
					buf = romfile.read(4)
					command = version_safe_str(buf)

				buf = romfile.read(4)					
				readlength = 0
				if isinstance(buf[0], str):
					readlength = from_bytes(buf)
				else:
					readlength = int.from_bytes(buf, byteorder='little')				
					
				if command == 'DIN' and readlength == 0:
					print('Bad UNIF: DINF chunk with specified length of 0')
					readlength =204
					
				buf = romfile.read(readlength)
				if command == 'PRG':
					prgrom.extend(buf)
					print_log(command + ' size ' + str(readlength), 4)
				elif command == 'CHR':
					chrrom.extend(buf)
					print_log(command + ' size ' + str(readlength), 4)
				buf = romfile.read(4)
				if (len(buf) > 0):
					command = version_safe_str(buf)

			print_log('UNIF file detected, attempting to convert: ' + file, 2)
		else:
			print_log('Attempting to evaluate unheadered ROM: ' + file, 2)
			unheadered = 1
			prgrom.extend(buf)

		while len(buf) > 0:
			buf = romfile.read(65536)
			prgrom.extend(buf)

	return prgrom + chrrom, header, unif, unheadered

def process_rom(rom_headers, root, unknown_sort_dir, file):
	fullname = os.path.join(root, file)
	full_sort_name = os.path.join(unknown_sort_dir, file)
	sha = hashlib.sha1()


	romdata, header, unif, unheadered = parse_rom_data(fullname, file)

	sha.update(romdata)
	shastr = sha.hexdigest().upper()

	assumed_size = 0

	header_bytes = bytearray(0)

	try:
		header_bytes = bytearray(header)
		if len(header_bytes) == 16:
			assumed_size = calc_rom_size(header_bytes)
	except:
		pass

	write_size = 0

	if len(romdata) != assumed_size and assumed_size > 0:
		print_log('Evaluating unexpected data (' + str(len(romdata)) + ' vs ' + str(assumed_size) + ') for ' + file, 4)
		limited_sha = hashlib.sha1()
		limited_sha.update(romdata[0:assumed_size])
		limited_shastr = limited_sha.hexdigest().upper()
		try:
			found = rom_headers[shastr]
			print_log('Using data size for evaluation.', 4)
		except:
			shastr = limited_shastr
			print_log('Using reported size for evaluation.', 4)
			write_size = assumed_size

	try:
		hstring = rom_headers[shastr]

		if header != hstring:
			print_log('Updating header for SHA1:' + shastr + ' File: ' + file, 3)
			if (len(header_bytes) == 16):
				newmapper = calc_rom_mapper(bytearray(hstring))
				oldmapper = calc_rom_mapper(header_bytes)
				if newmapper != oldmapper:
					print_log('Updating incorrect mapper from ' + str(oldmapper) + ' to ' + str(newmapper) + '.', 3)

				print_log(" ".join(["{:02x}".format(ord(x) if isinstance(x, str) else x) for x in header]) + ' (old)', 4)
			print_log(" ".join(["{:02x}".format(ord(x) if isinstance(x, str) else x) for x in bytes(hstring)]) + ' (new)\n', 4)
			write_new_file(hstring, romdata, fullname, write_size)

	except:
		print_log('ROM not found in database. SHA1: ' + shastr + ' File: ' + file, 3)
		print_log('', 4)
		if MARK_UNHEADERED and not TRIAL_RUN:
			if unif:
				write_new_file('', romdata, fullname)
				unheadered = 1

			if unheadered:
				if (fullname[len(fullname) - 4:].lower() != '.unh'):
					rename_file(fullname, fullname + '.unh')
					fullname = fullname + '.unh'
					full_sort_name = full_sort_name + '.unh'

		if SORT_UNKNOWN and not TRIAL_RUN:
			rename_file(fullname, full_sort_name)

def process_fds(root, file):
	fullname = os.path.join(root, file)
	diskdata = bytearray()
	buf = 0
	with open(fullname, 'rb') as romfile:
		buf = romfile.read(16)
		header_id = version_safe_str(buf)
		if header_id != 'FDS' and header_id != 'NES':
			return
		while len(buf) > 0:
			buf = romfile.read(65536)
			diskdata.extend(buf)

	write_new_file('', diskdata, fullname)

def walk_dirs(rom_headers, start_path):
	for root, dirs, files in os.walk(start_path):
		unknown_sort_dir = root.replace(start_path, os.path.join('..', 'nes_unknown'), 1)

		if SORT_UNKNOWN and not TRIAL_RUN:
			mirror_paths(unknown_sort_dir)

		for file in files:

			if file.lower().rfind('.nes') > 0 or file.lower().rfind('.unif') > 0 or file.lower().rfind('.unf') > 0:
				process_rom(rom_headers, root, unknown_sort_dir, file)

			elif file.lower().rfind('.fds') > 0:
				process_fds(root, file)

### Main ###

print_log('Reading XML, please wait...', 2)
rom_headers = populate_dict(NES_20) #populate with argument 0 for iNES 1.0 headers
print_log('Evaluating files...', 2)
walk_dirs(rom_headers, START_PATH)
print_log('\n\nProcessing complete.' +
	(' This has been a trial run. See the top of the script to change options.' if TRIAL_RUN else ''), 2)
