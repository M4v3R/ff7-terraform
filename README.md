# Terraform - World Map script editor for Final Fantasy VII

Author: mav  
Version: 1.0 / 07.03.2020  
License: GPL v3  

## What it is

This app will let you extract scripts and text messages that Final Fantasy VII
uses in the World map module from game files, namely - world_*.lgp files.

It will decompile the worldmap scripts and put each script in a separate file,
so you can read and edit it.

In future it will let you recompile the world lgp archive based on your changed
scripts, so you can modify the game's behavior.

## Usage

Just run the script, pointing it to the world lgp archive:

```bash
$ ./terraform.py world_us.lgp
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

Inside the `*.ev` directories you will find three kinds of files:

* `system_F.s` - system functions, where `F` is the Function ID
* `model_M_F.s` - model functions, where `M` is the Model ID, and `F` is the Function ID
* `mesh_X_Z_T.s` - mesh functions, where `X` and `Z` are coordinates, and `T` is the mesh type

Please keep the directory structure and file naming conventions intact in order
to be able to recompile this data later.

## Credits

**Reverse engineering FF7 files**  
  - Qhimm's Forums community - https://forums.qhimm.org  
  - QhimmWiki - http://wiki.ffrtt.ru/index.php?title=FF7

**Parts of PyFF7 project**  
  - Niema Moshiri - https://github.com/niemasd/PyFF7
