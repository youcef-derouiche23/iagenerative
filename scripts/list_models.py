#!/usr/bin/env python3
"""Script pour lister les modèles Gemini disponibles"""

import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

print("Modèles Gemini disponibles:\n")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(f"- {m.name}")
        print(f"  Description: {m.description}")
        print()
