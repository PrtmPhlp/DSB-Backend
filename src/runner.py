#!/usr/bin/env python3
# ------------------------------------------------
"""
Example for runner as a module
"""

import scraper
import format_json
import schema

scraper.main()
format_json.main('json/scraped.json', 'json/formatted.json')
schema.main('json/schema.json', 'json/formatted.json')
