#!/usr/bin/env python
# coding: utf-8

"""
This script performs clock glitching attacks using ChipWhisperer against an FPGA target.
"""

#### LIBRARY ####

import chipwhisperer as cw
import src.glitch as glitch
import subprocess
import csv
import ast
import time
from importlib import reload
from tqdm.notebook import tqdm
import re
import struct
from progressbar import progressbar
import progressbar
import argparse, configparser, textwrap
import configparser
import serial
import os
from prettytable import PrettyTable
import pandas as pd
import csv, ast

import src.cw_toolkit as tk

# Widget for display progress bar
widgets = [
        progressbar.Percentage(),
        ' [', progressbar.Timer(), '] ',
        progressbar.GranularBar(), ' ',
    ]

# Configuration scope
PLATFORM = "NOTHING"
SCOPETYPE = 'OPENADC'
SS_VER = 'SS_VER_1_0'

# Arguments manager
parser = argparse.ArgumentParser(description = textwrap.dedent('''
Arguments description for glitch clock with the chipWhisperer against FPGA target

 * Only one part is faulty, it needs to be configured :
   - width, offset, ext_offset
   - repeat parameters can be modified
   - function-targeted (if other than NAPOT)
   - specify the folder with README and log file of the experiment
   - specify the log file in csv
   - And a parameter allows to resume the experiment, where it crashed, if necessary about the number of FI.
'''), formatter_class=argparse.RawTextHelpFormatter)

parser.add_argument('--name-board',         type=str, required=True,    help='Name of FPGA used')
parser.add_argument('--sn-chipwhisperer',   type=str, required=True,    help='ID Product of Chipwhisperer used')
parser.add_argument('--ftdi-FPGA',          type=str, required=True,    help='ID Product of FPGA targeted')
parser.add_argument('--freq-load-bit',      type=int,                   help='Frequency speed for load the bitstream with OpenFPGALoader')
parser.add_argument('--bitstream-file',     type=str, required=True,    help='Bitstream file target`s build path')
parser.add_argument('--repeat',             type=int, default=1,        help='Value repeat')
parser.add_argument('--Nb-FI',              type=int, default=1,        help='Number of injections on a parameter set')
parser.add_argument('--resume-progress',    type=int, default=0,        help='Value to resume progression')
parser.add_argument('--size-data',          type=int, default=0,        help='Size of character to read by injection')
parser.add_argument('--function-targeted',  type=str, default='s',      help='Specify the letter for selected the function target:\n')
parser.add_argument('--function-argument',  type=str, default='',       help='If necessary specify argument for function target\n')
parser.add_argument('--path-exp',                     default=None,     help='Folder for experimentation')
parser.add_argument('--csv-log',                      default=None,     help='Log file')
parser.add_argument('--file-log',    type=str, required = True,  help = 'Log file to analyzed')
args = parser.parse_args()


# Load CSV file
try:
    df_log = pd.read_csv(args.file_log, header=None)
