# Grokipedia Proxy for SearxNG

A lightweight Flask-based proxy that scrapes Grokipedia and transforms the content into Wikipedia API-compatible JSON format for use with SearxNG.

## ⚠️ Important: No Source Code Modifications

**This integration uses ONLY configuration files - NO SearxNG source code was modified.**

- ✅ Uses **official SearxNG Docker image** (`searxng/searxng:latest`)
- ✅ Custom engine is **volume-mounted** (not baked into the image)
- ✅ Only **configuration files** were modified (docker-compose.yml, settings.yml)
- ✅ You can **safely update SearxNG** without breaking this integration

See [SearxNG Integration Documentation](../searxng/GROKIPEDIA_INTEGRATION.md) for details.

## Features

- Scrapes Grokipedia.com and mimics Wikipedia REST API v1 format
- Easy Docker deployment with docker-compose
- Health check endpoint for monitoring
- Production-ready with Gunicorn (4 workers)
- Automatic network integration with SearxNG
- Custom SearxNG engine for seamless integration
- **Configuration-only integration** - no SearxNG code modifications

## Architecture

```
User Query → SearxNG → Grokipedia Engine → Grokipedia Proxy → Grokipedia.com
                                                    ↓
User ← SearxNG ← Wikipedia-format JSON ← HTML Parsing (BeautifulSoup)
```

## Setup Complete! ✓

The integration has been configured:

1. ✓ Proxy created (`proxy.py`)
2. ✓ Docker configuration ready (`docker-compose.yml`, `Dockerfile`)
3. ✓ Custom Grokipedia engine created (`grokipedia.py`)
4. ✓ SearxNG docker-compose updated to mount the engine
5. ✓ SearxNG settings.yml updated with Grokipedia source

## Documentation

- **[SearxNG Setup Guide](SEARXNG_SETUP.md)** - Complete step-by-step instructions for integrating with SearxNG
- **[CLAUDE.md](CLAUDE.md)** - Technical architecture and development guide
- **[MODIFICATIONS_SUMMARY.md](MODIFICATIONS_SUMMARY.md)** - Audit trail of all changes

## Quick Start

### 1. Start the Grokipedia Proxy

```bash
# From this project directory
docker-compose up -d --build
```

The proxy runs on the internal Docker network only (not publicly accessible for security).

### 2. Test the Proxy

**Option A: Test from within the Docker network**
```bash
# Health check from SearxNG container
docker exec searxng wget -qO- http://grokipedia-proxy:5000/health

# Test a query from SearxNG container
docker exec searxng wget -qO- http://grokipedia-proxy:5000/api/rest_v1/page/summary/Python

# Or from the proxy container itself
docker exec grokipedia-proxy curl http://localhost:5000/health
docker exec grokipedia-proxy curl http://localhost:5000/api/rest_v1/page/summary/Python
```

**Option B: Temporarily expose for testing (development only)**
```bash
# Add to docker-compose.yml temporarily:
#   ports:
#     - "127.0.0.1:5000:5000"  # Localhost only
# Then: docker-compose up -d

# Test locally
curl http://localhost:5000/health
curl http://localhost:5000/api/rest_v1/page/summary/Artificial_intelligence

# Remove port mapping when done for security
```

### 3. Configure and Restart SearxNG

**See [SEARXNG_SETUP.md](SEARXNG_SETUP.md) for detailed configuration instructions.**

Quick summary - you need to modify two SearxNG files:
1. `docker-compose.yml` - Add volume mount for custom engine
2. `searx/settings.yml` - Add Grokipedia engine configuration and enable HTTP

Then restart SearxNG:

```bash
# From your SearxNG directory
cd ../searxng
docker-compose restart searxng
```

### 4. Test in SearxNG

Open SearxNG at http://localhost:8080 and try:

- `!grok Python` - Search Grokipedia for Python
- `!grok Artificial intelligence` - Search for AI article

You should see results from both the infobox and the results list!

## What Was Configured

### Configuration-Only Integration ✅

**No SearxNG source code was modified.** All changes are configuration files that work with the official Docker image.

**For step-by-step setup instructions, see [SEARXNG_SETUP.md](SEARXNG_SETUP.md).**

### 1. Grokipedia Proxy (This Directory)
- `proxy.py` - Flask app that scrapes Grokipedia.com (URL: `https://grokipedia.com/page/{title}`)
- Uses semantic HTML parsing: `<article>` tags for content, `<span>` for paragraphs
- Returns Wikipedia REST API v1 compatible JSON

