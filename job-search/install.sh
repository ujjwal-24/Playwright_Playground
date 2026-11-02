#!/usr/bin/env bash
set -euo pipefail
cd /workspace/job-apply-mcp
python3 -m venv .venv
.venv/bin/python -m pip install -r /workspace/Playwright_Playground/job-search/requirements.lock
.venv/bin/python -m pip check
.venv/bin/python -c 'from mcp.server.fastmcp import FastMCP; from playwright.async_api import async_playwright'
test -x /usr/bin/chromium
