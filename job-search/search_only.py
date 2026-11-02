"""Read-only adapter. Does not import or expose any application automation."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import urlencode, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, '/workspace/job-apply-mcp')
from tools.profile import CandidateProfile, compute_match_score, _normalize, _fuzzy_ratio
from playwright.async_api import async_playwright

SETTINGS = json.loads((ROOT / 'profile.json').read_text())
PROFILE = CandidateProfile(
    title='Performance Test Engineer', experience_years=5.5,
    location='', preferred_locations=('Noida', 'Gurugram', 'Gurgaon'),
    skills=('JMeter', 'BlazeMeter', 'LoadRunner'),
    target_roles=('Performance Test Engineer', 'Performance Testing Engineer',
                  'Performance Tester', 'Performance Engineer', 'Load Test Engineer'),
    default_search_keywords=('Performance Testing', 'JMeter', 'BlazeMeter', 'LoadRunner'),
    title_must_contain=('performance', 'load test', 'jmeter', 'blazemeter', 'loadrunner'),
    avoid_keywords=(),
)
ALIASES = {'apache jmeter': 'jmeter', 'blaze meter': 'blazemeter',
           'load runner': 'loadrunner', 'micro focus loadrunner': 'loadrunner',
           'opentext loadrunner': 'loadrunner', 'hp loadrunner': 'loadrunner'}

def canonical(text):
    text = _normalize(text)
    for old, new in sorted(ALIASES.items(), key=lambda x: -len(x[0])):
        text = text.replace(old, new)
    return text

def screening_answer(question):
    answer = SETTINGS['confirmed_screening_answers'].get(question)
    if answer is None:
        return {'status': 'needs_user_answer', 'question': question,
                'answer': None, 'submission_allowed': False}
    return {'status': 'confirmed', 'question': question, 'answer': answer,
            'submission_allowed': False}

def rank_jobs(jobs):
    ranked, seen = [], set()
    for raw in jobs:
        j = dict(raw)
        url = j.get('apply_url', '')
        u = urlsplit(url)
        if u.scheme != 'https' or not u.netloc:
            continue
        key = urlunsplit((u.scheme, u.netloc.lower(), u.path.rstrip('/'), '', ''))
        if key in seen:
            continue
        seen.add(key)
        title = canonical(j.get('title', ''))
        if not any(k in title for k in PROFILE.title_must_contain):
            continue
        desc = canonical(j.get('description', ''))
        required = sorted({canonical(s) for s in j.get('required_skills', []) if s.strip()})
        targets = {canonical(s) for s in PROFILE.skills}
        evidence = title + ' ' + desc + ' ' + ' '.join(required)
        matched = sorted(s for s in targets if re.search(r'\b' + re.escape(s) + r'\b', evidence))
        loc = j.get('location', '')
        local = any(re.search(r'\b' + p + r'\b', loc.lower()) for p in ('noida', 'gurugram', 'gurgaon'))
        role = max(1.0 if _normalize(r) in title else _fuzzy_ratio(_normalize(r), title)
                   for r in PROFILE.target_roles)
        skill = len(set(required) & targets) / len(required) if required else min(len(matched) / max(len(targets)*.3, 1), 1)
        # Upstream awards location points to any remote/India job too. Preserve it,
        # and prioritize Noida/Gurugram separately instead of mislabelling its score.
        score = compute_match_score(title, desc, loc, required or None, PROFILE)
        location_points = round(score - .35*role - .40*skill, 3)
        ranked.append({**j, 'match_score': score, 'score_maximum': .90,
            'score_components': {'role': round(.35*role, 3), 'skills': round(.40*skill, 3),
                                 'location': location_points, 'avoid_penalty': 0},
            'preferred_city': local, 'matching_target_skills': matched,
            'target_skills_not_evidenced': sorted(targets-set(matched)),
            'additional_requirements_to_verify': sorted(set(required)-targets),
            'experience_eligibility': 'unverified; total experience 5.5 years; per-tool years unknown',
            'personal_skill_gaps': 'unverified; target tools are search criteria, not confirmed proficiency',
            'score_basis': 'upstream weights; alias-normalized required tags when present, otherwise text fallback',
            'description_complete': j.get('description_complete', False)})
    return sorted(ranked, key=lambda j: (not j['preferred_city'], -j['match_score']))

async def search_jobs(browser_name='chromium', keywords=None, locations=None):
    """Sequential public Naukri searches; GET requests only, no apply/login actions."""
    keywords = keywords or ['Performance Testing JMeter', 'Performance Testing BlazeMeter', 'Performance Testing LoadRunner']
    locations = locations or ['Noida', 'Gurugram']
    jobs, diagnostics = [], []
    async with async_playwright() as pw:
        launch = {'headless': True}
        if os.environ.get('HTTPS_PROXY'):
            launch['proxy'] = {'server': os.environ['HTTPS_PROXY']}
        if browser_name == 'chromium':
            launch['executable_path'] = '/usr/bin/chromium'
        browser = await getattr(pw, browser_name).launch(**launch)
        context = await browser.new_context(ignore_https_errors=False, locale='en-IN')
        async def readonly(route):
            if route.request.method not in ('GET', 'HEAD', 'OPTIONS'):
                await route.abort()
            else:
                await route.continue_()
        await context.route('**/*', readonly)
        try:
            for location in locations:
                for keyword in keywords:
                    # Do not turn 5.5 into an incorrect 5-7 minimum/maximum filter.
                    slug = keyword.lower().replace(' ', '-')
                    url = f'https://www.naukri.com/{slug}-jobs-in-{location.lower()}'
                    page = await context.new_page()
                    payloads, pending, crashes = [], [], []
                    page.on('crash', lambda _: crashes.append('page_crash'))
                    async def capture(response):
                        if 'jobapi/v3/search' in response.url:
                            try:
                                data = await response.json()
                                payloads.extend(data.get('jobDetails', []))
                            except Exception:
                                pass
                    def received(response):
                        pending.append(asyncio.create_task(capture(response)))
                    page.on('response', received)
                    try:
                        response = await page.goto(url, wait_until='domcontentloaded', timeout=45000)
                        await page.wait_for_timeout(5000)
                        if pending:
                            await asyncio.gather(*pending)
                        text = (await page.inner_text('body')).lower()
                        status = response.status if response else None
                        error = ('HTTP '+str(status)) if status and status >= 400 else None
                        if not payloads:
                            error = error or ('challenge_or_access_denied' if any(x in text for x in ['captcha', 'access denied', 'verify you are human']) else 'no_job_payload; not verified empty results')
                        diagnostics.append({'url': url, 'http_status': status, 'jobs_received': len(payloads), 'error': error, 'crashes': crashes})
                        for item in payloads:
                            jd = item.get('jdURL', '')
                            if jd.startswith('/'):
                                jd = 'https://www.naukri.com'+jd
                            tags = [s.strip() for s in item.get('tagsAndSkills', '').split(',') if s.strip()]
                            loc = next((p.get('label', '') for p in item.get('placeholders', []) if p.get('type') == 'location'), '')
                            jobs.append({'title': item.get('title', ''), 'company': item.get('companyName', ''),
                                'location': loc, 'apply_url': jd, 'platform': 'naukri',
                                'description': item.get('jobDescription', ''), 'required_skills': tags,
                                'description_complete': False, 'experience_requirements': item.get('experience', 'unverified')})
                    except Exception as exc:
                        diagnostics.append({'url': url, 'error': str(exc), 'crashes': crashes})
                    finally:
                        if not page.is_closed():
                            await page.close()
        finally:
            await context.close()
            await browser.close()
    return {'mode': 'search-only', 'jobs': rank_jobs(jobs), 'diagnostics': diagnostics,
            'applications_submitted': 0}

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--browser', choices=['chromium','firefox'], default='chromium')
    parser.add_argument('--input', type=Path, help='Rank previously captured job JSON without network access')
    args = parser.parse_args()
    result = {'jobs': rank_jobs(json.loads(args.input.read_text()))} if args.input else asyncio.run(search_jobs(args.browser))
    (ROOT / 'results.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    if not args.input and not result['jobs'] and any(d.get('error') for d in result['diagnostics']):
        raise SystemExit(2)  # blocked search must not look like a successful empty search