### 2. Custom SearxNG Engine (External File)
- `grokipedia.py` - Custom engine for SearxNG
- **Lives outside the container** in this project directory
- **Mounted into container** at: `/usr/local/searxng/searx/engines/grokipedia.py` (read-only)
- Loaded by SearxNG at runtime - no image rebuild needed

### 3. Network Integration
- Proxy runs on Docker network: `searxng`
- SearxNG can access proxy at: `http://grokipedia-proxy:5000`
- External access: `http://localhost:5000`

### 4. SearxNG Configuration Files Modified

#### SearxNG's `searx/settings.yml` - Engine Configuration

Added Grokipedia engine entry (after Wikipedia):

```yaml
  - name: grokipedia
    engine: grokipedia
    shortcut: grok
    base_url: http://grokipedia-proxy:5000
    enable_http: true
    display_type: ["infobox", "list"]
    categories: [general]
```

Modified `outgoing:` section to enable HTTP:

```yaml
outgoing:
  enable_http2: true
  enable_http: true  # ← Added for internal proxy connections
```

#### SearxNG's `docker-compose.yml` - Volume Mount

Added volume mount to load custom engine:

```yaml
volumes:
  - ./searx:/etc/searxng:rw
  - ../seargrok/grokipedia.py:/usr/local/searxng/searx/engines/grokipedia.py:ro  # ← Added
```

**Why this works:**
- SearxNG's official image supports loading custom engines via volume mounts
- The engine file lives **outside the container** (in this directory)
- You can update SearxNG without losing the integration
- No need to rebuild SearxNG from source

## Technical Details

### Grokipedia URL Structure
Grokipedia uses the following URL pattern:
```
https://grokipedia.com/page/{title}
```

Example: `https://grokipedia.com/page/Python` or `https://grokipedia.com/page/Artificial_intelligence`

### HTML Structure Parsed
The proxy extracts:
- `<article>` tag for main content
- First `<span>` tag with `break-words` class for summary text
- Uses standard semantic HTML with Tailwind CSS classes

## Updating SearxNG

Since this integration uses only configuration files, you can safely update SearxNG:

```bash
# From your SearxNG directory
cd ../searxng

# Pull the latest official image
docker compose pull searxng

# Restart with the new image
docker compose up -d searxng
```

**The Grokipedia integration will continue to work** because:
- The custom engine (`grokipedia.py`) is volume-mounted from outside the container
- Configuration files (`settings.yml`, `docker-compose.yml`) are preserved
- No SearxNG source code was modified

If the integration stops working after an update, simply restart both containers:

```bash
# From SearxNG directory
docker compose restart searxng

# From this project directory
cd ../seargrok
docker compose restart grokipedia-proxy
```

### Change Port

Edit `docker-compose.yml` to change the exposed port:

```yaml
ports:
  - "YOUR_PORT:5000"
```

## Architecture

```
SearxNG Container
    |
    | HTTP Request
    v
Grokipedia Proxy (Flask)
    |
    | HTTP Request
    v
Grokipedia.com
    |
    | HTML Response
    v
Grokipedia Proxy (BeautifulSoup parsing)
    |
    | JSON Response (Wikipedia format)
    v
SearxNG Container
```

## Troubleshooting

### Proxy not accessible from SearxNG

- Check that both containers are on the same Docker network:
  ```bash
  docker network inspect searxng
  ```
- Verify both containers are running:
  ```bash
  docker ps | grep -E "searxng|grokipedia"
  ```
- Test proxy directly:
  ```bash
  curl http://localhost:5000/health
  ```

### No results in SearxNG

- Check SearxNG logs:
  ```bash
  docker logs searxng
  ```
- Check proxy logs:
  ```bash
  docker-compose logs -f
  ```
- Verify the engine is loaded:
  ```bash
  docker exec searxng ls -l /usr/local/searxng/searx/engines/grokipedia.py
  ```

### Parse errors or "No summary available"

- Grokipedia's HTML structure may have changed
- Check logs: `docker-compose logs -f grokipedia-proxy`
- Update CSS selectors in `proxy.py` if needed (currently uses `<article>` and `<p>` tags)
- Test a specific article:
  ```bash
  curl http://localhost:5000/api/rest_v1/page/summary/Python
  ```

### Grokipedia shows "0 articles available"

Note: As of November 2025, Grokipedia is still in early development (v0.1). Some articles may not be available yet, even though the platform was reported to have 800k+ articles at launch.

## Development

To run locally without Docker:

```bash
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
python proxy.py
```

## License

MIT
