#!/usr/bin/env python
# coding: utf-8

import chipwhisperer as cw
import glitch
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
import matplotlib.pylab as plt
import matplotlib
matplotlib.use('Agg')
import argparse, configparser, textwrap
import configparser
import serial
import os
from prettytable import PrettyTable

def log_file(reg_file, i_FI, event, width, offset, ext_offset, data):
    """
    Logs glitching information to a file.

    Parameters:
    reg_file (str): Name of the file to write to.
    i_FI (int): Number of fault injections.
    event (str): Description of the event.
    width (int): Glitch width.
    offset (int): Glitch offset.
    ext_offset (int): Extended glitch offset.
    data (str): Data related to the glitch event.
    """
    if reg_file is not None:
        with open(reg_file, 'a') as file:
            file.write(str(i_FI))
            file.write(",")
            file.write(str(event))
            file.write(",")
            file.write(str(width))
            file.write(",")
            file.write(str(offset))
            file.write(",")
            file.write(str(ext_offset))
            file.write(",")
            for char in data:
                if char.isprintable():  # Check if character is printable
                    file.write(char)  # Write character to the file
            file.write("\n")

def read_config(file_path):
    """
    Reads configuration file.

    Parameters:
    file_path (str): Path to the configuration file.

    Returns:
    configparser.ConfigParser: Configuration data.
    """
    config = configparser.ConfigParser()
    config.read(file_path)
    return config

def setup_generic(scope, target):
    """
    Checks and sets up the ChipWhisperer.

    Parameters:
    scope (chipwhisperer.scope): ChipWhisperer scope object.
    target (chipwhisperer.targets): ChipWhisperer target object.
    """
    try:
        if not scope.connectStatus:
            scope.con()
    except NameError:
        scope = cw.scope()

    target_type = cw.targets.SimpleSerial

    try:
        target = cw.target(scope, target_type)
    except:
        print("INFO: Caught exception on reconnecting to target - attempting to reconnect to scope first.")
        print("INFO: This is a work-around when USB has died without Python knowing. Ignore errors above this line.")
        scope = cw.scope()
        target = cw.target(scope, target_type)

    print("INFO: Found ChipWhisperer😍")

    time.sleep(0.05)
    scope.default_setup()

def reboot_flush(scope, target):
    """
    Resets the target.

    Parameters:
    scope (chipwhisperer.scope): ChipWhisperer scope object.
    target (chipwhisperer.targets): ChipWhisperer target object.
    """
    scope.io.nrst = False
    time.sleep(0.05)
    scope.io.nrst = "high"
    target.flush()

def reboot_bitstream(name_board, IDfpga, freq, bistream):
    """
    Loads the FPGA bitstream.

    Parameters:
    name_board (str): Name of the FPGA board.
    IDfpga (str): FPGA serial ID.
    freq (str): Frequency.
    bistream (str): Path to the bitstream file.
    """
    print("\nLoad the bitstream ... 🏗️")

    IDProduct_FPGA = "--ftdi-serial " + str(IDfpga) if IDfpga is not None else ""
    Frequency = "--freq " + str(freq) if freq is not None else ""
     
    command = "openFPGALoader -b " + name_board + " " + Frequency + " " + IDProduct_FPGA + " " + bistream

    subprocess.run(f'{command}', shell=True, executable="/bin/bash")

def write_result_Glitch(file, liste):
    """
    Writes glitching results to a file.

    Parameters:
    file (str): Path to the output file.
    liste (list): List of glitching results.
    """
    with open(file, 'a', newline='') as fichier_csv:
        writer = csv.writer(fichier_csv)

        for valeur in liste:
            writer.writerow([valeur])

def target_function(target, callfunc, argumentfunc):
    """
    Chooses the function target to be faulted.

    Parameters:
    target (chipwhisperer.targets): ChipWhisperer target object.
    callfunc (str): Function call.
    argumentfunc (bytes): Function argument.
    """
    target.simpleserial_write(callfunc, bytearray([]))

def disconnected_setup(scope, target):
    """
    Disconnects ChipWhisperer setup.

    Parameters:
    scope (chipwhisperer.scope): ChipWhisperer scope object.
    target (chipwhisperer.targets): ChipWhisperer target object.
    """
    scope.dis()
    target.dis()
    print("Chipwhisperer disconnect 🐌")
