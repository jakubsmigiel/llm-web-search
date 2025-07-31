"""
Scraping websites
"""

import trafilatura

def scrape_trafilatura(url):
    try:
        document = trafilatura.fetch_url(url)
        text = trafilatura.extract(
            document, 
            output_format="markdown", 
            with_metadata=True, 
            include_tables=True, 
            include_links=True, 
            include_comments=False, 
            favor_recall=False, 
            favor_precision=True
        )
    except Exception as e:
        text = None

    return text