#!/bin/bash
if [ -d ".venv" ]
then
    source .venv/bin/activate
    python3 app.py
else
    python3 -m venv .venv
    source .venv/bin/activate
    python3 -m pip install --upgrade pip
    pip3 install -r requirements.txt
    python3 app.py
fi