except Exception as e:
    print("ERROR: read_csv()")
    lines = []
    with open(args.file_log, 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        for line in reader:
            lines.append(line)
    df_log = pd.DataFrame(lines)


list_width      = []
list_offset     = []
list_ext_offset = []

for index, row in df_log.iterrows():

    if row['event'] == 'success':
        list_width.append(float(row['Width']))
        list_offset.append(float(row['Offset']))
        list_ext_offset.append(float(row['Ext_Offset']))

args = parser.parse_args()

if args.path_exp is not None and not os.path.exists(args.path_exp):
    os.makedirs(args.path_exp)

if args.path_exp is not None:
    file_md = "README.md"
    README = os.path.join(args.path_exp, file_md)

    print("\nClock glitching attacks using ChipWhisperer against an FPGA target 🎯 \n")

    # Display configuration 
    print("Configuration setup 🔧 : ")
    print(f"Bitstream File: {args.bitstream_file}")
    print(f"Function Targeted: {args.function_targeted}")
    print("\nGlitch Parameters 🎯:")
    print("Testing the values success in file : ", args.file_log_replay)
    print(f"Repeat: {args.repeat}")

    print("\nLog file 📁: ")
    print(args.csv_log)

    with open(README, 'a') as file:
        file.write("Configuration setup 🔧 : \n")
        file.write(f"Bitstream File: {args.bitstream_file} \n")
        file.write(f"ChipWhisperer setup is the {args.sn_chipwhisperer} \n")
        file.write(f"FPGA setup is the {args.ftdi_FPGA} \n")
        file.write(f"Function Targeted: {args.function_targeted}\n")
        file.write("\nGlitch Parameters 🎯:\n")
        file.write(f"\nRepeat: {args.repeat}\n")
        file.write("\nLog files 📁:\n")
        file.write(args.csv_log)

if args.csv_log is not None:
    file_log = os.path.join(args.path_exp, args.csv_log)

print("\n Scope preparation ... 🎠\n")

# declaration scope and target
scope = cw.scope(sn=args.sn_chipwhisperer)
target = cw.target(scope)

# Checking the ChipWhisperer 
tk.setup_generic(scope, target)

# Clock configuration for 25Mhz
# Multiply the ChipWhisperer clock to get 25 MHz
scope.clock.clkgen_mul = 7
target.baud = 115200
print("baudrate : ", target.baud) # Display the baudrate communication

# ## Settings configuration for clock glitch
scope.glitch.clk_src = 'clkgen'
scope.glitch.trigger_src = 'ext_single'
scope.glitch.output = "clock_xor"
scope.io.hs2 = "glitch"

# ## Results of fault injections
gc = glitch.GlitchController(groups=["success", "reset", "normal"], parameters=["width", "offset", "ext_offset"])

print("\nFault injection in progress ... ⏰\n")

iteration_progressbar = 0 # variable for progress bar
iteration_success     = 0
iteration_normal      = 0
iteration_reset       = 0
iteration_FI          = 0

# reload the bitstream
tk.reboot_bitstream(args.name_board, args.ftdi_FPGA, args.freq_load_bit, args.bitstream_file)

with progressbar.ProgressBar(max_value=args.Nb_FI*len(list_width), widgets=widgets) as bar:

    for param_select in range(len(list_width)):

        for i in range(args.Nb_FI):

            iteration_progressbar += 1
            iteration_FI += 1 # counter number of fault injection

            if iteration_FI >= args.resume_progress:

                print("progressbar : ", iteration_progressbar)

                bar.update(iteration_progressbar)

                scope.glitch.width = list_width[param_select]
                scope.glitch.offset = list_offset[param_select]
                scope.glitch.ext_offset = list_ext_offset[param_select]

                print("\nWidth | Offset | Ext_Offset [", scope.glitch.width, " | ", scope.glitch.offset, " | ", scope.glitch.ext_offset, "]\n")

                if scope.adc.state:
                    print(scope.adc.state)
                    print("reboot ... 💥")
                    gc.add("reset", (scope.glitch.width, scope.glitch.offset, scope.glitch.ext_offset))
                    tk.reboot_flush(scope, target)
                    tk.reboot_bitstream(args.name_board, args.ftdi_FPGA, args.freq_load_bit, args.bitstream_file)

                tk.reboot_flush(scope, target) # initialization

                scope.arm()

                tk.target_function(target, args.function_targeted, args.function_argument)

                ret = scope.capture()

                if ret:
                    print('Timeout - no trigger')
                    gc.add("reset", (scope.glitch.width, scope.glitch.offset, scope.glitch.ext_offset))
                    print("reboot ... 💥")
                    tk.reboot_bitstream(args.name_board, args.ftdi_FPGA, args.freq_load_bit, args.bitstream_file)
                    tk.reboot_flush(scope, target)
                    iteration_reset += 1
                    event = "reset"

                else:
                    val = target.simpleserial_read_witherrors('r', 1, glitch_timeout=10, ack=False)
                    print(val)

                    if val['valid'] is False:
                        gc.add("reset", (scope.glitch.width, scope.glitch.offset, scope.glitch.ext_offset))
                        plt.plot(scope.glitch.width, scope.glitch.offset, 'xr', alpha=1)
                        print("reboot ... 💥")
                        iteration_reset += 1
                        event = "reset"

                    else:
                        if val['payload'] == bytearray([0xc]):
                            broken = True
                            gc.add("success", (scope.glitch.width, scope.glitch.offset, scope.glitch.ext_offset))
                            print(val)
                            print(scope.glitch.width, scope.glitch.offset, scope.glitch.ext_offset)
                            plt.plot(scope.glitch.width, scope.glitch.offset, 'go', alpha=1)
                            print("Successful injection ! 🐙 \n")
                            iteration_success += 1
                            event = "success"
                        else:
                            gc.add("normal", (scope.glitch.width, scope.glitch.offset, scope.glitch.ext_offset))
                            event = "normal"
                            iteration_normal+=1

                data_read = target.read(args.size_data)

                data_read =  str(scope.io.tio_states[2]) + ", " + data_read

                tk.log_file(file_log, iteration_FI, event, scope.glitch.width, scope.glitch.offset, scope.glitch.ext_offset, data_read)
        
    print("FI: ", iteration_FI)
    print("normal: ", iteration_normal)
    print("reset: ", iteration_reset)
    print("success: ", iteration_success)

print("\n --- Results ---\n")
table = PrettyTable()
table.field_names = ["Parameters", "number of visits"]
table.add_row(["success", iteration_success])
table.add_row(["normal", iteration_normal])
table.add_row(["reset", iteration_reset])
print(table)

with open(README, 'a') as file:
    file.write("\n\n --- Results ---\n")
    table_str = table.get_string()
    file.write(table_str)
    file.write("\nWith a total FI of ")
    file.write(str(args.Nb_FI))

# Disconnected the setup
tk.disconnected_setup(scope, target)

assert broken, "No fault was successfully injected"
