# NES Header Repair Tool

Please note that Python is not a language I use much, and this script is a merely intended as a quick and dirty way to fix NES headers. It DOES alter the contents of files, so please bet aware that there is some potential something could go wrong. Please make sure to have backups before attempting to use it.

## Requirements
This script requires New Rising Sun's NES header database which can be found [here](https://forums.nesdev.com/viewtopic.php?f=3&t=19940&p=248796). It needs to be unzipped and placed in the same directory as the script itself.

Although the script does run with python2, unicode handling for file renaming works better in Python 3.

A normal command to run the script would be:

```
python3 nes_header_repair.py
```

## Configuration

There are several options at the top of the script file which can be adjusted by the user. By default TRIAL_RUN is enabled, which will prevent any changes to files. Please be sure to adjust these settings to your liking and ensure they work as expected before disabling TRIAL_RUN.
