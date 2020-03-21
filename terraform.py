#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
Terraform - World Map script editor for Final Fantasy VII
by Maciej "mav" Trebacz
'''

import struct
import re
from sys import argv, exit
from os import makedirs
from os.path import isdir, isfile

from PyFF7.lgp import LGP, pack_lgp
from PyFF7.text import decode_field_text

from constants import *
from parser import Parser
from utils import error, log, read_word

OUTPUT_DIR = "output"
TEMP_DIR = "temp"
VERSION = "1.0"
VALUE_PREFIX = ""
verbose = False
messages = []

USAGE = "USAGE:\n\
* Extract scripts:  %s extract <world lgp file>\n\
* Compile scripts: %s compile <input directory> <output lgp file>" % (argv[0], argv[0])


def header():
    print("-------------------------------------------")
    print("Terraform v%s - FF7 Worldmap script editor" % VERSION)
    print("-------------------------------------------\n")


def dump_functions(functions, directory):
    directory = OUTPUT_DIR + '/' + directory
    log("Writing functions to directory: " + directory)

    if not isdir(directory):
        makedirs(directory)

    for function in functions:
        name = function[0]
        opcodes = function[1]
        labels = function[2]
        entry = function[3]
        with open(directory + '/' + name + '.s', 'w') as outfile:
            # Write headers
            if entry[0] == FUNCTION_SYSTEM:
                outfile.write('# System Function ID %02d\n' % entry[2])

            elif entry[0] == FUNCTION_MODEL:
                modelname = MODELS[str(entry[3])] if str(entry[3]) in MODELS else 'Unknown'
                outfile.write('# Model ID %02d (%s), Function ID %02d\n' % (entry[3], modelname, entry[2]))

            elif entry[0] == FUNCTION_MESH:
                outfile.write('# Mesh Function ID %d, Mesh Type %d\n' % (entry[2], entry[3]))

            offset = entry[1] * 2 + 0x400
            outfile.write('# Start offset: 0x%04x\n\n' % offset)

            for opcode in opcodes:
                indent = ''
                for i in range(0, opcode[3]):
                    indent += '  '

                if opcode[4] is not None and opcode[2] in labels:
                    idx = labels.index(opcode[2]) + 1
                    text = f"{indent}@LABEL_{idx}"
                    outfile.write(text + "\n")

                # Skip noisy ResetStack opcodes
                if opcode[0] == OPCODES[0x100][0]:
                    continue

                if opcode[0] == 'If':
                    text = f"{indent}If {opcode[1][0]} Then"
                elif opcode[0] == 'EndIf':
                    text = f"{indent}EndIf"
                elif opcode[0] == 'Return':
                    text = f"{indent}End"
                elif opcode[0] == 'GoTo':
                    text = f"{indent}GoTo @{opcode[1][0]}"
                else:
                    text = f"{indent}{opcode[0]}({', '.join(opcode[1])})"
                    if opcode[0] == 'SetWindowMessage':
                        mess = messages[int(opcode[1][0])].replace("\n", " ")
                        if len(mess) > 50:
                            mess = mess[:50] + ' ...'
                        text += ' # ' + mess

                if verbose and opcode[4] is not None:
                    hex_text = ''
                    for h in opcode[4]:
                        hex_text += ' %s' % struct.pack('<H', h).hex()

                    outfile.write('%s# %04x:%s\n' % (indent, opcode[2], hex_text))

                outfile.write(text + "\n")

            outfile.close()


def dump_messages(messages, filename):
    filename = OUTPUT_DIR + '/' + filename
    log("Writing messages to file: " + filename)
    with open(filename, 'w') as outfile:
        i = 0
        for text in messages:
            outfile.write("---[ MESSAGE ID %d:\n" % i)
            outfile.write(text + "\n\n")
            i += 1

        outfile.close()


def read_functions(index, code):
    functions = []
    file_id = 0
    for entry in index:

        # System Functions
        name = f'%03d_system_%02d' % (file_id, entry[2])

        # Model Functions
        if entry[0] == FUNCTION_MODEL:
            name = '%03d_model_%02d_%02d' % (file_id, entry[3], entry[2])

        # Mesh Functions
        elif entry[0] == FUNCTION_MESH:
            x = entry[2] / 36
            z = entry[2] % 36
            name = '%03d_mesh_%02d_%02d_%d' % (file_id, x, z, entry[3])

        file_id += 1
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
            words = [word]
            pos += 1

            if 0x204 <= word < 0x300:
                opcode = OPCODES[0x204]
            elif word not in OPCODES:
                opcodes.append(("Unknown%04x" % word, [], pos - 1, indent, words))
                continue
            else:
                opcode = OPCODES[word]

            # Stack arguments
            if opcode[1] > 0:
                for i in range(0, opcode[1]):
                    op = opcodes.pop()
                    words = op[4] + words

                    # If current opcode is 'IsEqual', and its param is a SpecialByte($PlayerEntityModelId)
                    # adjust the second param with a constant for better readibility
                    if opcode[0] == OPCODES[0x70][0] and op[1][0] == '$' + SPECIAL_VARS['8'] and \
                            op[0] == OPCODES[0x11b][0]:
                        last_param = params.pop()
                        if (VALUE_PREFIX == '' or last_param[0] == VALUE_PREFIX) and last_param[len(VALUE_PREFIX):] in MODELS:
                            params.append(f"{VALUE_PREFIX}${MODELS[last_param[len(VALUE_PREFIX):]]}")
                        else:
                            params.append(last_param)

                    # Replace constant values with Model constants wherever possible
                    if word in MODEL_OPCODES and op[0] == OPCODES[0x110][0] and str(op[1][0]) in MODELS:
                        params.append(f"{VALUE_PREFIX}${MODELS[str(op[1][0])]}")

                    elif op[0] == OPCODES[0x015][0]: # Neg
                        params.append(f"-{op[1][0]}")

                    elif op[0] == OPCODES[0x030][0]: # Multiply
                        params.append(f"{op[1][0]} * {op[1][1]}")

                    elif op[0] == OPCODES[0x040][0]: # Add
                        params.append(f"{op[1][0]} + {op[1][1]}")

                    elif op[0] == OPCODES[0x041][0]: # Sub
                        params.append(f"{op[1][0]} - {op[1][1]}")

                    elif op[0] == OPCODES[0x050][0]: # ShiftLeft
                        params.append(f"{op[1][0]} << {op[1][1]}")

                    elif op[0] == OPCODES[0x051][0]: # ShiftRight
                        params.append(f"{op[1][0]} >> {op[1][1]}")

                    elif op[0] == OPCODES[0x060][0]: # IsLessThan
                        params.append(f"{op[1][0]} < {op[1][1]}")

                    elif op[0] == OPCODES[0x061][0]: # IsGreaterThan
                        params.append(f"{op[1][0]} > {op[1][1]}")

                    elif op[0] == OPCODES[0x062][0]: # IsLessOrEqaulThan
                        params.append(f"{op[1][0]} <= {op[1][1]}")

                    elif op[0] == OPCODES[0x063][0]: # IsGreaterOrEqualThan
                        params.append(f"{op[1][0]} >= {op[1][1]}")

                    elif op[0] == OPCODES[0x070][0]: # IsEqual
                        params.append(f"{op[1][0]} == {op[1][1]}")

                    elif op[0] == OPCODES[0x80][0]: # Bit And
                        params.append(f"{op[1][0]} & {op[1][1]}")

                    elif op[0] == OPCODES[0xa0][0]: # Bit Or
                        params.append(f"{op[1][0]} | {op[1][1]}")

                    elif op[0] == OPCODES[0xb0][0]: # AND
                        params.append(f"{op[1][0]} AND {op[1][1]}")

                    elif op[0] == OPCODES[0xc0][0]: # OR
                        params.append(f"{op[1][0]} OR {op[1][1]}")

                    elif op[0] == OPCODES[0x110][0]: # Value
                        params.append(f"{VALUE_PREFIX}{op[1][0]}")

                    else: # other opcodes
                        params.append(f"{op[0]}({', '.join(op[1])})")
                params.reverse()

            # Code arguments
            if opcode[2] > 0:
                for i in range(0, opcode[2]):
                    word = code[pos]
                    words.append(word)

                    if opcode[0] == OPCODES[0x114][0]:  # SavemapBit
                        bit = word % 8
                        byte = int(word / 8) + 0xBA4
                        if byte in SAVEMAP_VARS:
                            params.append("$" + SAVEMAP_VARS[byte])
                        else:
                            params.append("0x" + ("%04x" % byte).upper())
                        params.append(str(bit))

                    elif opcode[0] in [OPCODES[0x118][0], OPCODES[0x11c][0]]:  # SavemapByte or SavemapWord
                        byte = int(word / 8) + 0xBA4
                        if byte in SAVEMAP_VARS:
                            params.append("$" + SAVEMAP_VARS[byte])
                        else:
                            params.append("0x" + ("%04x" % byte).upper())

                    elif opcode[0] in [OPCODES[0x117][0], OPCODES[0x11b][0], OPCODES[0x11f][0]] \
                            and str(word) in SPECIAL_VARS: # Special*
                        params.append("$" + SPECIAL_VARS[str(word)])

                    elif opcode[0] == OPCODES[0x200][0]:  # GoTo
                        if word not in labels:
                            labels.append(word)
                        idx = labels.index(word) + 1
                        params.append(f"LABEL_{str(idx)}")

                    elif opcode[0] == OPCODES[0x201][0]:  # If
                        jumps.append(word)
                        pos += 1
                        continue

                    else:
                        params.append(str(word))

                    pos += 1

            if opcode == OPCODES[0x204]:
                params.append(str(word - 0x204))
            opcodes.append((opcode[0], params, pos - 1 - opcode[2], indent, words))

            # De-indent when a jump was made here
            while pos in jumps:
                indent -= 1
                jumps.pop()

                # Add a dummy EndIf opcode as a hint for the compiler
                opcodes.append(('EndIf', [], pos - 1 - opcode[2], indent, None))

            # Indent everything after If opcode
            if opcode[0] == OPCODES[0x201][0]:
                indent += 1

        functions.append((name, opcodes, labels, entry))

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
            error("Invalid function type: %d" % function_type)
            continue

    return index


def read_messages(data):
    num_entries = read_word(data, 0)

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


def compile_world(input_directory, output_file):
    if not isdir(input_directory):
        error("Input directory not found!")
        exit(1)

    if not isfile(output_file):
        error("Output LGP file not found!")
        exit(1)

    if not isdir(TEMP_DIR):
        makedirs(TEMP_DIR)

    log("Compiling world scripts...")
    parser = Parser(input_directory)
    parser.compile()

    log("Extracting LGP archive...")
    lgp = LGP(output_file)
    files = []
    for i, e in enumerate(lgp.load_files()):
        filename = "%s/%s" % (TEMP_DIR, e[0])
        f = open(filename, 'wb');
        f.write(e[1])
        f.close()
        files.append((e[0], filename))

    log("Writing new scripts...")
    parser.write_files(TEMP_DIR)

    log("Packing a new LGP archive...")
    pack_lgp(files, output_file)


def extract_world(lgp_file):
    if not isfile(lgp_file):
        error("Input LGP file not found!")
        exit(1)

    lgp = LGP(lgp_file)
    scripts = []
    messages_file = None

    if not isdir(OUTPUT_DIR):
        makedirs(OUTPUT_DIR)

    files = lgp.load_files()
    for i, e in enumerate(files):
        if re.match("wm\d.ev", e[0]):
            scripts.append(e)
        if e[0] == 'mes' or e[0] == '/mes':
            messages_file = e

    if not messages_file:
        error("Messages file 'mes' not found inside %s!" % lgp_file)
        exit(1)

    extract_messages(messages_file)

    for i in range(0, 3):
        extract_scripts(scripts[i])


if __name__ == "__main__":
    header()

    if len(argv) < 2:
        print(USAGE); exit(1)

    if argv[1] == 'extract':
        if len(argv) < 3:
            print(USAGE); exit(1)

        if len(argv) > 3 and argv[3][:2] == '-v':
            verbose = True

        extract_world(argv[2])

    elif argv[1] == 'compile':
        if len(argv) < 4:
            print(USAGE); exit(1)
        compile_world(argv[2], argv[3])


