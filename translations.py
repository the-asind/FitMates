# Load translations
import json

translations = {}
for lang in ['en', 'ru']:
    with open(f'translations/{lang}.json', 'r', encoding='utf-8') as f:
        translations[lang] = json.load(f)