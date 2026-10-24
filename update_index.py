#!/usr/bin/env python3
"""Generate a searchable HTML index for public GitHub repositories and Netlify sites."""
import json, os, urllib.request, urllib.parse, html
from datetime import datetime, timezone

OWNER = os.getenv('GITHUB_OWNER', 'DatWins')
GH_TOKEN = os.getenv('GH_TOKEN') or os.getenv('GITHUB_TOKEN', '')
NETLIFY_TOKEN = os.getenv('NETLIFY_AUTH_TOKEN', '')


def get_json(url, token=None):
    headers = {'Accept': 'application/json', 'User-Agent': 'datwins-repository-index/1.0'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def github_repos():
    repos, page = [], 1
    while True:
        url = f'https://api.github.com/users/{urllib.parse.quote(OWNER)}/repos?type=public&per_page=100&page={page}&sort=full_name'
        batch = get_json(url, GH_TOKEN or None)
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return repos


def clean_repo_url(value):
    if not value:
        return ''
    value = str(value).strip()
    if value.endswith('.git'):
        value = value[:-4]
    if value.startswith('git@github.com:'):
        value = 'https://github.com/' + value.split(':', 1)[1]
    return value.rstrip('/')


def netlify_sites():
    if not NETLIFY_TOKEN:
        print('NETLIFY_AUTH_TOKEN not set; building GitHub-only index.')
        return []
    sites, page = [], 1
    while True:
        url = f'https://api.netlify.com/api/v1/sites?per_page=100&page={page}'
        batch = get_json(url, NETLIFY_TOKEN)
        if isinstance(batch, dict):
            batch = batch.get('sites', [])
        if not batch:
            break
        sites.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return sites


def get_netlify_repo(site):
    candidates = [
        site.get('repo_url'), site.get('repository_url'), site.get('repo', {}).get('url') if isinstance(site.get('repo'), dict) else None,
        site.get('repo', {}).get('repository_url') if isinstance(site.get('repo'), dict) else None,
        site.get('build_settings', {}).get('repo_url'), site.get('build_settings', {}).get('repo_path')
    ]
    for item in candidates:
        url = clean_repo_url(item)
        if url:
            # Netlify's repo_path may be just owner/repo without a scheme.
            if not url.startswith('http') and '/' in url and 'github.com' not in url:
                url = 'https://github.com/' + url.lstrip('/')
            if 'github.com/' in url:
                return url
    return ''


def make_entries(repos, sites):
    by_repo = {}
    extra_sites = []
    owner_prefix = f'https://github.com/{OWNER.lower()}/'
    for s in sites:
        repo_url = get_netlify_repo(s)
        site_url = s.get('ssl_url') or s.get('url') or ''
        if site_url and site_url.startswith('//'):
            site_url = 'https:' + site_url
        if site_url and not site_url.startswith('http'):
            site_url = 'https://' + site_url
        if repo_url:
            key = repo_url.lower().rstrip('/')
            record = {'project': s.get('name') or s.get('custom_domain') or 'Netlify site', 'url': site_url, 'repo_url': repo_url}
            by_repo.setdefault(key, []).append(record)
            if not key.startswith(owner_prefix):
                extra_sites.append({'name': record['project'], 'full_name': repo_url.removeprefix('https://github.com/'), 'repo_url': repo_url, 'site_url': site_url, 'site_type': 'Netlify site', 'pages_enabled': False, 'netlify': [record], 'classification': 'Netlify repository outside owner', 'archived': False, 'private': False})
        else:
            extra_sites.append({'name': s.get('name') or 'Netlify site', 'full_name': 'Repository not reported by Netlify API', 'repo_url': '', 'site_url': site_url, 'site_type': 'Netlify site', 'pages_enabled': False, 'netlify': [{'project': s.get('name') or 'Netlify site', 'url': site_url, 'repo_url': ''}], 'classification': 'Netlify repository not identified', 'archived': False, 'private': False})

    entries = []
    for r in repos:
        full = r.get('full_name', f"{OWNER}/{r['name']}")
        repo_url = r.get('html_url', f'https://github.com/{full}')
        linked = by_repo.get(repo_url.lower().rstrip('/'), [])
        pages = bool(r.get('has_pages'))
        homepage = (r.get('homepage') or '').strip()
        if homepage and homepage.startswith('http'):
            site_url, site_type = homepage, 'Homepage URL'
        elif pages:
            if r['name'].lower() == f'{OWNER}.github.io'.lower():
                site_url = f'https://{OWNER.lower()}.github.io/'
            else:
                site_url = f'https://{OWNER.lower()}.github.io/{r["name"]}/'
            site_type = 'Likely GitHub Pages URL'
        elif linked:
            site_url, site_type = linked[0].get('url', ''), 'Netlify'
        else:
            site_url, site_type = '', ''
        classification = 'Both' if linked and pages else ('Netlify' if linked else ('GitHub Pages' if pages else 'Neither identified'))
        entries.append({'name': r['name'], 'full_name': full, 'repo_url': repo_url, 'site_url': site_url, 'site_type': site_type,
                        'pages_enabled': pages, 'netlify': linked, 'classification': classification,
                        'archived': bool(r.get('archived')), 'private': bool(r.get('private'))})
    entries.extend(extra_sites)
    entries.sort(key=lambda x: (x['name'] or '').lower())
    return entries


def build_html(entries):
    data = json.dumps(entries, ensure_ascii=False).replace('</', '<\\/')
    updated = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    return r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>DatWins — Repository & Website Index</title>
<style>
:root{color-scheme:light dark;--bg:#f5f7fb;--panel:#fff;--ink:#172033;--muted:#657087;--line:#dce2ec;--accent:#2858c5;--tag:#e8eefc;--shadow:0 8px 24px rgba(30,50,90,.07)}
@media(prefers-color-scheme:dark){:root{--bg:#101522;--panel:#171e2d;--ink:#edf2ff;--muted:#a8b3c9;--line:#303a4d;--accent:#9bb7ff;--tag:#253452;--shadow:0 8px 24px rgba(0,0,0,.15)}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif}header{padding:32px 20px 25px;background:linear-gradient(135deg,#172b52,#315eb2);color:white}header .wrap,main{max-width:1200px;margin:auto}h1{font-size:clamp(1.8rem,4vw,2.7rem);margin:0 0 8px;letter-spacing:-.03em}.wrap{padding:0 20px}.stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:20px 0}.stat,.controls,.card{background:var(--panel);border:1px solid var(--line);border-radius:15px;box-shadow:var(--shadow)}.stat{padding:14px 16px}.stat strong{display:block;font-size:1.7rem}.stat span{color:var(--muted);font-size:.88rem}.controls{padding:14px;display:grid;grid-template-columns:minmax(220px,1fr) 240px 180px;gap:10px;margin-bottom:16px}input,select{width:100%;font:inherit;color:var(--ink);background:var(--panel);border:1px solid var(--line);border-radius:9px;padding:11px 12px}.count{color:var(--muted);font-size:.92rem;margin:0 0 12px}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;padding-bottom:36px}.card{padding:17px;display:flex;flex-direction:column;gap:10px;min-width:0}.titleline{display:flex;align-items:flex-start;justify-content:space-between;gap:10px}.card h2{font-size:1.05rem;line-height:1.3;margin:0;overflow-wrap:anywhere}.badge{font-size:.73rem;white-space:nowrap;padding:4px 8px;border-radius:999px;background:var(--tag);color:var(--accent);font-weight:700}.sub{font-size:.87rem;color:var(--muted);overflow-wrap:anywhere}.links{display:flex;flex-wrap:wrap;gap:8px;margin-top:auto;padding-top:3px}a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}.link{border:1px solid var(--line);border-radius:8px;padding:7px 10px;font-size:.88rem;font-weight:650}.primary{background:var(--tag)}.notice{font-size:.82rem;color:var(--muted);margin:0}.empty{grid-column:1/-1;text-align:center;padding:50px 20px;color:var(--muted)}footer{max-width:1200px;margin:auto;padding:0 20px 30px;color:var(--muted);font-size:.84rem}@media(max-width:900px){.grid{grid-template-columns:repeat(2,minmax(0,1fr))}.controls{grid-template-columns:1fr 1fr}.controls input{grid-column:1/-1}}@media(max-width:580px){.stats{grid-template-columns:repeat(2,minmax(0,1fr))}.grid{grid-template-columns:1fr}.controls{grid-template-columns:1fr}.controls input{grid-column:auto}}
</style></head><body><header><div class="wrap"><h1>DatWins Repository & Website Index</h1><p>Automatically refreshed directory of public GitHub repositories and available Netlify/GitHub Pages website links.</p></div></header>
<main class="wrap"><section class="stats" id="stats"></section><section class="controls" aria-label="Search and filters"><input id="search" type="search" placeholder="Search repository, project, or URL…" aria-label="Search repositories"><select id="category" aria-label="Filter by hosting"><option value="all">All entries</option><option value="Netlify">Netlify-connected</option><option value="GitHub Pages">GitHub Pages enabled</option><option value="Both">Both Netlify & Pages</option><option value="Neither identified">Neither hosting method identified</option><option value="Netlify repository not identified">Netlify repository not identified</option><option value="Netlify repository outside owner">Netlify repository outside owner</option></select><select id="sort" aria-label="Sort entries"><option value="name">Sort: Name A–Z</option><option value="category">Sort: Hosting category</option></select></section><p class="count" id="count"></p><section class="grid" id="grid" aria-live="polite"></section></main><footer>Updated: __UPDATED__. Public GitHub repositories are fetched from the GitHub API. Netlify connections are included when NETLIFY_AUTH_TOKEN is configured in repository secrets. “Likely GitHub Pages URL” follows the standard URL pattern and should be verified before relying on it. “Neither hosting method identified” does not prove that no website exists.</footer>
<script>
const entries=__DATA__;
const $=id=>document.getElementById(id);const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const counts={repos:entries.filter(e=>e.repo_url&&e.full_name.includes('/')).length,netlify:entries.filter(e=>e.netlify?.length).length,pages:entries.filter(e=>e.pages_enabled).length,extras:entries.filter(e=>!e.repo_url||e.classification==='Netlify repository outside owner').length};
$('stats').innerHTML=[['Index entries',entries.length],['Netlify-linked entries',counts.netlify],['Pages-enabled repositories',counts.pages],['Other Netlify entries',counts.extras]].map(([l,n])=>`<div class="stat"><strong>${n}</strong><span>${l}</span></div>`).join('');
function card(e){let site=e.site_url?`<a class="link primary" href="${esc(e.site_url)}" target="_blank" rel="noopener noreferrer">${e.site_type==='Likely GitHub Pages URL'?'Open likely site':'Open website'} ↗</a>`:'';let repo=e.repo_url?`<a class="link" href="${esc(e.repo_url)}" target="_blank" rel="noopener noreferrer">GitHub repository ↗</a>`:'';let projects=(e.netlify||[]).map(n=>`<div class="sub">Netlify project: <strong>${esc(n.project)}</strong>${n.url?` · <a href="${esc(n.url)}" target="_blank" rel="noopener noreferrer">Open Netlify site ↗</a>`:''}</div>`).join('');let note=e.site_type==='Likely GitHub Pages URL'?'<p class="notice">Likely Pages URL — generated from the standard URL pattern, not independently verified.</p>':'';return `<article class="card"><div class="titleline"><h2>${esc(e.name)}</h2><span class="badge">${esc(e.classification)}</span></div><div class="sub">${esc(e.full_name)}</div>${projects}${e.pages_enabled?'<div class="sub">GitHub Pages: enabled</div>':''}${e.archived?'<div class="sub">Archived repository</div>':''}${note}<div class="links">${site}${repo}</div></article>`}
function render(){let q=$('search').value.trim().toLowerCase(),cat=$('category').value,sort=$('sort').value;let list=entries.filter(e=>{let text=[e.name,e.full_name,e.repo_url,e.site_url,e.classification,...(e.netlify||[]).map(n=>n.project)].join(' ').toLowerCase();return (cat==='all'||e.classification===cat)&&text.includes(q)});list.sort((a,b)=>sort==='category'?(a.classification.localeCompare(b.classification)||a.name.localeCompare(b.name)):a.name.localeCompare(b.name));$('count').textContent=`Showing ${list.length} of ${entries.length} entries`;$('grid').innerHTML=list.length?list.map(card).join(''):'<div class="empty">No matching entries. Try another search or filter.</div>'}
['search','category','sort'].forEach(id=>$(id).addEventListener(id==='search'?'input':'change',render));render();
</script></body></html>'''.replace('__DATA__', data).replace('__UPDATED__', updated)


def main():
    repos = github_repos()
    sites = netlify_sites()
    entries = make_entries(repos, sites)
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(build_html(entries))
    print(f'Wrote index.html with {len(entries)} entries ({len(repos)} public GitHub repositories, {len(sites)} Netlify sites scanned).')

if __name__ == '__main__':
    main()
