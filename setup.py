import sys
from cx_Freeze import setup, Executable

includefiles = ['world_script.lark']

# Dependencies are automatically detected, but it might need fine tuning.
build_exe_options = {"packages": ["os", "lark"],
                     "include_files": includefiles}

# GUI applications require a different base on Windows (the default is for a
# console application).
base = None

setup(name="Terraform 3000",
      version="0.1",
      description="eso",
      options={"build_exe": build_exe_options},
      executables=[Executable("main_ui.py", base=base)])
