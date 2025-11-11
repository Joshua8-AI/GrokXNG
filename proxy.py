from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/api/rest_v1/page/summary/<path:title>')
def get_summary(title):
    """
    Proxy endpoint that mimics Wikipedia API format.
    Fetches from Grokipedia and transforms to Wikipedia-compatible JSON.
    """
    try:
        # Fetch from Grokipedia - URL structure is /page/{title}
        groki_url = f"https://grokipedia.com/page/{title.replace(' ', '_')}"
        logger.info(f"Fetching from Grokipedia: {groki_url}")

        resp = requests.get(groki_url, timeout=10)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # Extract content - Grokipedia uses semantic HTML with <article> tags
        article = soup.find("article")
        if article:
            extract_html = str(article)
        else:
            # Fallback to main tag
            main = soup.find("main")
            extract_html = str(main) if main else ""

        # Extract text summary from the first paragraph in the article
        # Grokipedia uses <span> tags with class "mb-4 block break-words" for paragraphs
        if article:
            # Try to find span with the paragraph class first
            first_p = article.find("span", class_=lambda c: c and "break-words" in c)
            # Fallback to any p or span tag
            if not first_p:
                first_p = article.find("p") or article.find("span")
        else:
            first_p = soup.find("span", class_=lambda c: c and "break-words" in c)
            if not first_p:
                first_p = soup.find("p") or soup.find("span")

        extract = first_p.get_text(strip=True) if first_p else "No summary available."

        # Mimic Wikipedia REST API response format
        fake_wiki_response = {
            "type": "standard",
            "title": title.replace('_', ' '),
            "extract": extract,
            "extract_html": extract_html,
            "lang": "en",
            "dir": "ltr",
            "timestamp": None
        }

        logger.info(f"Successfully processed: {title}")
        return jsonify(fake_wiki_response)

    except requests.HTTPError as e:
        # 404s and other HTTP errors should return empty results for SearxNG
        logger.warning(f"HTTP error from Grokipedia ({e.response.status_code}): {groki_url}")
        return jsonify({
            "type": "standard",
            "title": title.replace('_', ' '),
            "extract": "",
            "extract_html": "",
            "lang": "en",
            "dir": "ltr",
            "timestamp": None
        }), 200
    except requests.RequestException as e:
        # Network errors, timeouts, etc. - return empty results
        logger.error(f"Network error fetching from Grokipedia: {e}")
        return jsonify({
            "type": "standard",
            "title": title.replace('_', ' '),
            "extract": "",
            "extract_html": "",
            "lang": "en",
            "dir": "ltr",
            "timestamp": None
        }), 200
    except Exception as e:
        # Parsing errors - return error with fallback text
        logger.error(f"Parsing error: {e}")
        return jsonify({
            "type": "error",
            "title": title.replace('_', ' '),
            "extract": f"Error parsing content: {str(e)}",
            "extract_html": "",
            "lang": "en"
        }), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
