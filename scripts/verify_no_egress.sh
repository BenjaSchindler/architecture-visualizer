#!/usr/bin/env bash
# verify_no_egress.sh — prove a rendered diagram HTML cannot phone home.
#
# It checks for the patterns that actually cause a static HTML file to load
# something over the network, and confirms the CSP lockdown is present.
# Benign URLs inside the inlined library (license headers, the
# "http://www.w3.org/2000/svg" XML namespace literal) are NOT resource loads
# and are ignored by design — we look for loading *attributes*, not any URL.
#
# Usage:  bash verify_no_egress.sh path/to/arch.html
# Exit:   0 = PASS (self-contained, no egress)   1 = FAIL   2 = usage error
#
# Gold standard beyond this script: open the file in a browser with DevTools →
# Network tab → reload → expect 0 requests. Or open it with Wi-Fi off.

set -u
f="${1:-}"
if [ -z "$f" ] || [ ! -f "$f" ]; then
  echo "usage: bash verify_no_egress.sh path/to/arch.html" >&2
  exit 2
fi

fail=0
note() { printf '  %s\n' "$1"; }
bad()  { fail=1; printf '  ✗ %s\n' "$1"; }

echo "Zero-egress audit: $f"

# 1) CSP must be present and lock down outbound connections.
if grep -qi "Content-Security-Policy" "$f"; then
  if grep -qi "connect-src 'none'" "$f"; then
    note "✓ CSP present with connect-src 'none' (blocks fetch/XHR/WebSocket)"
  else
    bad "CSP present but missing connect-src 'none'"
  fi
else
  bad "no Content-Security-Policy meta tag"
fi

# 2) External SCRIPT/STYLE references (the classic egress vectors).
if grep -niE "<script[^>]+\bsrc[[:space:]]*=" "$f" >/dev/null; then
  bad "external <script src=...> found:"; grep -niE "<script[^>]+\bsrc[[:space:]]*=" "$f" | sed 's/^/      /'
else
  note "✓ no external <script src>"
fi
if grep -niE "<link[^>]+href[[:space:]]*=[[:space:]]*[\"']?(https?:|//)" "$f" >/dev/null; then
  bad "external <link href=...> found:"; grep -niE "<link[^>]+href[[:space:]]*=" "$f" | sed 's/^/      /'
else
  note "✓ no external <link href>"
fi

# 3) Any element loading a remote resource via src= (img/iframe/object/embed/source/media).
if grep -niE "<(img|iframe|object|embed|source|video|audio)[^>]+src[[:space:]]*=[[:space:]]*[\"']?(https?:|//)" "$f" >/dev/null; then
  bad "remote media/frame src found:"; grep -niE "<(img|iframe|object|embed|source|video|audio)[^>]+src[[:space:]]*=[[:space:]]*[\"']?(https?:|//)" "$f" | sed 's/^/      /'
else
  note "✓ no remote media/iframe src"
fi

# 4) CSS that fetches: @import or url(http...).
if grep -niE "@import|url\([[:space:]]*[\"']?(https?:|//)" "$f" >/dev/null; then
  bad "CSS @import / remote url() found:"; grep -niE "@import|url\([[:space:]]*[\"']?(https?:|//)" "$f" | sed 's/^/      /'
else
  note "✓ no CSS @import / remote url()"
fi

# 5) Informational: count raw http(s) literals (expected: only library license/namespace strings).
n=$(grep -oiE "https?://" "$f" | wc -l | tr -d ' ')
note "ℹ ${n} raw http(s) literal(s) present — expected to be library license headers / XML-namespace strings, not loads"

echo
if [ "$fail" -eq 0 ]; then
  echo "PASS — self-contained, no egress vectors. Safe to open offline."
  exit 0
else
  echo "FAIL — review the ✗ lines above before sharing this file."
  exit 1
fi
