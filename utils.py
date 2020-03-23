#!/usr/bin/env python3


def read_word(script, pos):
	return script[pos * 2] + (script[pos * 2 + 1] << 8)


def write_word(data, pos, word):
	data[pos * 2] = word & 0xFF
	data[pos * 2 + 1] = (word >> 8) & 0xFF


def write_bytes(data, offset, bytes_to_write):
	for i in range(len(bytes_to_write)):
		data[offset + i] = bytes_to_write[i]


def error(text):
	print("[!] ERROR: " + text)


def log(text):
	print("[*] " + text)
