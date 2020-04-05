#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
Terraform - World Map script editor for Final Fantasy VII
by Maciej "mav" Trebacz
'''

from sys import argv, exit
from os import makedirs
from os.path import isdir, isfile

from extrator import Extractor
from parse import Parser
from utils import error, log

from PyFF7.lgp import LGP, pack_lgp
from constants import *

VERSION = "0.9.2"

USAGE = "USAGE:\n\
* Extract scripts: %s extract <world lgp file>\n\
* Compile scripts: %s compile <input directory> <output lgp file>" % (argv[0], argv[0])


def header():
    print("---------------------------------------------")
    print("Terraform v%s - FF7 Worldmap script editor" % VERSION)
    print("---------------------------------------------\n")


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


def extract_world(lgp_file, verbose):
    if not isfile(lgp_file):
        error("Input LGP file not found!")
        exit(1)

    extractor = Extractor(lgp_file, OUTPUT_DIR, verbose)
    extractor.extract()


if __name__ == "__main__":
    header()

    if len(argv) < 2:
        print(USAGE); exit(1)

    if argv[1] == 'extract':
        if len(argv) < 3:
            print(USAGE); exit(1)

        verbose = False
        if len(argv) > 3 and argv[3][:2] == '-v':
            verbose = True

        extract_world(argv[2], verbose)

    elif argv[1] == 'compile':
        if len(argv) < 4:
            print(USAGE); exit(1)
        compile_world(argv[2], argv[3])


