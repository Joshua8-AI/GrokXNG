# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Grokipedia Engine
-----------------

This engine connects to Grokipedia via a proxy that mimics Wikipedia's REST API format.
The proxy translates Grokipedia's HTML structure into Wikipedia-compatible JSON responses.

Configuration in settings.yml:
    engines:
      - name: grokipedia
        engine: grokipedia
        shortcut: grok
        base_url: http://grokipedia-proxy:5000
        display_type: ["infobox", "list"]
        categories: [general]
"""

import urllib.parse
from searx import utils
from searx import network as _network

# Engine configuration
about = {
    "website": 'https://grokipedia.com/',
    "wikidata_id": None,
    "official_api_documentation": None,
    "use_official_api": False,
    "require_api_key": False,
    "results": 'JSON',
}

# Default display type - can be overridden in settings.yml
display_type = ["infobox", "list"]
"""Display results in both infobox and result list"""

# Base URL for the Grokipedia proxy - can be overridden in settings.yml
base_url = 'http://grokipedia-proxy:5000'
"""The Grokipedia proxy base URL"""

# API endpoint template
api_path = '/api/rest_v1/page/summary/{title}'


def request(query, params):
    """Assemble a request to the Grokipedia proxy."""
    # Strip any bang commands from the query (e.g., "!grok Python" or "\!grok Python" -> "Python")
    import re
    query = re.sub(r'^\\?!\w+\s+', '', query).strip()

    # Capitalize the first letter of each word for better results
    if query and query.islower():
        query = query.title()

    # URL encode the query
    title = urllib.parse.quote(query.replace(' ', '_'))

    # Build the full URL
    params['url'] = base_url + api_path.format(title=title)

    # Don't raise errors on 404 - we'll handle them in response()
    params['raise_for_httperror'] = False
    params['soft_max_redirects'] = 2

    return params


def response(resp):
    """Parse the JSON response from the Grokipedia proxy."""
    results = []

    # Handle 404 - article not found
    if resp.status_code == 404:
        return []

    # Handle other HTTP errors
    if resp.status_code >= 400:
        return []

    try:
        api_result = resp.json()
    except Exception:
        return []

    # Check if this is an error response from the proxy
    if api_result.get('type') == 'error':
        return []

    # Extract data from the response
    title = utils.html_to_text(api_result.get('title', ''))
    extract = api_result.get('extract', '')

    # Build Grokipedia URL
    grokipedia_link = f"https://grokipedia.com/page/{urllib.parse.quote(title.replace(' ', '_'))}"

    # Add result to list if 'list' is in display_type
    if "list" in display_type:
        results.append({
            'url': grokipedia_link,
            'title': title,
            'content': extract[:300] + '...' if len(extract) > 300 else extract,
        })

    # Add infobox if 'infobox' is in display_type and we have content
    if "infobox" in display_type and extract:
        results.append({
            'infobox': title,
            'id': grokipedia_link,
            'content': extract,
            'urls': [{'title': 'Grokipedia', 'url': grokipedia_link}],
        })

    return results
