#!/usr/bin/env bash
# Runs both suites. Requires node and (for the UI suite) playwright + chromium.
set -e
cd "$(dirname "$0")"

echo "== data layer =="
node extract-core.js
node data.test.js

echo
echo "== netlify functions =="
node functions.test.js

echo
echo "== browser =="
# serve.js runs the real function handlers with the Apps Script call stubbed,
# so the page under test is byte-for-byte the one that ships.
node serve.js >/dev/null 2>&1 &
SERVER=$!
cleanup() { kill "$SERVER" >/dev/null 2>&1 || true; wait "$SERVER" 2>/dev/null || true; }
trap cleanup EXIT
sleep 1

set +e
node ui.test.js
STATUS=$?
if [ $STATUS -eq 0 ]; then
  echo
  echo "== orders page =="
  node orders.test.js
  STATUS=$?
fi

if [ $STATUS -eq 0 ]; then
  echo
  echo "== embedded in an auto-sizing iframe =="
  node embed.test.js
  STATUS=$?
fi
set -e
cleanup
trap - EXIT
exit $STATUS
