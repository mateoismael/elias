#!/usr/bin/env python3
import os

# Debug CSV path detection
csv_path = os.getenv('PHRASES_CSV', 'frases_pilot_autores.csv')
print(f"CSV path from env: {csv_path}")
print(f"File exists: {os.path.exists(csv_path)}")

if os.path.exists(csv_path):
    print(f"File found at: {os.path.abspath(csv_path)}")
    with open(csv_path, 'r') as f:
        lines = f.readlines()
        print(f"File has {len(lines)} lines")
else:
    print("File not found, checking current directory:")
    import glob
    csv_files = glob.glob("*.csv")
    print(f"CSV files found: {csv_files}")