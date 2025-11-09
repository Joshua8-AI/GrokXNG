# SearxNG Setup Guide

This guide explains how to configure your SearxNG instance to use the Grokipedia proxy.

## Overview

The Grokipedia integration requires **configuration changes only** - no SearxNG source code modifications. You'll be:
1. Mounting the custom engine file into the SearxNG container
2. Adding engine configuration to settings.yml
3. Enabling HTTP for internal proxy communication

## Prerequisites

- SearxNG running in Docker (official image: `searxng/searxng:latest`)
- SearxNG and Grokipedia proxy on the same Docker network
- This assumes your SearxNG directory structure is:
  ```
  searxng/
  ├── docker-compose.yml
  └── searx/
      └── settings.yml
  ```

## Step 1: Network Setup

Both containers must be on the same Docker network for communication.

### Option A: Add Grokipedia proxy to existing SearxNG network

In the Grokipedia proxy `docker-compose.yml` (already configured):
```yaml
networks:
  searxng-network:
    external: true
    name: searxng  # Must match your SearxNG network name
```

### Option B: Create a shared network

```bash
# Create network if it doesn't exist
docker network create searxng

# Update both docker-compose.yml files to use this network
```

## Step 2: Modify SearxNG docker-compose.yml

Add a volume mount to load the custom Grokipedia engine into the SearxNG container.

**Location:** `searxng/docker-compose.yml`

### Before:
```yaml
services:
  searxng:
    container_name: searxng
    image: searxng/searxng:latest
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - ./searx:/etc/searxng:rw
    networks:
      - searxng
```

### After:
```yaml
services:
  searxng:
    container_name: searxng
    image: searxng/searxng:latest
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - ./searx:/etc/searxng:rw
      - ../seargrok/grokipedia.py:/usr/local/searxng/searx/engines/grokipedia.py:ro  # ADD THIS LINE
    networks:
      - searxng

networks:
  searxng:
    external: false
```

**Important notes:**
- The path `../seargrok/grokipedia.py` assumes the directory structure is:
  ```
  parent-directory/
  ├── searxng/
  └── seargrok/
  ```
- Adjust the path if your directories are in different locations
- The `:ro` flag makes it read-only (recommended)

## Step 3: Modify SearxNG settings.yml

Add the Grokipedia engine configuration and enable HTTP for internal communication.

**Location:** `searxng/searx/settings.yml`

### Change 1: Add Grokipedia Engine

Find the `engines:` section (around line 500-600) and add this **before** the Wikipedia engine entry:

```yaml
engines:
  # ... other engines ...

  - name: grokipedia
    engine: grokipedia
    shortcut: grok
    base_url: http://grokipedia-proxy:5000
    enable_http: true
    display_type: ["infobox", "list"]
    categories: [general]

  - name: wikipedia
    engine: wikipedia
    # ... rest of wikipedia config ...
```

