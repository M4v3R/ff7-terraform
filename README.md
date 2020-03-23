# Terraform - World Map script editor for Final Fantasy VII

Author: mav  
Version: 0.9.0 / 23.03.2020  
License: GPL v3  

## What it is

This app will let you extract scripts and text messages that Final Fantasy VII
uses in the World map module from game files, namely - world_*.lgp files.

It will decompile the worldmap scripts and put each script in a separate file,
so you can read and edit it.

Finally, it will let you recompile the world lgp archive based on your changed
scripts, so you can modify the game's behavior.

## Usage

You need to install Python 3 on your machine and put it in your `$PATH`. You
also need `lark-parser` Python package, which you can install by issuing the 
following command:

```bash
python -m pip install lark-parser
```

Now you can just run the script, pointing it to the world lgp archive:

```bash
python terraform.py extract world_us.lgp
```

All output files will be put in the `output` directory. Inside you will find
the following structure:

```
output\
 |- wm0.ev\      - overworld scripts
 |   |- ...
 |- wm2.ev\      - underwater scripts
 |   |- ...
 |- wm3.ev\      - snowfield (Great Glacier) scripts
 |   |- ...
 |
 -- messages.txt - text messages used by the scripts
```

Inside the `*.ev` directories you will find three kinds of files (`N` is the function index number):

* `N_system_F.s` - system functions, where `F` is the Function ID
* `N_model_M_F.s` - model functions, where `M` is the Model ID, and `F` is the Function ID
* `N_mesh_X_Z_T.s` - mesh functions, where `X` and `Z` are coordinates, and `T` is the mesh type

Please keep the directory structure and file naming conventions intact in order
to be able to recompile this data later.

Note that sometimes `N` will be in the format `003-002`. This means that this function is a duplicate
of another function, so if you want to edit it just go to that other function (#002 in this case).

To recompile your world lgp file issue the following command:

```bash
python terraform.py compile output world_us.lgp
```

Where `output` is the directory containing the extracted scripts, and `world_us.lgp` is the archive
you want to put the new scripts into.

## WorldScript documentation

Files with `.s` extension contain a disassembled version of worldmap scripts in a Pascal-like 
language we call WorldScript. Although this tool doesn't currently provide the documentation for it 
yet, you can read about how world scripts work and what are the available opcodes on the FF7 Wiki:

http://wiki.ffrtt.ru/index.php?title=FF7/WorldMap_Module/Script

http://wiki.ffrtt.ru/index.php?title=FF7/WorldMap_Module/Script/Opcodes

## Credits

**Reverse engineering FF7 files**  
  - Qhimm's Forums community - https://forums.qhimm.org  
  - QhimmWiki - http://wiki.ffrtt.ru/index.php?title=FF7

**Parts of PyFF7 project**  
  - Niema Moshiri - https://github.com/niemasd/PyFF7
