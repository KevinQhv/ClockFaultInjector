<h1>
    <p align="center">
        Clock Fault Injector ⏰
    </p>
</h1>



<p align="center">
    <img src="https://img.shields.io/badge/language-Python-%23f34b7d.svg?style=for-the-badge" alt="Python">
    <img src="https://img.shields.io/badge/platform-Ubuntu-0078d7.svg?style=for-the-badge" alt="Ubuntu">
</p>



## Clock Glitching Attacks with ChipWhisperer 

This Python script conducts clock glitching attacks using the ChipWhisperer platform against an FPGA target. It leverages the glitch library and various other dependencies to control glitch parameters, execute fault injections, and log the results.


## 📋 Requirements

First of all, you need to install the libraries necessary and the 2 tools required to use the script : 

- Python 3
- ChipWhisperer library
- glitch library
- tqdm
- prettytable
- progressbar
- and others as specified in the script

```bash
    $ pip3 install -r requirements.txt
```

- openFPGALoader : https://github.com/trabucayre/openFPGALoader?tab=readme-ov-file

- chipwhisperer : https://github.com/newaetech/chipwhisperer?tab=readme-ov-file

## 🚀 Getting started

1. Clone this repository on your local machine in a python environment, if necessary, to install all requirements.

2. Create an SoC to be generated in an FPGA board in order to inject a fault using the clock signal with the script. The [Litex](https://github.com/enjoy-digital/litex) framework makes it easy to create an SoC on an FPGA board.

> **For information:** Fault injection using clock glitch with Chipwhisperer requires several connections such as UART communication, the reset pin, the trigger GPIO output on the FPGA board connected to Chipwhisperer-Lite or Chipwhisperer-Pro. It is necessary to declare a GPIO as the external clock that will be supplied by the Chipwhisperer used. Please refer to [Chipwhisperer Documentation](https://chipwhisperer.readthedocs.io/en/latest/index.html)

4. Run the script with the various parameters as you wish:

```bash
    $ python3 ClockFaultInjector.py
        --name-board <name_of_FPGA_board> \
        --sn-chipwhisperer <ChipWhisperer_serial_number> \
        --ftdi-FPGA <FPGA_target_serial_number> \ 
        --freq-load-bit <bitstream_loading_frequency> \
        --bitstream-file <path_to_bitstream_file> \
        --min-width <min_width_value> \
        --max-width <max_width_value> \
        --min-offset <min_offset_value> \
        --max-offset <max_offset_value> \
        --min-ext-offset <min_ext_offset_value> \
        --max-ext-offset <max_ext_offset_value> \
        --repeat <repeat_value> \
        --resume-progress <resume_progress_value> \
        --size-data <size_of_data_to_read> \
        --function-targeted <function_targeted_value> \
        --function-argument <function_argument_value> \
        --path-exp <experiment_folder_path> \
        --csv-log <log_file_name>
``` 


Replace the placeholder values with your actual parameters. 
For have a more details :
```bash
python3 ClockFaultInjector.py --help
```

6. This script then generates a log file in csv format, with the following information on each line of the file: 
```Number of fault injections | fault injection parameters (Width, Offset, Ext_Offset) | additional data depending on your faulted program.```

## Author

This script was developed by [@KevinQhv](https://github.com/KevinQhv).
