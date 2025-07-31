"""
Search engine functions
"""

import time
from googlesearch import search

def google_search(query: str):
    results = search(query, num_results=100, unique=True, advanced=True)
    results_dict = []
    for sleep in (1, 1, 5, 10, 15, 30):
        try:
            results = list(results)
            break
        except:
            print(f'retrying search - sleeping {sleep}s')
            time.sleep(sleep)
        
    for result in results:
        results_dict.append({
            'title': result.title,
            'href': result.url,
            'body': result.description,
        })
        
    return results_dict