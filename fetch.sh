#!/bin/bash
# Local refresh: new videos -> product photos -> rebuild site
export PYTHONUTF8=1
cd "$(dirname "$0")"
python update.py && python images.py && python build.py
