#!/bin/bash
echo "============================================================"
echo "  🛒 DUX IMPORTS - Sistema de E-commerce"
echo "============================================================"
cd "$(dirname "$0")"
pip3 install -r requirements.txt -q
python3 app.py
