#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
Terraform - World Map script editor for Final Fantasy VII
by Maciej "mav" Trebacz
'''

import re
from sys import argv
from os import makedirs
from os.path import isdir

from PyFF7.lgp import LGP
from PyFF7.text import decode_field_text
from constants import *

OUTPUT_DIR = "output"
USAGE = "USAGE: %s <world_us.lgp>" % argv[0]

def read_word(script, pos):
	return script[pos * 2] + (script[pos * 2 + 1] << 8)

def dump_functions(functions, directory):
	directory = OUTPUT_DIR + '/' + directory
	print("Writing functions to directory: " + directory)

	if not isdir(directory):
		makedirs(directory)

	for function in functions:
		name = function[0]
		opcodes = function[1]
		labels = function[2]
		with open(directory + '/' + name + '.s', 'w') as outfile:
			for opcode in opcodes:
				indent = ''
				for i in range(0, opcode[3]):
					indent += '  '

				if opcode[2] in labels:
					idx = labels.index(opcode[2]) + 1
					text = f"{indent}LABEL_{idx}:"
					outfile.write(text + "\n")

				# Skip noisy ResetStack opcodes
				if opcode[0] == OPCODES[0x100][0]:
					continue

				text = f"{indent}{opcode[0]}({', '.join(opcode[1])})"
				outfile.write(text + "\n")

			outfile.close()

def dump_messages(messages, filename):
	filename = OUTPUT_DIR + '/' + filename
	print("Writing messages to file: " + filename)
	with open(filename, 'w') as outfile:
		i = 0
		for text in messages:
			outfile.write("---[ MESSAGE ID %d:\n" % i)
			outfile.write(text + "\n\n")
			i += 1

		outfile.close()

def read_functions(index, code):
	functions = []
	for entry in index:

		# System Functions
		name = f'system_%02d' % entry[2]

		# Model Functions
		if entry[0] == FUNCTION_MODEL:
			name = 'model_%02d_%02d' % (entry[3], entry[2])

		# Mesh Functions
		elif entry[0] == FUNCTION_MESH:
			x = entry[2] / 36
			z = entry[2] % 36
			name = 'mesh_%02d_%02d_%d' % (x, z, entry[3])

		opcode = (0,)
		opcodes = []
		pos = entry[1]
		indent = 0
		jumps = []
		labels = []

		# Read the code until we reach Return opcode
		while opcode[0] != OPCODES[0x203][0]: 
			params = []
			word = code[pos]
			pos += 1

			if not word in OPCODES:
				opcodes.append(("Unknown%04x" % word, [], pos - 1, indent))
				continue

			opcode = OPCODES[word]

			# Stack arguments
			if opcode[1] > 0:
				for i in range(0, opcode[1]):
					op = opcodes.pop()

					# If current opcode is 'IsEqual', and its param is a SpecialByte($PlayerEntityModelId)
					# adjust the second param with a constant for better readibility
					if opcode[0] == OPCODES[0x70][0] and op[1][0] == '$' + SPECIAL_VARS['8'] and \
					  op[0] == OPCODES[0x11b][0]:
						last_param = params.pop()
						if last_param[0] == '&' and last_param[1:] in MODELS:
							params.append(f"&${MODELS[last_param[1:]]}")  
						else:
							params.append(last_param)

					# Replace constant values with Model constants wherever possible
					if word in MODEL_OPCODES and op[0] == OPCODES[0x110][0] and str(op[1][0]) in MODELS:
						params.append(f"&${MODELS[str(op[1][0])]}")  

					elif op[0] == OPCODES[0x030][0]: # Multiply
						params.append(f"{op[1][0]} * {op[1][1]})")

					elif op[0] == OPCODES[0x040][0]: # Add
						params.append(f"{op[1][0]} + {op[1][1]})")

					elif op[0] == OPCODES[0x041][0]: # Sub
						params.append(f"{op[1][0]} - {op[1][1]})")

					elif op[0] == OPCODES[0x050][0]: # ShiftLeft
						params.append(f"{op[1][0]} << {op[1][1]})")

					elif op[0] == OPCODES[0x051][0]: # ShiftRight
						params.append(f"{op[1][0]} >> {op[1][1]})")

					elif op[0] == OPCODES[0x060][0]: # IsLessThan
						params.append(f"{op[1][0]} < {op[1][1]})")

					elif op[0] == OPCODES[0x061][0]: # IsGreaterThan
						params.append(f"{op[1][0]} > {op[1][1]})")

					elif op[0] == OPCODES[0x062][0]: # IsLessOrEqaulThan
						params.append(f"{op[1][0]} <= {op[1][1]})")

					elif op[0] == OPCODES[0x063][0]: # IsGreaterOrEqualThan
						params.append(f"{op[1][0]} >= {op[1][1]})")

					elif op[0] == OPCODES[0x070][0]: # IsEqual
						params.append(f"{op[1][0]} == {op[1][1]})")

					elif op[0] == OPCODES[0xb0][0]: # AND
						params.append(f"{op[1][0]} AND {op[1][1]})")

					elif op[0] == OPCODES[0xc0][0]: # OR
						params.append(f"{op[1][0]} OR {op[1][1]})")

					elif op[0] == OPCODES[0x110][0]: # Value
						params.append(f"&{op[1][0]}")

					else: # other opcodes
						params.append(f"{op[0]}({', '.join(op[1])})")
				params.reverse()

			# Code arguments
			if opcode[2] > 0:
				for i in range(0, opcode[2]):
					if opcode[0] == OPCODES[0x114][0]: # SavemapBit
						bit = code[pos] % 8
						byte = int(code[pos] / 8) + 0xBA4
						if byte in SAVEMAP_VARS:
							params.append("$" + SAVEMAP_VARS[byte])
						else:
							params.append("0x" + ("%04x" % byte).upper())
						params.append(str(bit))

					elif opcode[0] in [OPCODES[0x118][0], OPCODES[0x11c][0]]: # SavemapByte or SavemapWord
						byte = int(code[pos] / 8) + 0xBA4
						if byte in SAVEMAP_VARS:
							params.append("$" + SAVEMAP_VARS[byte])
						else:
							params.append("0x" + ("%04x" % byte).upper())

					elif opcode[0] in [OPCODES[0x117][0], OPCODES[0x11b][0], OPCODES[0x11f][0]] \
						and str(code[pos]) in SPECIAL_VARS: # Special*
						params.append("$" + SPECIAL_VARS[str(code[pos])])

					elif opcode[0] == OPCODES[0x200][0]: # GoTo
						if code[pos] not in labels:
							labels.append(code[pos])
						idx = labels.index(code[pos]) + 1
						params.append(f"LABEL_{str(idx)}")

					elif opcode[0] == OPCODES[0x201][0]: # If
						jumps.append(code[pos])
						pos += 1
						continue

					else:
						params.append(str(code[pos]))

					pos += 1

			opcodes.append((opcode[0], params, pos - 1 - opcode[2], indent))

			# De-indent when a jump was made here
			while pos in jumps:
				indent -= 1
				jumps.pop()

			# Indent everything after If opcode
			if opcode[0] == OPCODES[0x201][0]:
				indent += 1				

		functions.append((name, opcodes, labels))

	return functions

def read_code(script):
	code = []
	i = 0x200
	while i * 2 < len(script):
		word = read_word(script, i)
		code.append(word)
		i += 1

	return code

def read_index(script):
	index = []
	pos = 2 # skip first dummy entry
	while pos < 0x200:
		entry = read_word(script, pos)
		offset = read_word(script, pos + 1)
		pos += 2

		function_type = entry >> 14
		if function_type == FUNCTION_SYSTEM:
			function_id = entry & 0xFF
			index.append((FUNCTION_SYSTEM, offset, function_id))
		elif function_type == FUNCTION_MODEL:
			model_id = (entry >> 8) & 0x3F
			function_id = entry & 0xFF
			index.append((FUNCTION_MODEL, offset, function_id, model_id))
		elif function_type == FUNCTION_MESH:
			mesh_coords = (entry >> 4) & 0x3FF
			walkmesh_type = entry & 0xF
			index.append((FUNCTION_MESH, offset, mesh_coords, walkmesh_type))
		elif entry == 0xFFFF: # dummy entries
			continue
		else:
			print("Error: Invalid function type: %d" % function_type)
			continue

	return index

def read_messages(data):
	num_entries = read_word(data, 0)
	messages = []

	for i in range(0, num_entries):
		offset = read_word(data, 1 + i)
		messages.append(decode_field_text(data[offset:]))

	return messages

def extract_scripts(file):
	filename = file[0]
	script = file[1]

	index = read_index(script)
	code = read_code(script)
	functions = read_functions(index, code)

	dump_functions(functions, filename)

def extract_messages(file):
	filename = file[0]
	data = file[1]
	messages = read_messages(data)

	dump_messages(messages, 'messages.txt')

def extract_world(lgp_file):
	lgp = LGP(lgp_file)
	scripts = []
	messages_file = None

	if not isdir(OUTPUT_DIR):
		makedirs(OUTPUT_DIR)

	for i, e in enumerate(lgp.load_files()):
		if re.match("wm\d.ev", e[0]):
			scripts.append(e)
		if e[0] == 'mes':
			messages_file = e

	for i in range(0, 3):
		extract_scripts(scripts[i])

	extract_messages(messages_file)

if __name__ == "__main__":
    if len(argv) != 2:
        print(USAGE); exit(1)
    extract_world(argv[1])
