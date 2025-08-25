#!/usr/bin/env python3
import os
import sys
sys.path.append('scripts')

# Import the function directly
from send_emails import load_phrases

try:
    csv_path = os.getenv('PHRASES_CSV', 'frases_pilot_autores.csv')
    print(f"Trying to load: {csv_path}")
    phrases = load_phrases(csv_path)
    print(f"Successfully loaded {len(phrases)} phrases")
    print(f"First phrase: {phrases[0].text[:50]}...")
except Exception as e:
    print(f"Error: {e}")
    print(f"Error type: {type(e)}")