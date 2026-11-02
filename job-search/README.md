# Performance Testing search-only workspace

Inspected upstream commit: `606d5060af600c5b976effc714574a2d7385ee77`.
Upstream tracked files are unchanged. Local adaptation lives in `/workspace/Playwright_Playground/job-search`.

## Use

Run from `/workspace/Playwright_Playground/job-search`:

```sh
/workspace/job-apply-mcp/.venv/bin/python search_only.py
```

This searches public Naukri listings sequentially for Performance Testing with
JMeter, BlazeMeter, and LoadRunner, in Noida then Gurugram. It writes `results.json`.
Exit 2 means all searches were blocked or failed, not a successful empty search.
Searches currently have no verified recency filter or per-tool experience eligibility
filter. Raw descriptions may be snippets; `description_complete=false` makes this explicit.
Noida/Gurugram/Gurgaon listings rank ahead of other locations, then by raw score.
Results include matching target tools, missing evidence, additional requirements to
verify, direct job URLs, and component scores. Missing evidence does not prove a personal gap.

Total experience is user-confirmed as **5.5 years**. Individual tool experience,
other skills, salary, notice, residence, and willingness answers are unknown.
`profile.json` stores search targets, not claims of proficiency. Add only confirmed
screening answers using the exact question text. The screening tool returns
`needs_user_answer` and `answer=null` for every unconfirmed question, including
willingness/relocation questions. It does not infer Yes, No, age, salary, or years.
There is no application or resume-upload capability in this adapter.

For an MCP client, use `mcp-client.json`. This file is a configuration snippet;
it has not been installed into the current chat's tool catalogue. Start the server
with `/workspace/job-apply-mcp/.venv/bin/python /workspace/Playwright_Playground/job-search/mcp_search_only.py`.
Only `search_jobs`, `rank_jobs`, and `screening_answer` are exposed.
Do not launch upstream `server.py`, `run.py`, or `_apply_fresh.py`: they retain
application functionality and unsafe default screening answers. The upstream
application code has deliberately not been patched during environment onboarding.

## Accurate scores

Original formula in `tools/profile.py`:
`max(0, 0.35*role + 0.40*skill + 0.15*location - 0.10*avoid)` (rounded to 3 decimals).
The positive weights total **0.90**. The clamp to 1.0 does not change that maximum.
This is relevance, not confidence, hiring probability, or verified eligibility.
0.70 means 0.70 raw, or 77.8% of the attainable 0.90; it does not mean a 70% chance.

Role: best substring/fuzzy match against target roles.
Skills with explicit tags: fraction of listed tags exactly matching normalized
profile skills. The adapter normalizes tool aliases before passing them to the
original scorer. Job tag requirements outside the three target tools are
unverified requirements, not automatically proven skill gaps.
Skills without tags: upstream counts profile skills found as substrings in title
and description, divided by `max(skill_count*0.3, 1)`, capped at 1. With THREE
profile skills this gives full skill points for ONE mentioned tool. Consequently
a perfect title, preferred location and only JMeter in text can already score
0.90. Always inspect matching skills, requirements, and description completeness.
Location: upstream gives full points for preferred-city substrings, Remote, or
India. It does not distinguish Noida from India-wide listings. The adapter keeps
these weights but applies preferred-city priority separately.
Avoid: any configured avoidance term triggers a 0.10 deduction. The local target
profile has no avoidance terms because the user did not specify exclusions.
The original hard title gate and `should_exclude` are separate from the numeric
score. The adapter replaces the DevOps title gate with Performance/Load/tool titles.

## Firefox crash investigation

No logs, Firefox profiles, or crash dumps from the prior search were available in
this workspace. The prior crash's cause remains unconfirmed.

Current observations:
- No DISPLAY; upstream hard-codes `headless=False`. That is incompatible with this
  headless workspace without a display server, but is not proof of the previous tab crash.
- Firefox browser build absent; installation attempted with Playwright 1.64.1.
  Both `cdn.playwright.dev` and `playwright.download.prss.microsoft.com` returned
  explicit `403 Domain forbidden`. No downloaded artifact was used.
- Naukri and LinkedIn HTTPS CONNECT probes returned 403. Six actual headless
  Chromium searches failed with `ERR_TUNNEL_CONNECTION_FAILED`; no page-crash
  events were emitted. These are network failures, not observed browser crashes.
- Available memory approximately 33 GiB; /dev/shm approximately 17 GiB. No evidence
  of current memory pressure; previous OOM cannot be assessed without prior logs.
- Chromium local DOM rendering and MCP integration checks passed.
- Upstream disables TLS checks in browser contexts and shares one context across
  concurrently scraped sites. This adapter keeps TLS verification, explicitly uses
  the inherited proxy, runs one public search at a time, and records crash events.
- Upstream broad exception handling can convert scraper errors into empty results.
  This adapter records per-query errors and distinguishes blocked from empty.

After network settings are saved/applied, rerun the search first. If Firefox
comparison is required, install its matched build with:

```sh
PLAYWRIGHT_BROWSERS_PATH=/workspace/Playwright_Playground/job-search/browsers /workspace/job-apply-mcp/.venv/bin/python -m playwright install firefox
PLAYWRIGHT_BROWSERS_PATH=/workspace/Playwright_Playground/job-search/browsers /workspace/job-apply-mcp/.venv/bin/python /workspace/Playwright_Playground/job-search/search_only.py --browser firefox
```

Keep TLS and browser sandbox verification enabled. Compare one identical query
in both browsers and retain event/error output before assigning a crash cause.
Do not bypass CAPTCHAs, proxy denials, or sign in automatically.

## Validation and saved setup

`install.sh` reuses the checkout and installs the exact versions from
`requirements.lock`. Upstream `mcp>=1` initially installed MCP 2.3.0, whose
FastMCP API is incompatible; the tested environment uses MCP 1.30.0.
`pip check` and repeat installation passed.

Run `/workspace/job-apply-mcp/.venv/bin/python /workspace/Playwright_Playground/job-search/validate.py`.
It validates synthetic scores (not real jobs), aliases, city ordering, deduplication,
title gating, question pause, Chromium rendering, MCP initialization/tool calls,
and rejection of the unavailable apply tool. All checks passed.

The browser and dependencies are retained on disk; no web server must remain live.
Each task is already isolated. Use these existing checkouts; do not create a Git
worktree unless explicitly requested.
