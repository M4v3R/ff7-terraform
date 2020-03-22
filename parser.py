#!/usr/bin/env python3

from sys import exit
from os import walk
from os.path import isfile, isdir

from PyFF7.text import encode_text
from compiler import Compiler
from utils import log, error, write_word, write_bytes
from constants import *


class Parser(object):
    directory = None
    messages = []
    scripts = []
    message_line = 0

    def __init__(self, input_directory):
        super(Parser, self).__init__()
        self.directory = input_directory

    def store_message(self, message):
        encoded = ''
        id = len(self.messages)

        try:
            encoded = encode_text(message.strip())
        except ValueError as e:
            error(f"In message ID {id}:\n" + str(e))
            exit(1)

        self.messages.append(encoded)

    def load_messages(self):
        log("Reading messages...")

        filename = self.directory + '/messages.txt'
        if not isfile(filename):
            error("messages.txt not found in input directory.")
            exit(1)

        num = 0
        message = ''

        with open(filename, 'r') as file:
            while True:
                line = file.readline()
                if line[:8] == '---[ MES':
                    if num > 0:
                        self.store_message(message)
                        message = ''
                    num += 1
                    continue

                if line == '':
                    self.store_message(message)
                    break

                message += line
                num += 1

    def load_scripts(self):
        log("Reading scripts...")
        for script in ['wm0.ev', 'wm2.ev', 'wm3.ev']:
            directory = self.directory + '/' + script
            functions = []
            if not isdir(directory):
                error("Script directory not found: " + directory)
                exit(1)

            files = []
            for prefix in ['system', 'model', 'mesh']:
                for r, d, f in walk(directory):
                    for file in f:
                        if prefix not in file:
                            continue

                        files.append(file)

                files.sort()

            for filename in files:
                offset = 1
                with open(directory + '/' + filename) as file:
                    compiler = Compiler(file, offset)
                    code = compiler.compile()
                    offset += int(len(code) / 2)
                    functions.append((filename, code))

            self.scripts.append((script, functions))

    def compile(self):
        self.load_messages()
        self.load_scripts()

    def write_messages(self, directory):
        filename = directory + '/mes'
        data = bytearray(0x1000)
        num_entries = len(self.messages)

        write_word(data, 0, num_entries)

        # Write offsets
        offset = 2 + num_entries * 2
        for i in range(0, num_entries):
            write_word(data, i + 1, offset)
            write_bytes(data, int(offset / 2), self.messages[i])
            offset += len(self.messages[i])

        with open(filename, 'wb') as file:
            file.write(data)

    def write_scripts(self, directory):
        for script, functions in self.scripts:
            filename = directory + '/' + script
            data = bytearray(0x7000)
            index_pos = 2
            offset = 1

            # First dummy function
            write_word(data, 0x200, 0x203)

            for name, code in functions:
                function = name[:name.index(".")].split("_")
                if function[1] == 'system':
                    ident = int(function[2])
                elif function[1] == 'model':
                    ident = int(function[3]) | int(function[2]) << 8 | 0x4000
                else:
                    x = int(function[2])
                    z = int(function[3])
                    type = int(function[4])
                    coords = x * 36 + z
                    ident = type | coords << 4 | 0x8000

                write_word(data, index_pos, ident)
                write_word(data, index_pos + 1, offset)

                write_bytes(data, 0x200 + offset, code)
                index_pos += 2
                offset += int(len(code) / 2)

            while index_pos < 0x200:
                write_word(data, index_pos, 0xFFFF)
                write_word(data, index_pos + 1, 0)
                index_pos += 2

            with open(filename, 'wb') as file:
                file.write(data)

    def write_files(self, directory):
        self.write_messages(directory)
        self.write_scripts(directory)
