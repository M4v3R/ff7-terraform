#!/usr/bin/env python3

from os import walk
from os.path import isfile, isdir

from PyFF7.text import encode_text
from compiler import Compiler
from utils import log, error, write_word, write_bytes


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
                with open(directory + '/' + filename) as file:
                    compiler = Compiler(file)
                    functions.append(compiler.compile())

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
            write_bytes(data, offset, self.messages[i])
            offset += len(self.messages[i])

        with open(filename, 'wb') as file:
            file.write(data)

    def write_files(self, directory):
        self.write_messages(directory)
