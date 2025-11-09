# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Grokipedia Proxy is a Flask-based proxy that scrapes Grokipedia.com and transforms its content into Wikipedia REST API v1 compatible JSON format. This allows SearxNG (a meta-search engine) to search Grokipedia alongside other search engines using a custom engine integration.

**Key principle:** This is a configuration-only integration with SearxNG. No SearxNG source code is modified - only configuration files and volume mounts are used.

## Architecture

The system consists of three main components:

1. **Grokipedia Proxy** (`proxy.py`): Flask application that scrapes Grokipedia.com
2. **SearxNG Custom Engine** (`grokipedia.py`): Python module loaded by SearxNG via volume mount
3. **Docker Network Integration**: Both containers communicate over the `searxng` Docker network

```
User → SearxNG → Grokipedia Engine (grokipedia.py) → Grokipedia Proxy (proxy.py) → Grokipedia.com
                                                              ↓
User ← SearxNG ← Wikipedia-format JSON ← BeautifulSoup HTML Parsing
```

### Component Details

**Grokipedia Proxy** (runs in Docker container `grokipedia-proxy`):
- Accepts Wikipedia REST API v1 format requests at `/api/rest_v1/page/summary/{title}`
- Fetches pages from `https://grokipedia.com/page/{title}`
- Parses semantic HTML using BeautifulSoup (`<article>` tags, `<span>` with `break-words` class)
- Returns Wikipedia-compatible JSON responses
- Runs on Gunicorn with 4 workers for production

**SearxNG Custom Engine** (mounted read-only into SearxNG container):
- Lives outside the SearxNG container in this project directory: `grokipedia.py`
- Mounted into container at: `/usr/local/searxng/searx/engines/grokipedia.py`
- Loaded by SearxNG at runtime - no rebuild needed
- Communicates with proxy at `http://grokipedia-proxy:5000` (internal Docker network)
- Supports both infobox and list display types

**Network Integration**:
- Proxy runs on Docker network: `searxng` (external network)
- Internal communication: `http://grokipedia-proxy:5000`
- External access: `http://localhost:5000`

## Common Development Commands

### Running the Proxy

```bash
# Build and start the proxy
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop the proxy
docker-compose down
```

### Testing

```bash
# Health check
curl http://localhost:5000/health

# Test article scraping
curl http://localhost:5000/api/rest_v1/page/summary/Python
curl http://localhost:5000/api/rest_v1/page/summary/Artificial_intelligence

# Quick integration test (requires SearxNG running)
./QUICK_CHECK.sh
```

### Local Development (without Docker)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Run Flask development server
python proxy.py
```

### SearxNG Integration

```bash
# Restart SearxNG to load engine changes
cd ../searxng
docker-compose restart searxng

# Verify engine is mounted
docker exec searxng ls -l /usr/local/searxng/searx/engines/grokipedia.py

# View SearxNG logs
docker logs searxng
```

### Debugging

```bash
# Check both containers are running
docker ps | grep -E "grokipedia|searxng"

# Verify network connectivity
docker network inspect searxng

# Test proxy from within SearxNG container
docker exec searxng wget -qO- http://grokipedia-proxy:5000/health
```

## SearxNG Configuration

**For complete setup instructions, see [SEARXNG_SETUP.md](SEARXNG_SETUP.md).**

The integration requires two configuration changes in the SearxNG setup:

**1. Volume Mount** (in SearxNG's `docker-compose.yml`):
```yaml
volumes:
  - ../seargrok/grokipedia.py:/usr/local/searxng/searx/engines/grokipedia.py:ro
```

**2. Engine Configuration** (in SearxNG's `searx/settings.yml`):
```yaml
engines:
  - name: grokipedia
    engine: grokipedia
    shortcut: grok
    base_url: http://grokipedia-proxy:5000
    enable_http: true
    display_type: ["infobox", "list"]
    categories: [general]

outgoing:
  enable_http: true  # Required for internal proxy connections
```

## Grokipedia Website Specifics

**URL Structure**: `https://grokipedia.com/page/{title}`
- Titles use underscores for spaces (e.g., `Artificial_intelligence`)
- First letter of each word is capitalized in the engine code

**HTML Structure** (as of implementation):
- Main content in `<article>` tags
- Paragraphs in `<span>` tags with `break-words` class (Tailwind CSS)
- Fallback to `<main>` or `<p>` tags if article structure changes

**Note**: Grokipedia is in early development (v0.1 as of Nov 2025). HTML structure may change and require updates to the parsing logic in `proxy.py:26-50`.

## Updating and Maintenance

### Updating SearxNG

Since this uses configuration-only integration:
```bash
# From SearxNG directory
cd ../searxng
docker compose pull searxng
docker compose up -d searxng
```

The integration will continue to work because:
- Custom engine is volume-mounted from outside
- Configuration files are preserved
- No source code modifications

### Updating the Custom Engine

1. Edit `grokipedia.py` in this directory
2. Restart SearxNG: `docker-compose restart searxng`
3. No rebuild required - engine is loaded at runtime

### Updating the Proxy

1. Edit `proxy.py` or `requirements.txt`
2. Rebuild: `docker-compose up -d --build`
3. Verify: `curl http://localhost:5000/health`

## Error Handling

The proxy handles several error cases:
- **404 from Grokipedia**: Returns empty results to SearxNG
- **HTTP errors (>=400)**: Returns empty results
- **Parsing errors**: Returns error JSON with fallback text
- **Network timeouts**: 10-second timeout on Grokipedia requests

The SearxNG engine:
- Strips bang commands from queries (e.g., `!grok Python` → `Python`)
- Capitalizes queries that are all lowercase
- Handles both 404 and error responses gracefully
- Never raises HTTP errors to SearxNG (uses `raise_for_httperror: False`)

## Dependencies

Core stack:
- Python 3.11
- Flask 3.0.0 (web framework)
- BeautifulSoup4 4.12.2 + lxml 5.1.0 (HTML parsing)
- Requests 2.31.0 (HTTP client)
- Gunicorn 21.2.0 (production WSGI server)

## File Structure

```
project-root/
├── proxy.py                    # Flask app - main proxy logic
├── grokipedia.py              # SearxNG custom engine (mounted into SearxNG container)
├── docker-compose.yml         # Container orchestration
├── Dockerfile                 # Proxy container definition
├── requirements.txt           # Python dependencies
├── settings_addition.yml      # Template for SearxNG settings
├── QUICK_CHECK.sh            # Integration test script
└── README.md                 # User documentation
```