**Configuration explained:**
- `name: grokipedia` - Engine name shown in SearxNG
- `engine: grokipedia` - References the `grokipedia.py` file we mounted
- `shortcut: grok` - Allows searches with `!grok query`
- `base_url: http://grokipedia-proxy:5000` - Internal Docker network address
- `enable_http: true` - Required for HTTP communication (proxy doesn't use HTTPS)
- `display_type: ["infobox", "list"]` - Shows results in both infobox and result list
- `categories: [general]` - Appears in general searches

**Priority:** Placing Grokipedia **before** Wikipedia gives it higher priority in search results.

### Change 2: Enable HTTP in Outgoing Settings

Find the `outgoing:` section (around line 180-200) and add `enable_http: true`:

```yaml
outgoing:
  request_timeout: 8.0
  max_request_timeout: 15.0
  useragent_suffix: ""
  pool_connections: 20
  pool_maxsize: 5
  enable_http2: true
  enable_http: true  # ADD THIS LINE
```

**Why this is needed:** By default, SearxNG may restrict HTTP connections for security. Since the Grokipedia proxy runs on the internal Docker network without HTTPS, we need to enable HTTP.

### Change 3 (Optional): Set Default Locale to English

If you want to force English language for the UI:

```yaml
ui:
  default_locale: "en"  # Change from "" to "en"
```

## Step 4: Start/Restart Services

### Start the Grokipedia Proxy

```bash
# From the seargrok directory
cd seargrok
docker-compose up -d --build
```

### Verify Proxy is Running

```bash
# Health check
curl http://localhost:5000/health
# Expected: {"status":"healthy"}

# Test article fetch
curl http://localhost:5000/api/rest_v1/page/summary/Python
# Expected: JSON response with Wikipedia-compatible format
```

### Restart SearxNG

```bash
# From the searxng directory
cd searxng
docker-compose restart searxng

# Or rebuild if needed
docker-compose up -d --build
```

### Verify Engine is Mounted

```bash
# Check the custom engine file exists in the container
docker exec searxng ls -l /usr/local/searxng/searx/engines/grokipedia.py

# Expected output:
# -r--r--r-- 1 root root 3254 Nov 8 12:00 /usr/local/searxng/searx/engines/grokipedia.py
```

## Step 5: Test the Integration

### Test 1: Check SearxNG Logs

```bash
# Watch logs for any errors
docker logs searxng -f

# Look for messages like:
# - "loaded engine grokipedia"
# - Any errors related to grokipedia
```

### Test 2: Use the Bang Shortcut

Open SearxNG at http://localhost:8080 and search:
```
!grok Python
```

You should see:
- An **infobox** at the top with Python information from Grokipedia
- A **result item** in the search results list

### Test 3: General Search

Search for:
```
Artificial intelligence
```

You should see results from multiple engines including Grokipedia (if configured before Wikipedia, it will appear first).

## Verification Checklist

- [ ] Grokipedia proxy is running: `docker ps | grep grokipedia-proxy`
- [ ] Proxy health check passes: `curl http://localhost:5000/health`
- [ ] Both containers on same network: `docker network inspect searxng`
- [ ] Custom engine file is mounted: `docker exec searxng ls /usr/local/searxng/searx/engines/grokipedia.py`
- [ ] Settings.yml has Grokipedia engine entry: `docker exec searxng grep -A 7 "name: grokipedia" /etc/searxng/settings.yml`
- [ ] HTTP is enabled: `docker exec searxng grep "enable_http: true" /etc/searxng/settings.yml`
- [ ] Bang search works: `!grok Python` shows results
- [ ] General search includes Grokipedia: Search shows Grokipedia infobox

## Troubleshooting

### Issue: "Engine grokipedia not found"

**Cause:** Custom engine file not properly mounted.

**Solution:**
```bash
# Verify file exists on host
ls -l ../seargrok/grokipedia.py

# Check volume mount in SearxNG container
docker inspect searxng | grep grokipedia

# Restart with proper mount
docker-compose restart searxng
```

### Issue: "Connection refused" or "Cannot connect to proxy"

**Cause:** Containers not on same network or wrong proxy address.

**Solution:**
```bash
# Check both containers are on same network
docker network inspect searxng

# Verify proxy is accessible from SearxNG container
docker exec searxng wget -qO- http://grokipedia-proxy:5000/health

# Check proxy container name matches (must be 'grokipedia-proxy')
docker ps | grep grokipedia
```

### Issue: "HTTPS required" or "HTTP disabled"

**Cause:** `enable_http: true` not set in settings.yml.

**Solution:**
```bash
# Verify HTTP is enabled
docker exec searxng grep -A 10 "^outgoing:" /etc/searxng/settings.yml | grep enable_http

# If not present, add it and restart
docker-compose restart searxng
```

### Issue: No results from Grokipedia

**Cause:** Article doesn't exist on Grokipedia or HTML structure changed.

**Solution:**
```bash
# Test proxy directly
curl http://localhost:5000/api/rest_v1/page/summary/Python

# Check proxy logs
docker-compose -f ../seargrok/docker-compose.yml logs -f grokipedia-proxy

# Verify Grokipedia website is accessible
curl https://grokipedia.com/page/Python
```

### Issue: SearxNG won't start after changes

**Cause:** Syntax error in settings.yml.

**Solution:**
```bash
# Check SearxNG logs for YAML errors
docker logs searxng

# Validate YAML syntax (from host)
python3 -c "import yaml; yaml.safe_load(open('searx/settings.yml'))"

# Common issues:
# - Incorrect indentation (must use spaces, not tabs)
# - Missing colons
# - Incorrect list formatting
```

## Updating SearxNG

Since this integration uses only configuration files, you can safely update SearxNG:

```bash
cd searxng

# Pull latest official image
docker compose pull searxng

# Restart with new image
docker compose up -d searxng
```

**The Grokipedia integration will continue to work** because:
- Custom engine is volume-mounted from outside the container
- Configuration files persist in the `./searx` directory
- No source code was modified in the SearxNG image

## Updating the Custom Engine

To modify the Grokipedia engine behavior:

```bash
# 1. Edit the engine file
cd seargrok
nano grokipedia.py

# 2. Restart SearxNG to reload the engine
cd ../searxng
docker-compose restart searxng

# No rebuild needed - engine is loaded at runtime
```

## Advanced Configuration

### Customize Display Type

Edit the engine entry in settings.yml:

```yaml
# Show only in infobox
display_type: ["infobox"]

# Show only in results list
display_type: ["list"]

# Show in both (default)
display_type: ["infobox", "list"]
```

### Change Proxy URL or Port

If you run the proxy on a different port or host:

```yaml
- name: grokipedia
  engine: grokipedia
  base_url: http://your-host:your-port  # Change this
  # ... rest of config
```

### Disable Grokipedia Temporarily

Comment out or remove the engine entry:

```yaml
# - name: grokipedia
#   engine: grokipedia
#   ... etc
```

Then restart: `docker-compose restart searxng`

## Reverting the Integration

To completely remove Grokipedia from SearxNG:

### 1. Remove Engine Entry

Edit `searx/settings.yml` and delete the Grokipedia engine section (7 lines).

### 2. Remove Volume Mount

Edit `docker-compose.yml` and remove the line:
```yaml
- ../seargrok/grokipedia.py:/usr/local/searxng/searx/engines/grokipedia.py:ro
```

### 3. Restart SearxNG

```bash
docker-compose restart searxng
```

### 4. Stop Grokipedia Proxy (Optional)

```bash
cd ../seargrok
docker-compose down
```

## Support

- **Proxy Issues:** Check `seargrok/README.md` and proxy logs
- **SearxNG Issues:** Check SearxNG official documentation
- **Integration Issues:** Review this guide and troubleshooting section

## Summary

**Minimal changes required:**
1. Add 1 line to `docker-compose.yml` (volume mount)
2. Add 7 lines to `settings.yml` (engine configuration)
3. Add 1 line to `settings.yml` (enable HTTP)

**Total:** 9 lines of configuration changes, zero source code modifications.
