# Performance Testing job search

Search-only tools targeting JMeter, BlazeMeter, and LoadRunner roles, prioritizing Noida and Gurugram. Total experience: 5.5 years; individual tool experience remains unverified. No applications are submitted. Unknown screening questions pause for an answer.

See [setup and usage](job-search/README.md) and [live search status](job-search/JOBS.md). Live searches were blocked by the environment network policy during setup; no verified job shortlist is available yet.

The Python tools use a separate clone of [pulkit017/job-apply-mcp](https://github.com/pulkit017/job-apply-mcp) at `/workspace/job-apply-mcp` (inspected commit `606d5060af600c5b976effc714574a2d7385ee77`). That clone is a dependency, not this repository's remote.

## Setup in the cloud workspace

If the dependency checkout is missing, clone it:

```sh
git clone https://github.com/pulkit017/job-apply-mcp.git /workspace/job-apply-mcp
git -C /workspace/job-apply-mcp checkout 606d5060af600c5b976effc714574a2d7385ee77
```

Then run:

```sh
bash /workspace/Playwright_Playground/job-search/install.sh
/workspace/job-apply-mcp/.venv/bin/python /workspace/Playwright_Playground/job-search/validate.py
/workspace/job-apply-mcp/.venv/bin/python /workspace/Playwright_Playground/job-search/search_only.py
```

The workspace must provide `/usr/bin/chromium`. Search mode keeps TLS verification enabled, uses the configured proxy, and exposes no application tools. Local adaptations live in this repository; upstream tracked files remain unchanged.
