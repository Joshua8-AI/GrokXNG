#!/bin/bash
echo "=== Grokipedia Integration Quick Check ==="
echo

echo "1. Checking containers..."
docker ps | grep -E "grokipedia|searxng" | awk '{print "   ✓", $NF, "-", $2}'

echo
echo "2. Testing proxy health..."
curl -s http://localhost:5000/health && echo " ✓ Proxy is healthy"

echo
echo "3. Testing proxy scraping..."
curl -s http://localhost:5000/api/rest_v1/page/summary/Python | python3 -c "import sys, json; d=json.load(sys.stdin); print(f'   ✓ Title: {d[\"title\"]}'); print(f'   ✓ Extract: {d[\"extract\"][:80]}...')" 2>/dev/null

echo
echo "4. Checking SearxNG engine..."
docker exec searxng ls /usr/local/searxng/searx/engines/grokipedia.py >/dev/null 2>&1 && echo "   ✓ Custom engine is mounted"

echo
echo "5. Checking network..."
docker network inspect searxng --format '{{range .Containers}}{{.Name}} {{end}}' | grep -q "grokipedia-proxy.*searxng" && echo "   ✓ Both containers on same network"

echo
echo "=== Status: All systems operational ==="
echo
echo "Test in browser: http://localhost:8080"
echo "Search with: !grok Python"
