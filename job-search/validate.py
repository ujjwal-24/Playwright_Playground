"""Synthetic validation only. Fixtures are not real job listings."""
import asyncio
import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from playwright.async_api import async_playwright
from search_only import rank_jobs, screening_answer, PROFILE
from tools.profile import compute_match_score

async def main():
    jobs = [
      {'title':'Performance Test Engineer', 'company':'TEST FIXTURE', 'location':'Noida',
       'required_skills':['Apache JMeter', 'BlazeMeter', 'Load Runner'], 'apply_url':'https://example.com/jobs/1'},
      {'title':'Performance Test Engineer', 'location':'Pune', 'required_skills':['JMeter'], 'apply_url':'https://example.com/jobs/2'},
      {'title':'Performance Test Engineer', 'location':'Gurgaon', 'required_skills':['JMeter', 'Java'], 'apply_url':'https://example.com/jobs/3'},
      {'title':'DevOps Engineer', 'location':'Noida', 'apply_url':'https://example.com/jobs/4'},
    ]
    ranked = rank_jobs(jobs + [dict(jobs[0], apply_url='https://example.com/jobs/1?tracking=foo')])
    assert len(ranked) == 3
    assert ranked[0]['match_score'] == .9
    assert ranked[0]['matching_target_skills'] == ['blazemeter', 'jmeter', 'loadrunner']
    assert ranked[1]['location'] == 'Gurgaon'
    assert ranked[1]['additional_requirements_to_verify'] == ['java']
    assert ranked[1]['match_score'] == .7
    # The original fallback saturates with one skill for a three-skill profile.
    assert compute_match_score('Performance Test Engineer','JMeter','Noida',profile=PROFILE) == .9
    assert screening_answer('Are you willing to relocate?')['status'] == 'needs_user_answer'
    assert screening_answer('Unknown question')['answer'] is None
    print('PASS ranking, aliases, preferred cities, dedup, title gate, exact 0.90/0.70 scores, screening pause')
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, executable_path='/usr/bin/chromium')
        page = await browser.new_page(ignore_https_errors=False)
        await page.set_content('<h1>Performance Testing</h1><p>JMeter BlazeMeter LoadRunner</p>')
        assert await page.locator('h1').inner_text() == 'Performance Testing'
        await browser.close()
    print('PASS actual headless Chromium launch and DOM extraction')
    params = StdioServerParameters(command=sys.executable, args=[str(Path(__file__).with_name('mcp_search_only.py'))])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            assert {t.name for t in tools.tools} == {'search_jobs','rank_jobs','screening_answer'}
            result = await session.call_tool('screening_answer', {'question':'Unknown screening question'})
            assert 'needs_user_answer' in result.content[0].text
            assert not result.isError
            blocked = await session.call_tool('apply_job', {'job_url':'https://example.com'})
            assert blocked.isError
    print('PASS MCP handshake, search-only tool catalogue, question pause, rejected apply tool')

asyncio.run(main())
