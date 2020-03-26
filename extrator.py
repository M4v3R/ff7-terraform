import re
import struct

from os import makedirs
from os.path import isdir, isfile

from PyFF7.lgp import LGP, pack_lgp
from PyFF7.text import decode_field_text

from constants import *
from utils import error, log, read_word

VALUE_PREFIX = ""


class Extractor:
    def __init__(self, input_file, output_directory, verbose):
        super(Extractor, self).__init__()
        self.lgp_file = input_file
        self.directory = output_directory
        self.messages_file = None
        self.messages = []
        self.scripts = []
        self.verbose = False

    def dump_functions(self, functions, directory):
        directory = self.directory + '/' + directory
        log("Writing functions to directory: " + directory)

        if not isdir(directory):
            makedirs(directory)

        for function in functions:
            name = function[0]
            opcodes = function[1]

            if opcodes is None:
                with open(directory + '/' + name + '.s', 'w') as outfile:
                    outfile.write('# Dummy function, duplicate of function #' + name[4:7])
                    outfile.close()
                continue

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
                            mess = self.messages[int(opcode[1][0])].replace("\n", " ")
                            if len(mess) > 50:
                                mess = mess[:50] + ' ...'
                            text += ' # ' + mess

                    if self.verbose and opcode[4] is not None:
                        hex_text = ''
                        for h in opcode[4]:
                            hex_text += ' %s' % struct.pack('<H', h).hex()

                        outfile.write('%s# %04x:%s\n' % (indent, opcode[2], hex_text))

                    outfile.write(text + "\n")

                outfile.close()

    def dump_messages(self, filename):
        filename = self.directory + '/' + filename
        log("Writing messages to file: " + filename)
        with open(filename, 'w') as outfile:
            i = 0
            for text in self.messages:
                outfile.write("---[ MESSAGE ID %d:\n" % i)
                outfile.write(text + "\n\n")
                i += 1

            outfile.close()

    def read_functions(self, index, code):
        functions = []
        offsets = {}
        file_id = 0
        for entry in index:
            pos = entry[1]

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

            opcode = (0,)
            opcodes = []
            indent = 0
            jumps = []
            labels = []

            if pos not in offsets:
                offsets[pos] = file_id
            else:
                functions.append((name[:3] + ('-%03d' % offsets[pos]) + name[3:], None))
                file_id += 1
                continue

            file_id += 1

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
                            if (VALUE_PREFIX == '' or last_param[0] == VALUE_PREFIX) and last_param[
                                                                                         len(VALUE_PREFIX):] in MODELS:
                                params.append(f"{VALUE_PREFIX}${MODELS[last_param[len(VALUE_PREFIX):]]}")
                            else:
                                params.append(last_param)

                        # If current opcode is 'IsEqual', and its param is a SpecialByte($LastFieldID)
                        # adjust the second param with a constant for better readibility
                        if opcode[0] == OPCODES[0x70][0] and op[1][0] == '$' + SPECIAL_VARS['6'] and \
                                op[0] == OPCODES[0x11b][0]:
                            last_param = params.pop()
                            if (VALUE_PREFIX == '' or last_param[0] == VALUE_PREFIX) and last_param[len(
                                    VALUE_PREFIX):] in FIELD_IDS:
                                params.append(f"{VALUE_PREFIX}${FIELD_IDS[last_param[len(VALUE_PREFIX):]]}")
                            else:
                                params.append(last_param)

                        # Replace constant values with Model constants wherever possible
                        if word in MODEL_OPCODES and op[0] == OPCODES[0x110][0] and str(op[1][0]) in MODELS:
                            params.append(f"{VALUE_PREFIX}${MODELS[str(op[1][0])]}")

                        # Replace constant values with Field IDs constants wherever possible
                        elif op[0] == OPCODES[0x110][0] and word == 0x318 and i == 1 and str(op[1][0]) in FIELD_IDS:
                            params.append(f"{VALUE_PREFIX}${FIELD_IDS[str(op[1][0])]}")

                        elif op[0] == OPCODES[0x015][0]:  # Neg
                            params.append(f"-{op[1][0]}")

                        elif op[0] == OPCODES[0x030][0]:  # Multiply
                            params.append(f"{op[1][0]} * {op[1][1]}")

                        elif op[0] == OPCODES[0x040][0]:  # Add
                            params.append(f"{op[1][0]} + {op[1][1]}")

                        elif op[0] == OPCODES[0x041][0]:  # Sub
                            params.append(f"{op[1][0]} - {op[1][1]}")

                        elif op[0] == OPCODES[0x050][0]:  # ShiftLeft
                            params.append(f"{op[1][0]} << {op[1][1]}")

                        elif op[0] == OPCODES[0x051][0]:  # ShiftRight
                            params.append(f"{op[1][0]} >> {op[1][1]}")

                        elif op[0] == OPCODES[0x060][0]:  # IsLessThan
                            params.append(f"{op[1][0]} < {op[1][1]}")

                        elif op[0] == OPCODES[0x061][0]:  # IsGreaterThan
                            params.append(f"{op[1][0]} > {op[1][1]}")

                        elif op[0] == OPCODES[0x062][0]:  # IsLessOrEqaulThan
                            params.append(f"{op[1][0]} <= {op[1][1]}")

                        elif op[0] == OPCODES[0x063][0]:  # IsGreaterOrEqualThan
                            params.append(f"{op[1][0]} >= {op[1][1]}")

                        elif op[0] == OPCODES[0x070][0]:  # IsEqual
                            params.append(f"{op[1][0]} == {op[1][1]}")

                        elif op[0] == OPCODES[0x80][0]:  # Bit And
                            params.append(f"{op[1][0]} & {op[1][1]}")

                        elif op[0] == OPCODES[0xa0][0]:  # Bit Or
                            params.append(f"{op[1][0]} | {op[1][1]}")

                        elif op[0] == OPCODES[0xb0][0]:  # AND
                            params.append(f"{op[1][0]} AND {op[1][1]}")

                        elif op[0] == OPCODES[0xc0][0]:  # OR
                            params.append(f"{op[1][0]} OR {op[1][1]}")

                        elif op[0] == OPCODES[0x110][0]:  # Value
                            params.append(f"{VALUE_PREFIX}{op[1][0]}")

                        else:  # other opcodes
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
                            byte = word + 0xBA4
                            if byte in SAVEMAP_VARS:
                                params.append("$" + SAVEMAP_VARS[byte])
                            else:
                                params.append("0x" + ("%04x" % byte).upper())

                        elif opcode[0] in [OPCODES[0x117][0], OPCODES[0x11b][0], OPCODES[0x11f][0]] \
                                and str(word) in SPECIAL_VARS:  # Special*
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

    def read_code(self, script):
        code = []
        i = 0x200
        while i * 2 < len(script):
            word = read_word(script, i)
            code.append(word)
            i += 1

        return code

    def read_index(self, script):
        index = []
        pos = 2  # skip first dummy entry
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
            elif entry == 0xFFFF:  # dummy entries
                continue
            else:
                error("Invalid function type: %d" % function_type)
                continue

        # sorted_index = sorted(index, key=lambda item: item[1])
        # return sorted_index
        return index

    def read_messages(self, data):
        num_entries = read_word(data, 0)

        for i in range(0, num_entries):
            offset = read_word(data, 1 + i)
            self.messages.append(decode_field_text(data[offset:]))

    def extract_scripts(self, file):
        filename = file[0]
        script = file[1]

        index = self.read_index(script)
        code = self.read_code(script)
        functions = self.read_functions(index, code)

        self.dump_functions(functions, filename)

    def extract_messages(self):
        data = self.messages_file[1]
        self.read_messages(data)
        self.dump_messages('messages.txt')

    def extract(self):
        lgp = LGP(self.lgp_file)

        if not isdir(self.directory):
            makedirs(self.directory)

        files = lgp.load_files()
        for i, e in enumerate(files):
            if re.match("wm\d.ev", e[0]):
                self.scripts.append(e)
            if e[0] == 'mes' or e[0] == '/mes':
                self.messages_file = e

        if not self.messages_file:
            error("Messages file 'mes' not found inside %s!" % self.lgp_file)
            exit(1)

        self.extract_messages()

        for i in range(0, 3):
            self.extract_scripts(self.scripts[i])

