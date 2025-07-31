"""
Caching and uncaching simple data structures based on a textual ID
"""

import hashlib
import json
import os

def get_hash(text):
    sha = hashlib.sha256()
    sha.update(text.encode())
    return sha.hexdigest()

def cache(name, content):
    text_id = get_hash(name)
    with open(f'cache/{text_id}.json', 'w') as f:
        json.dump(content, f)
    print(f'cached', text_id)

def uncache(name):
    text_id = get_hash(name)
    if not os.path.exists(f'cache/{text_id}.json'):
        return None
    with open(f'cache/{text_id}.json', 'r') as f:
        content = json.load(f)
    print(f'uncached', text_id)
    return content