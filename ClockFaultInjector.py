#!/usr/bin/env python
# coding: utf-8

"""
This script performs clock glitching attacks using ChipWhisperer against an FPGA target.

Requirements:
- ChipWhisperer library
- glitch library
- subprocess
- csv
- ast
- time
- importlib
- tqdm
- re
- struct
- progressbar
- argparse
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

import src.cw_toolkit as tk

    
# Widget for display progress bar
widgets = [
        progressbar.Percentage(),
        ' [', progressbar.Timer(), '] ',
        progressbar.GranularBar(), ' ',
    ]


# Configuration scope
PLATFORM ="NOTHING"
SCOPETYPE = 'OPENADC'
SS_VER = 'SS_VER_1_0'

# Arguments manager
parser = argparse.ArgumentParser(description = textwrap.dedent('''
Arguments description for glitch clock with the chipWhisperer against FPGA target

 * All is faulty, it needs to be configured :
   - name of board FPGA used
   - ID Product of Chipwhisperer used
   - ID Product of FPGA board used
   - bitstream-file
 * Only one part is faulty, it needs to be configured :
   - min-width, max-width & min-offset, max-offset & min-ext-offset, max-ext-offset
   - repeat parameters can be modified
   - function-targeted (if other than NAPOT)
   - specify the folder with README and log file of the experiment
   - specify the log file in csv
   - And a parameter allows to resume the experiment, where it crash, if neccessary about the number of FI.
'''), formatter_class=argparse.RawTextHelpFormatter)

parser.add_argument('--name-board',         type=str,                     help = 'Name of FPGA used', required = True)
parser.add_argument('--sn-chipwhisperer',   type=str,                     help = 'ID Product of Chipwhisperer used', required = True)
parser.add_argument('--ftdi-FPGA',          type=str,                     help = 'ID Product of FPGA targeted', required = True)
parser.add_argument('--freq-load-bit',      type=int,                     help = 'Frequency speed for load the bitstream with OpenFPGALoader')
parser.add_argument('--bitstream-file',     type=str,                     help = 'Bitstream file target`s build path', required = True)
parser.add_argument('--min-width',          type=int,   default = -49,    help = 'Value minimum Width')
parser.add_argument('--max-width',          type=int,   default = 49,     help = 'Value maximum Width')
parser.add_argument('--min-offset',         type=int,   default = -49,    help = 'Value minimum offset')
parser.add_argument('--max-offset',         type=int,   default = 49,     help = 'Value maximum offset')
parser.add_argument('--min-ext-offset',     type=int,   default = 0,      help = 'Value minimum ext_offset')
parser.add_argument('--max-ext-offset',     type=int,   default = 200,    help = 'Value maximum ext_offset')
parser.add_argument('--repeat',             type=int,   default = 5,      help = 'Value repeat')
parser.add_argument('--resume-progress',    type=int,   default = 0,      help = 'Value to resume progression')
parser.add_argument('--size-data',          type=int,   default = 0,      help = 'Size of character to read by injection')
parser.add_argument('--function-targeted',  type=str,   default='s',      help = 'Specify the letter for selected the function target:\n')
parser.add_argument('--function-argument',  type=str,   default='',       help = 'If necessary specify argument for function target\n')
parser.add_argument('--path-exp',                default = None,          help = 'Folder experimentation')
parser.add_argument('--csv-log',                default = None,           help = 'Log file')
args = parser.parse_args()


if args.path_exp is not None and not os.path.exists(args.path_exp):
    os.makedirs(args.path_exp)

if args.path_exp is not None:
    file_md = "README.md"
    README                  = os.path.join(args.path_exp, file_md)

    print("\nClock glitching attacks using ChipWhisperer against an FPGA target 🎯 \n")

    # Display configuration 
    print("Configuration setup 🔧 : ")
    print(f"Bitstream File: {args.bitstream_file}")
    print(f"Function Targeted: {args.function_targeted}")
    print("\nGlitch Parameters 🎯:")
    table_conf = PrettyTable()
    table_conf.field_names = ["Parameters", "Minimum", "Maximum"]
    table_conf.add_row(["width", args.min_width, args.max_width])
    table_conf.add_row(["offset", args.min_offset, args.max_offset])
    table_conf.add_row(["ext_offset", args.min_ext_offset, args.max_ext_offset])
    print(table_conf)
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
        table_conf_str = table_conf.get_string()
        file.write(table_conf_str)
        file.write(f"\nRepeat: {args.repeat}\n")
        file.write("\nLog files 📁:\n")
        file.write(args.csv_log)

if args.csv_log is not None:
    file_log       = os.path.join(args.path_exp, args.csv_log)


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

### Faults injections in clock ###

# Glitch a part between -49 and 49
# These width/offset settings are for CW-Lite/Pro; width/offset

# 3 settings for realized the glitch Clock
gc.set_range("width", args.min_width, args.max_width)
gc.set_range("offset", args.min_offset, args.max_offset)
gc.set_range("ext_offset", args.min_ext_offset, args.max_ext_offset)

step = 1
gc.set_global_step(step)

scope.glitch.repeat = args.repeat
sample_size = 10

tk.reboot_flush(scope, target)
broken = False


print("\nFault injection in progress ... ⏰\n")

# Total number step during the clock glitch
result = 1
for i in range(len(gc.parameters)):
    range_param = abs(gc.parameter_max[i] - gc.parameter_min[i]) + 1
    result *= range_param 
    
# result*= scope.glitch.repeat
print("Total number fault injection : ", result)

iteration_progressbar = 0 # variable for progress bar
iteration_success     = 0
iteration_normal      = 0
iteration_reset       = 0
iteration_FI          = 0

# reload the bitstream
tk.reboot_bitstream(args.name_board, args.ftdi_FPGA, args.freq_load_bit, args.bitstream_file)

with progressbar.ProgressBar(max_value=result, widgets=widgets) as bar:

    for glitch_settings in gc.glitch_values():

        iteration_progressbar += 1
        iteration_FI += 1 # counter number of fault injection

        if iteration_FI >= args.resume_progress:

            
            print("progressbar : ", iteration_progressbar)

            bar.update(iteration_progressbar)

            scope.glitch.offset = glitch_settings[1]
            scope.glitch.width = glitch_settings[0]
            scope.glitch.ext_offset = glitch_settings[2]

            print("\nWidth | Offset | Ext_Offset [",glitch_settings[0]," | ", glitch_settings[1], " | ", glitch_settings[2],"]\n")

            if scope.adc.state:

                print(scope.adc.state)

                print("reboot ... 💥")
                # can detect crash here (fast) before timing out (slow)
                print("Trigger still high!")
                gc.add("reset", (scope.glitch.width, scope.glitch.offset, scope.glitch.ext_offset))
                #Device is slow to boot?
                tk.reboot_flush(scope, target)

                # reload the bitstream
                tk.reboot_bitstream(args.name_board, args.ftdi_FPGA, args.freq_load_bit, args.bitstream_file)


            tk.reboot_flush(scope, target) # initialisation

            scope.arm()

            tk.target_function(target, args.function_targeted, args.function_argument)

            ret = scope.capture()

            if ret:
                print('Timeout - no trigger')
                gc.add("reset", (scope.glitch.width, scope.glitch.offset, scope.glitch.ext_offset))

                print("reboot ... 💥")

                # reload the bitstream
                tk.reboot_bitstream(args.name_board, args.ftdi_FPGA, args.freq_load_bit, args.bitstream_file)

                #Device is slow to boot?
                tk.reboot_flush(scope, target)

                iteration_reset+=1
                event = "reset"

            else:

                val = target.simpleserial_read_witherrors('r', 1, glitch_timeout=10, ack=False)#For loop check
                print(val)

                if val['valid'] is False:
                    gc.add("reset", (scope.glitch.width, scope.glitch.offset, scope.glitch.ext_offset))
                    plt.plot(scope.glitch.width, scope.glitch.offset, 'xr', alpha=1)
                    print("reboot ... 💥")

                    iteration_reset+=1
                    event = "reset"

                else:
                    if val['payload'] == bytearray([0xc]): #for loop check
                        broken = True
                        gc.add("success", (scope.glitch.width, scope.glitch.offset, scope.glitch.ext_offset))

                        print(val)
                        print(scope.glitch.width, scope.glitch.offset, scope.glitch.ext_offset)
                        plt.plot(scope.glitch.width, scope.glitch.offset, 'go', alpha=1)
                        print("Successful injection ! 🐙 \n")

                        iteration_success+=1
                        event = "success"

                    else:
                        gc.add("normal", (scope.glitch.width, scope.glitch.offset, scope.glitch.ext_offset))
                        event = "normal"
                        iteration_normal+=1

            data_read = target.read(args.size_data)

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
    file.write(str(result))

# Disconnected the setup
tk.disconnected_setup(scope, target)

assert broken, "No fault was successfully injected"
