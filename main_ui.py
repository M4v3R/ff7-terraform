#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Terraform 3000 - World Map dump/compile GUI
by TurBoss
"""

from terraform import compile_world, extract_world
from tkinter import Tk, Label, Entry, Button, filedialog, StringVar


def open_wm_clicked():
    wm_path.set(filedialog.askopenfilename())


def open_files_clicked():
    files_path.set(filedialog.askdirectory())


def comnpile_clicked():
    compile_world(files_path.get(), output_file="test")


def dump_clicked():
    extract_world(wm_path.get())


window = Tk()

wm_path = StringVar()
files_path = StringVar()

window.title("Terraform 3000")

lbl = Label(window, text="World Map")
lbl.grid(column=0, row=0)

open_wm_btn = Button(window, text="open", width=8, command=open_wm_clicked)
open_wm_btn.grid(column=0, row=1)

wm_path_entry = Entry(window, width=40, textvariable=wm_path)
wm_path_entry.grid(column=1, row=1)

dump_btn = Button(window, text="Dump", width=8, command=dump_clicked)
dump_btn.grid(column=2, row=1)

open_dump_btn = Button(window, text="open", width=8)
open_dump_btn.grid(column=0, row=2)

files_path_entry = Entry(window, width=40, textvariable=files_path)
files_path_entry.grid(column=1, row=2)

compile_btn = Button(window, text="Compile", width=8, command=comnpile_clicked)
compile_btn.grid(column=2, row=2)

window.mainloop()
