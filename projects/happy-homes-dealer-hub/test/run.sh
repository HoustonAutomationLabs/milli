#!/usr/bin/env bash
# Runs both suites. Requires node and (for the UI suite) playwright + chromium.
set -e
cd "$(dirname "$0")"

echo "== data layer =="
node extract-core.js
node data.test.js

echo
echo "== browser =="
mkdir -p .serve
cp ../index.html .serve/index.html
cp feed.sample.json .serve/feed.json
# point the test copy at the local fixture instead of the live Apps Script
node -e "
const fs=require('fs'),p='.serve/index.html';
let s=fs.readFileSync(p,'utf8');
s=s.replace(/feedUrl: \".*?\"/, 'feedUrl: \"./feed.json\"');
fs.writeFileSync(p,s);"
python3 -m http.server 8899 --directory .serve >/dev/null 2>&1 &
SERVER=$!
cleanup() { kill "$SERVER" >/dev/null 2>&1 || true; wait "$SERVER" 2>/dev/null || true; }
trap cleanup EXIT
sleep 1

set +e
node ui.test.js
STATUS=$?
set -e
cleanup
trap - EXIT
exit $STATUS
