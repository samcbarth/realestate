#!/usr/bin/env python3
"""Static build for realestate.samcbarth.com (Deal Math).

Sources (edit these, then run `python build.py`):
  site.json                     site config: ad ids, contact, directory link
  content/calculators/*.html    calculator explainers (JSON front matter in first comment)
  content/guides/*.html         TX / OK investor guides
  content/pages/*.html          about, contact, privacy, terms
  content/news/*.json           one file per news story
  data/counties.json            county pages (official facts only, with sources)

Output: clean-URL folders (calculators/, guides/, counties/, news/, ...) plus
sitemap.xml, robots.txt, rss.xml, news/feed.json, llms.txt, 404.html, assets/config.js.
"""
import datetime as dt
import html
import json
import pathlib
import re
import shutil
import subprocess
from email.utils import format_datetime

ROOT = pathlib.Path(__file__).parent
CFG = json.loads((ROOT / "site.json").read_text(encoding="utf-8"))
BASE = CFG["BASE"].rstrip("/")
NAME = CFG["SITE_NAME"]
TODAY = dt.date.today().isoformat()
GENERATED_DIRS = ["calculators", "guides", "counties", "news", "about", "contact", "privacy", "terms"]

GTM = '''<script async src="https://www.googletagmanager.com/gtm.js?id=GTM-KMS4X55L"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
</script>'''

NETWORK = [
    ("realestate", "Real Estate"),
    ("tools", "Tools"),
    ("games", "Games"),
    ("streaming", "Streaming"),
    ("homerepair", "Home Repair"),
    ("deals", "Deals"),
    ("news", "News"),
]

NAV = [
    ("/calculators/", "Calculators"),
    ("/guides/texas/", "Texas guides"),
    ("/guides/oklahoma/", "Oklahoma guides"),
    ("/counties/", "Counties"),
    ("/news/", "News"),
    ("/about/", "About"),
]

e = html.escape


def ldjson(obj):
    return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False).replace("</", "<\\/") + "</script>"


def crumbs_ld(trail):
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": n + 1, "name": name, "item": BASE + path}
            for n, (name, path) in enumerate(trail)
        ],
    }


def crumbs_html(trail):
    if len(trail) < 2:
        return ""
    parts = [f'<a href="{p}">{e(n)}</a>' for n, p in trail[:-1]]
    parts.append(f"<span>{e(trail[-1][0])}</span>")
    return '<nav class="crumbs" aria-label="Breadcrumb">' + " / ".join(parts) + "</nav>"


def article_ld(title, desc, path, published, modified, kind="Article", image=None):
    obj = {
        "@context": "https://schema.org",
        "@type": kind,
        "headline": title[:110],
        "description": desc,
        "url": BASE + path,
        "mainEntityOfPage": BASE + path,
        "datePublished": published,
        "dateModified": modified or published,
        "author": {"@type": "Person", "name": "Sam Barth", "url": "https://samcbarth.com"},
        "publisher": {"@type": "Organization", "name": NAME, "url": BASE + "/"},
        "image": image or BASE + "/assets/og/default.jpg",
    }
    return obj


def faq_ld(faq):
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": re.sub("<[^>]+>", "", a)}}
            for q, a in faq
        ],
    }


def head(title, desc, path, lds, og_type="website", image=None, extra=""):
    full_title = title if NAME in title else f"{title} | {NAME}"
    img = image or BASE + "/assets/og/default.jpg"
    return f'''<!doctype html>
<html lang="{CFG["LANG"]}">
<head>
{GTM}
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(full_title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{BASE}{path}">
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="{e(NAME)}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{BASE}{path}">
<meta property="og:image" content="{img}">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#1f6f4a">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="alternate" type="application/rss+xml" title="{e(NAME)}" href="/rss.xml">
<link rel="alternate" type="application/feed+json" title="{e(CFG["NEWS_NAME"])}" href="/news/feed.json">
<link rel="stylesheet" href="/assets/style.css">
<script src="/assets/config.js"></script>
<script src="/assets/site.js" defer></script>
{extra}
{"".join(ldjson(x) for x in lds)}
</head>
'''


def header(path):
    links = []
    for href, label in NAV:
        cur = ' aria-current="page"' if path.startswith(href) else ""
        links.append(f'<a href="{href}"{cur}>{label}</a>')
    return f'''<body>
<a class="skip" href="#main">Skip to content</a>
<header class="site-head"><div class="wrap">
<a class="logo" href="/"><span class="logo-mark" aria-hidden="true">DM</span>{e(NAME)}</a>
<nav class="nav" aria-label="Main">{"".join(links)}<button class="theme-toggle" type="button" aria-label="Toggle dark mode">Theme</button></nav>
</div></header>
'''


def footer():
    net = []
    for sub, label in NETWORK:
        cur = ' aria-current="true"' if sub == "realestate" else ""
        net.append(f'<a href="https://{sub}.samcbarth.com/"{cur}>{label}</a>')
    year = dt.date.today().year
    return f'''<footer class="site-foot"><div class="wrap">
<div class="foot-cols">
<div><h4>{e(NAME)}</h4><p>{e(CFG["TAGLINE"])}.</p></div>
<div><h4>Calculators</h4><ul>
<li><a href="/calculators/rental-cash-flow-cap-rate/">Cash flow and cap rate</a></li>
<li><a href="/calculators/fix-and-flip/">Fix and flip</a></li>
<li><a href="/calculators/brrrr/">BRRRR</a></li>
<li><a href="/calculators/70-percent-rule/">70% rule</a></li>
<li><a href="/calculators/">All calculators</a></li></ul></div>
<div><h4>Guides</h4><ul>
<li><a href="/guides/texas/">Texas investor guides</a></li>
<li><a href="/guides/oklahoma/">Oklahoma investor guides</a></li>
<li><a href="/counties/">County resources</a></li>
<li><a href="/news/">{e(CFG["NEWS_NAME"])}</a></li></ul></div>
<div><h4>Site</h4><ul>
<li><a href="/about/">About</a></li><li><a href="/contact/">Contact</a></li>
<li><a href="/privacy/">Privacy Policy</a></li><li><a href="/terms/">Terms</a></li>
<li><a href="/rss.xml">RSS</a></li></ul></div>
</div>
<p class="disclaimer">Educational information only, not legal, tax, or financial advice. Laws and county procedures change; confirm with the official source and a licensed professional before you bid, buy, or sign.</p>
<nav class="network" aria-label="samcbarth.com network"><strong>samcbarth.com network:</strong> {" ".join(net)}</nav>
<p class="disclaimer">&copy; {year} Sam Barth. {e(NAME)} is part of the samcbarth.com network.</p>
</div></footer>
</body>
</html>
'''


def ad(slot):
    return f'<div class="ad-slot" data-ad="{slot}"></div>'


def page(path, title, desc, body, lds, trail, og_type="website", image=None, side=True, extra=""):
    side_html = f'<aside class="side"><div class="sticky">{side_box()}{ad("sidebar")}</div></aside>' if side else ""
    lay = "layout has-side" if side else "layout"
    doc = (
        head(title, desc, path, lds + [crumbs_ld(trail)] if len(trail) > 1 else lds, og_type, image, extra)
        + header(path)
        + f'<div class="wrap {lay}"><main id="main" class="main">{crumbs_html(trail)}{body}</main>{side_html}</div>'
        + footer()
    )
    out = ROOT / path.lstrip("/") / "index.html" if path.endswith("/") else ROOT / path.lstrip("/")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding="utf-8")
    SITEMAP.append(path)


def side_box():
    items = "".join(
        f'<li><a href="/calculators/{c["slug"]}/">{e(c["short"])}</a></li>' for c in CALC_LIST
    )
    return f'<div class="note"><strong>Calculators</strong><ul>{items}</ul></div>'


# --------------------------------------------------------------- content io
def read_fragment(p):
    raw = p.read_text(encoding="utf-8")
    m = re.match(r"\s*<!--(.*?)-->", raw, re.S)
    if not m:
        raise SystemExit(f"{p}: missing JSON front matter comment")
    meta = json.loads(m.group(1))
    return meta, raw[m.end():].strip()


def fmt(v, kind):
    if v is None:
        return "n/a (no cash left in the deal)" if kind == "pct" else "n/a"
    if kind == "money":
        return ("-$" if v < 0 else "$") + f"{abs(v):,.0f}"
    if kind == "money2":
        return ("-$" if v < 0 else "$") + f"{abs(v):,.2f}"
    if kind == "pct":
        return f"{v:.2f}%"
    if kind == "ratio":
        return f"{v:.2f}"
    return f"{v:,.0f}" if abs(v) >= 1000 else f"{v:g}"


# --------------------------------------------------------------- calculators
# (name, label, default, prefix, suffix, step)  type "check" uses default bool
CALC_SPECS = {
    "mortgage": {
        "title": "Mortgage payment",
        "fields": [
            ("price", "Home price", 350000, "$", "", 1000), ("down_pct", "Down payment", 20, "", "%", 0.5),
            ("rate", "Interest rate", 7.0, "", "%", 0.05), ("years", "Loan term", 30, "", "yrs", 1),
            ("tax_yr", "Property tax per year", 7000, "$", "", 100), ("ins_yr", "Insurance per year", 2400, "$", "", 50),
            ("hoa_mo", "HOA per month", 0, "$", "", 10), ("pmi_pct", "PMI rate (if under 20% down)", 0.5, "", "%/yr", 0.05),
        ],
        "outputs": [
            ("total", "Total monthly payment", "money", True), ("pi", "Principal and interest", "money", False),
            ("tax_mo", "Property tax", "money", False), ("ins_mo", "Insurance", "money", False),
            ("pmi_mo", "PMI", "money", False), ("hoa_mo", "HOA", "money", False),
            ("loan", "Loan amount", "money", False), ("total_interest", "Total interest over the loan", "money", False),
        ],
    },
    "rental": {
        "title": "Rental property",
        "fields": [
            ("price", "Purchase price", 250000, "$", "", 1000), ("closing", "Closing costs", 7500, "$", "", 100),
            ("down_pct", "Down payment", 25, "", "%", 0.5), ("rate", "Interest rate", 7.25, "", "%", 0.05),
            ("years", "Loan term", 30, "", "yrs", 1), ("rent", "Monthly rent", 2200, "$", "", 25),
            ("other_income", "Other income per month", 0, "$", "", 10), ("vacancy", "Vacancy", 6, "", "%", 0.5),
            ("tax_yr", "Property tax per year", 5000, "$", "", 100), ("ins_yr", "Insurance per year", 2000, "$", "", 50),
            ("hoa_mo", "HOA per month", 0, "$", "", 10), ("utilities_mo", "Owner-paid utilities per month", 0, "$", "", 10),
            ("maint", "Maintenance (% of rent)", 5, "", "%", 0.5), ("mgmt", "Management (% of rent)", 8, "", "%", 0.5),
            ("capex", "CapEx reserve (% of rent)", 5, "", "%", 0.5),
        ],
        "outputs": [
            ("cashflow_mo", "Monthly cash flow", "money", True), ("cap_rate", "Cap rate", "pct", True),
            ("coc", "Cash-on-cash return", "pct", False), ("noi", "Net operating income (yearly)", "money", False),
            ("egi", "Effective gross income (yearly)", "money", False), ("opex", "Operating expenses (yearly)", "money", False),
            ("debt_mo", "Mortgage payment (P&I)", "money", False), ("cash_in", "Cash invested", "money", False),
            ("dscr", "Debt service coverage ratio", "ratio", False),
        ],
    },
    "yield": {
        "title": "Rental yield",
        "fields": [
            ("price", "Purchase price", 250000, "$", "", 1000), ("costs", "Purchase costs", 7500, "$", "", 100),
            ("rent", "Monthly rent", 2200, "$", "", 25), ("expenses_yr", "Annual operating expenses", 9000, "$", "", 100),
        ],
        "outputs": [
            ("gross_yield", "Gross rental yield", "pct", True), ("net_yield", "Net rental yield", "pct", True),
            ("annual_rent", "Annual rent", "money", False), ("net_income", "Net income before mortgage", "money", False),
        ],
    },
    "flip": {
        "title": "Fix and flip",
        "fields": [
            ("purchase", "Purchase price", 180000, "$", "", 1000), ("rehab", "Rehab budget", 45000, "$", "", 500),
            ("contingency", "Rehab contingency", 10, "", "%", 1), ("arv", "After repair value (ARV)", 300000, "$", "", 1000),
            ("months", "Months held", 6, "", "mo", 1), ("holding_mo", "Holding costs per month", 1200, "$", "", 50),
            ("buy_closing_pct", "Buying closing costs", 2, "", "%", 0.25), ("sell_cost_pct", "Selling costs", 8, "", "%", 0.25),
            ("loan_pct", "Loan covers (of purchase + rehab)", 90, "", "%", 1), ("rate", "Loan interest rate", 11, "", "%", 0.25),
            ("points", "Loan points", 2, "", "pts", 0.25),
        ],
        "outputs": [
            ("profit", "Estimated profit", "money", True), ("roi", "Return on cash invested", "pct", True),
            ("annualized", "Annualized return", "pct", False), ("cash_needed", "Cash needed", "money", False),
            ("total_cost", "All-in cost (incl. selling)", "money", False), ("rehab_total", "Rehab with contingency", "money", False),
            ("interest", "Loan interest", "money", False), ("points_cost", "Points paid", "money", False),
            ("holding", "Holding costs", "money", False), ("sell_costs", "Selling costs", "money", False),
        ],
    },
    "brrrr": {
        "title": "BRRRR",
        "fields": [
            ("purchase", "Purchase price", 120000, "$", "", 1000), ("closing", "Purchase closing costs", 4000, "$", "", 100),
            ("rehab", "Rehab cost", 40000, "$", "", 500), ("holding", "Holding costs until refi", 4000, "$", "", 100),
            ("arv", "After repair value (ARV)", 210000, "$", "", 1000), ("refi_ltv", "Refinance loan-to-value", 75, "", "%", 1),
            ("refi_cost", "Refinance closing costs", 5000, "$", "", 100), ("rate", "Refinance rate", 7.5, "", "%", 0.05),
            ("years", "Refinance term", 30, "", "yrs", 1), ("rent", "Monthly rent", 1750, "$", "", 25),
            ("opex_pct", "Operating costs incl. vacancy (% of rent)", 40, "", "%", 1),
        ],
        "outputs": [
            ("cash_left", "Cash left in the deal", "money", True), ("cashflow_mo", "Monthly cash flow after refi", "money", True),
            ("coc", "Cash-on-cash return", "pct", False), ("all_in", "All-in cost", "money", False),
            ("refi_loan", "Refinance loan", "money", False), ("cash_back", "Cash back at refi (after costs)", "money", False),
            ("payment", "New mortgage payment (P&I)", "money", False), ("equity", "Equity after refi", "money", False),
        ],
    },
    "rule70": {
        "title": "70% rule",
        "fields": [
            ("arv", "After repair value (ARV)", 250000, "$", "", 1000), ("repairs", "Estimated repairs", 40000, "$", "", 500),
            ("pct", "Rule percentage", 70, "", "%", 1),
        ],
        "outputs": [("max_offer", "Maximum offer", "money", True), ("arv_pct", "ARV times percentage", "money", False)],
    },
    "wholesale": {
        "title": "Wholesale assignment fee",
        "fields": [
            ("arv", "After repair value (ARV)", 250000, "$", "", 1000), ("repairs", "Estimated repairs", 40000, "$", "", 500),
            ("investor_pct", "End buyer's rule percentage", 70, "", "%", 1), ("contract_price", "Your contract price with the seller", 125000, "$", "", 1000),
            ("costs", "Your costs (marketing, earnest money at risk)", 2000, "$", "", 100),
        ],
        "outputs": [
            ("max_fee", "Maximum assignment fee", "money", True), ("net_fee", "Fee after your costs", "money", False),
            ("buyer_max", "End buyer's maximum price", "money", False),
        ],
    },
    "proptax_tx": {
        "title": "Texas property tax",
        "fields": [
            ("value", "Appraised value", 350000, "$", "", 1000), ("homestead", "Residence homestead", True, "", "", None),
            ("over65", "Owner 65+ or disabled", False, "", "", None), ("school_rate", "School district rate", 1.0, "", "per $100", 0.001),
            ("county_rate", "County rate", 0.35, "", "per $100", 0.001), ("city_rate", "City rate", 0.55, "", "per $100", 0.001),
            ("other_rate", "Other units (college, hospital, MUD)", 0.30, "", "per $100", 0.001),
            ("local_pct", "Local optional homestead exemption", 0, "", "%", 1),
        ],
        "outputs": [
            ("total", "Estimated yearly tax", "money", True), ("monthly", "Per month", "money", False),
            ("school_tax", "School district tax", "money", False), ("other_tax", "County, city and other units", "money", False),
            ("school_taxable", "School taxable value", "money", False), ("effective", "Effective tax rate", "pct", False),
        ],
    },
    "proptax_ok": {
        "title": "Oklahoma property tax",
        "fields": [
            ("value", "Fair cash value", 250000, "$", "", 1000), ("ratio", "Assessment ratio", 11, "", "%", 0.1),
            ("homestead", "Homestead exemption", True, "", "", None), ("mills", "Total millage", 110, "", "mills", 0.1),
        ],
        "outputs": [
            ("total", "Estimated yearly tax", "money", True), ("monthly", "Per month", "money", False),
            ("assessed", "Assessed value", "money", False), ("net_assessed", "Net assessed (after homestead)", "money", False),
            ("effective", "Effective tax rate", "pct", False),
        ],
    },
}


def run_calcs():
    """Run assets/calc.js in Node with each calculator's defaults."""
    defaults = {k: {f[0]: f[2] for f in s["fields"]} for k, s in CALC_SPECS.items()}
    script = (
        "const m=require(process.argv[1]);const d=JSON.parse(process.argv[2]);const o={};"
        "for(const k in d){o[k]=m.CALCS[k](d[k]);}console.log(JSON.stringify(o));"
    )
    res = subprocess.run(
        ["node", "-e", script, str(ROOT / "assets" / "calc.js"), json.dumps(defaults)],
        capture_output=True, text=True, check=True,
    )
    return defaults, json.loads(res.stdout)


def calc_widget(cid):
    s = CALC_SPECS[cid]
    fields = []
    for name, label, default, pre, suf, step in s["fields"]:
        fid = f"{cid}-{name}"
        if isinstance(default, bool):
            chk = " checked" if default else ""
            fields.append(f'<div class="field check"><label for="{fid}"><input type="checkbox" id="{fid}" name="{name}"{chk}> {e(label)}</label></div>')
        else:
            pre_h = f"<span>{e(pre)}</span>" if pre else ""
            suf_h = f"<span>{e(suf)}</span>" if suf else ""
            fields.append(
                f'<div class="field"><label for="{fid}">{e(label)}</label><div class="inp">{pre_h}'
                f'<input type="number" id="{fid}" name="{name}" value="{default}" step="{step}" inputmode="decimal">{suf_h}</div></div>'
            )
    outs = "".join(
        f'<div class="result{" key" if key else ""}"><span>{e(label)}</span><b data-out="{k}" data-fmt="{f}">{fmt(CALC_OUT[cid][k], f)}</b></div>'
        for k, label, f, key in s["outputs"]
    )
    return f'''<section class="calc" aria-label="{e(s["title"])} calculator">
<form data-calc="{cid}" data-results="{cid}-results" novalidate>
<h2>{e(s["title"])} inputs</h2>
<div class="fields">{"".join(fields)}</div>
<div class="calc-actions"><button class="btn" type="reset">Reset to example</button></div>
</form>
<div class="results" id="{cid}-results" aria-live="polite"><h2>Results</h2>{outs}</div>
</section>'''


def fill_placeholders(text):
    def sub(m):
        cid, is_in, key, kind = m.group(1), m.group(2), m.group(3), m.group(4)
        val = CALC_IN[cid][key] if is_in else CALC_OUT[cid][key]
        return fmt(val, kind)
    return re.sub(r"\{\{(\w+)\.(in\.)?(\w+)\|(\w+)\}\}", sub, text)


def faq_html(faq):
    if not faq:
        return ""
    items = "".join(f"<h3>{e(q)}</h3><p>{a}</p>" for q, a in faq)
    return f'<section class="faq"><h2>Frequently asked questions</h2>{items}</section>'


def related_html(paths):
    if not paths:
        return ""
    cards = []
    for p in paths:
        t = TITLES.get(p)
        if not t:
            raise SystemExit(f"related link {p} has no page")
        cards.append(f'<a class="card" href="{p}"><h3>{e(t[0])}</h3><p>{e(t[1])}</p></a>')
    return '<h2>Related</h2><div class="grid">' + "".join(cards) + "</div>"


def sources_html(sources, checked=None):
    if not sources:
        return ""
    lis = "".join(f'<li><a href="{e(u)}" rel="noopener" target="_blank">{e(lbl)}</a></li>' for lbl, u in sources)
    when = f'<p class="meta">Sources last checked {checked}.</p>' if checked else ""
    return f'<section class="sources"><h2>Sources</h2><ul>{lis}</ul>{when}</section>'


def body_with_mid_ad(body):
    return body.replace("<!--ad-->", ad("mid_content"), 1)


def softwareapp_ld(meta, path):
    return {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": meta["h1"],
        "applicationCategory": "FinanceApplication",
        "operatingSystem": "Any (web browser)",
        "url": BASE + path,
        "description": meta["description"],
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
    }


def build_calculators():
    for c in CALC_LIST:
        meta, body = c["meta"], c["body"]
        path = f'/calculators/{c["slug"]}/'
        trail = [(NAME, "/"), ("Calculators", "/calculators/"), (c["short"], path)]
        widgets = "".join(calc_widget(cid) for cid in meta["calcs"])
        content = (
            f'<article class="prose-wrap"><h1>{e(meta["h1"])}</h1>'
            f'<p class="answer">{meta["answer"]}</p>{widgets}{ad("after_intro")}'
            f'<div class="prose">{body_with_mid_ad(fill_placeholders(body))}'
            f'{faq_html(meta.get("faq"))}{related_html(meta.get("related"))}'
            f'<p class="meta">Last updated {meta["updated"]}. Results are estimates for planning; they are not lender quotes or tax bills.</p></div>'
            f'{ad("end_content")}</article>'
        )
        lds = [softwareapp_ld(meta, path), article_ld(meta["title"], meta["description"], path, meta["published"], meta["updated"])]
        if meta.get("faq"):
            lds.append(faq_ld(meta["faq"]))
        page(path, meta["title"], meta["description"], content, lds, trail, "article",
             extra='<script src="/assets/calc.js" defer></script>')
    cards = "".join(
        f'<a class="card" href="/calculators/{c["slug"]}/"><h3>{e(c["short"])}</h3><p>{e(c["meta"]["description"])}</p></a>'
        for c in CALC_LIST
    )
    body = (
        "<h1>Real estate investing calculators</h1>"
        '<p class="answer">Free calculators for the numbers investors run on every deal: cash flow, cap rate, yield, '
        "mortgage payment, fix-and-flip profit, BRRRR, the 70% rule, wholesale fees, and Texas and Oklahoma property tax. "
        "Each one shows its formula and a worked example.</p>"
        f'<div class="grid">{cards}</div>{ad("end_content")}'
    )
    lds = [{"@context": "https://schema.org", "@type": "CollectionPage", "name": "Real estate investing calculators", "url": BASE + "/calculators/"}]
    page("/calculators/", "Real Estate Investing Calculators", "Free real estate investing calculators: cash flow, cap rate, rental yield, mortgage, fix and flip, BRRRR, 70% rule, wholesale fee and TX/OK property tax.", body, lds, [(NAME, "/"), ("Calculators", "/calculators/")])


# --------------------------------------------------------------- guides
STATES = {"texas": "Texas", "oklahoma": "Oklahoma"}


def build_guides():
    for g in GUIDES:
        meta, body = g["meta"], g["body"]
        st = meta["state"]
        path = f'/guides/{st}/{g["slug"]}/'
        trail = [(NAME, "/"), (f"{STATES[st]} guides", f"/guides/{st}/"), (meta["short"], path)]
        content = (
            f'<article><h1>{e(meta["h1"])}</h1><p class="meta">Updated {meta["updated"]} &middot; Educational guide, not legal advice</p>'
            f'<p class="answer">{meta["answer"]}</p>{ad("after_intro")}'
            f'<div class="prose">{body_with_mid_ad(body)}{faq_html(meta.get("faq"))}'
            f'{sources_html(meta.get("sources"), meta["updated"])}{related_html(meta.get("related"))}</div>{ad("end_content")}</article>'
        )
        lds = [article_ld(meta["title"], meta["description"], path, meta["published"], meta["updated"])]
        if meta.get("faq"):
            lds.append(faq_ld(meta["faq"]))
        page(path, meta["title"], meta["description"], content, lds, trail, "article")

    for st, label in STATES.items():
        mine = [g for g in GUIDES if g["meta"]["state"] == st]
        cards = "".join(
            f'<a class="card" href="/guides/{st}/{g["slug"]}/"><h3>{e(g["meta"]["short"])}</h3><p>{e(g["meta"]["description"])}</p></a>'
            for g in mine
        )
        counties = [c for c in COUNTIES if c["state"] == label]
        ccards = "".join(f'<li><a href="/counties/{st}/{c["slug"]}/">{e(c["name"])}</a></li>' for c in counties)
        intro = STATE_INTRO[st]
        body = (
            f"<h1>{label} real estate investor guides</h1><p class=\"answer\">{intro}</p>"
            f'<div class="grid">{cards}</div>'
            f'<h2>{label} county resources</h2><ul class="prose">{ccards}</ul>{ad("end_content")}'
        )
        lds = [{"@context": "https://schema.org", "@type": "CollectionPage", "name": f"{label} real estate investor guides", "url": BASE + f"/guides/{st}/"}]
        page(f"/guides/{st}/", f"{label} Real Estate Investor Guides", f"How tax sales, foreclosures, probate property and sheriff sales work in {label}, with links to the statutes.", body, lds,
             [(NAME, "/"), (f"{label} guides", f"/guides/{st}/")])

    # comparison hub
    rows = "".join(f"<tr><th>{e(r[0])}</th><td>{r[1]}</td><td>{r[2]}</td></tr>" for r in COMPARE)
    body = (
        "<h1>Texas vs Oklahoma: how distressed property sales work</h1>"
        '<p class="answer">Texas forecloses most mortgages without going to court and sells on the first Tuesday of the month; '
        "Oklahoma usually forecloses through the courts and sells through the county sheriff after an appraisal. Tax sales differ too: "
        "Texas sells after a court judgment with a redemption period afterward, while Oklahoma holds an annual county treasurer resale in June.</p>"
        f'<div class="prose"><table><thead><tr><th></th><th>Texas</th><th>Oklahoma</th></tr></thead><tbody>{rows}</tbody></table>'
        '<p>Each row is explained, with the statute links, in the state guides: '
        '<a href="/guides/texas/">Texas guides</a> and <a href="/guides/oklahoma/">Oklahoma guides</a>.</p></div>'
        f'{ad("end_content")}'
    )
    page("/guides/", "Texas and Oklahoma Investor Guides", "Side-by-side comparison of tax sales, foreclosure, probate and sheriff sales in Texas and Oklahoma, with links to each state's statutes.", body,
         [article_ld("Texas vs Oklahoma: how distressed property sales work", "Comparison of TX and OK distressed property sale processes.", "/guides/", "2026-11-09", TODAY)],
         [(NAME, "/"), ("Guides", "/guides/")], "article")


STATE_INTRO = {
    "texas": "Texas sells foreclosed and tax-delinquent property at public auctions held on the first Tuesday of each month, "
             "between 10 a.m. and 4 p.m., at the county courthouse or another place the commissioners court designates, or online "
             "where the county authorizes it. These guides explain each sale type and link to the Texas statutes.",
    "oklahoma": "Oklahoma mortgage foreclosures usually run through the district court and end in a sheriff's sale, while tax-delinquent "
                "land goes to the county treasurer's annual resale held the second Monday of June. These guides explain each sale type "
                "and link to the Oklahoma statutes.",
}

COMPARE = [
    ("Usual mortgage foreclosure", "Nonjudicial (power of sale in the deed of trust), Property Code 51.002", "Judicial (court case, then sheriff's sale); a power of sale exists but a homestead owner can elect judicial foreclosure, 46 O.S. 43"),
    ("When sales happen", "First Tuesday of the month, 10 a.m. to 4 p.m.", "Sheriff's sales are set after judgment; the tax resale is the second Monday of June"),
    ("Foreclosure notice", "At least 21 days before the sale, posted at the courthouse and filed with the county clerk", "Published notice; sale at least 30 days after first publication, 12 O.S. 764"),
    ("Minimum bid at sheriff sale", "No statewide appraisal minimum for mortgage foreclosures", "Two-thirds of appraised value unless appraisal was waived"),
    ("Tax sale type", "Tax lien foreclosure by lawsuit, then sheriff or constable sale (Tax Code ch. 34)", "County treasurer resale of land delinquent 3 or more years (68 O.S. 3105, 3125)"),
    ("Redemption after a tax sale", "2 years for homesteads, ag land and mineral interests; 180 days for other property (Tax Code 34.21)", "See the Oklahoma tax sale guide for the treasurer's process"),
    ("Small estate shortcut", "Small estate affidavit up to $75,000, homestead only for real property (Estates Code ch. 205)", "Affidavit up to $50,000 (58 O.S. 393); summary administration up to $200,000 (58 O.S. 245)"),
]


# --------------------------------------------------------------- counties
def build_counties():
    data = COUNTY_DATA
    for c in COUNTIES:
        st = c["state"].lower()
        path = f'/counties/{st}/{c["slug"]}/'
        trail = [(NAME, "/"), ("Counties", "/counties/"), (c["name"] + ", " + c["abbr"], path)]
        facts = "".join(f"<tr><th>{e(k)}</th><td>{v}</td></tr>" for k, v in c["facts"])
        links = "".join(f'<li><a href="{e(u)}" rel="noopener" target="_blank">{e(lbl)}</a></li>' for lbl, u in c["links"])
        state_rules = data["state_rules"][c["state"]]
        rules = "".join(f"<li>{r}</li>" for r in state_rules["items"])
        directory = ""
        if CFG.get("TXOK_DIRECTORY_URL"):
            directory = f'<p><a class="dir-link" href="{e(CFG["TXOK_DIRECTORY_URL"])}">{e(CFG["TXOK_DIRECTORY_LABEL"])}</a></p>'
        guide_links = "".join(
            f'<li><a href="/guides/{st}/{g["slug"]}/">{e(g["meta"]["short"])}</a></li>' for g in GUIDES if g["meta"]["state"] == st
        )
        title = f'{c["name"]}, {c["state"]} Real Estate Investor Resources'
        desc = f'Official links for {c["name"]}, {c["state"]}: county website, {"appraisal district" if st == "texas" else "assessor"} and tax office, plus how foreclosure and tax sales work there. Sources checked {c["last_checked"]}.'
        body = (
            f'<article><h1>{e(c["name"])}, {e(c["state"])}: investor resources</h1>'
            f'<p class="meta">Last checked {c["last_checked"]} against official county and state sources</p>'
            f'<p class="answer">{c["answer"]}</p>{ad("after_intro")}<div class="prose">'
            f'<h2>Key facts</h2><table><tbody>{facts}</tbody></table>'
            f'<h2>Official {e(c["name"])} offices</h2><ul>{links}</ul>'
            f'<h2>How sales work in {e(c["name"])}</h2><p>{state_rules["lead"]}</p><ul>{rules}</ul>'
            '<p class="note">This page does not list auction dates or properties. Sale lists change every month; get them from the county offices above or the officer conducting the sale.</p>'
            f'{directory}<h2>{e(c["state"])} guides</h2><ul>{guide_links}</ul>'
            f'{sources_html(c["sources"] + state_rules["sources"], c["last_checked"])}</div>{ad("end_content")}</article>'
        )
        lds = [article_ld(title, desc, path, "2026-11-09", c["last_checked"])]
        page(path, title, desc, body, lds, trail, "article")

    sections = []
    for st, label in STATES.items():
        lis = "".join(
            f'<a class="card" href="/counties/{st}/{c["slug"]}/"><h3>{e(c["name"])}</h3><p>Seat: {e(c["seat"])} &middot; Pop. {c["pop2025"]:,} (2025 est.)</p></a>'
            for c in COUNTIES if c["state"] == label
        )
        sections.append(f'<h2>{label}</h2><div class="grid">{lis}</div>')
    body = (
        "<h1>Texas and Oklahoma county investor resources</h1>"
        '<p class="answer">County pages for the 12 largest Texas counties and 8 largest Oklahoma counties by 2025 Census Bureau population estimate. '
        "Each page links the official county, appraisal or assessor, and tax offices and summarizes how foreclosure and tax sales work under state law, "
        "with sources and the date we last checked them.</p>"
        + "".join(sections) + ad("end_content")
    )
    lds = [{"@context": "https://schema.org", "@type": "CollectionPage", "name": "TX and OK county investor resources", "url": BASE + "/counties/"}]
    page("/counties/", "Texas and Oklahoma County Investor Resources", "Official county links and sale rules for the largest Texas and Oklahoma counties, with sources and last-checked dates.", body, lds,
         [(NAME, "/"), ("Counties", "/counties/")])


# --------------------------------------------------------------- news
def build_news():
    for n in NEWS:
        path = f'/news/{n["slug"]}/'
        trail = [(NAME, "/"), ("News", "/news/"), (n["title"][:60], path)]
        paras = "".join(f"<p>{p}</p>" for p in n["body"])
        rel = related_html(n.get("related"))
        quote = ""
        if n.get("quote"):
            quote = f'<blockquote><p>"{e(n["quote"]["text"])}"</p><footer>{e(n["quote"]["by"])}</footer></blockquote>'
        body = (
            f'<article><p class="meta">{e(CFG["NEWS_NAME"])} &middot; <time datetime="{n["date"]}">{n["date_human"]}</time></p>'
            f'<h1>{e(n["title"])}</h1><p class="answer">{e(n["summary"])}</p>'
            f'<figure class="news-hero"><picture><source srcset="/assets/og/news-{n["slug"]}.webp" type="image/webp">'
            f'<img src="/assets/og/news-{n["slug"]}.jpg" alt="{e(n["title"])}" width="1200" height="630" loading="lazy"></picture></figure>'
            f'{ad("after_intro")}<div class="prose">{paras}{quote}'
            f'<h2>Why it matters to investors</h2><p>{n["why"]}</p>'
            f'<p><strong>Source:</strong> <a href="{e(n["source_url"])}" rel="noopener" target="_blank">{e(n["source_name"])}</a></p>'
            f'{rel}</div>{ad("end_content")}</article>'
        )
        img = f'{BASE}/assets/og/news-{n["slug"]}.jpg'
        ld = article_ld(n["title"], n["summary"], path, n["date"], n["date"], "NewsArticle", img)
        page(path, n["title"], n["summary"], body, [ld], trail, "article", img)

    items = "".join(
        f'<li><p class="meta">{n["date_human"]} &middot; {e(", ".join(n["tags"]))}</p><h3><a href="/news/{n["slug"]}/">{e(n["title"])}</a></h3><p>{e(n["summary"])}</p></li>'
        for n in NEWS
    )
    body = (
        f'<h1>{e(CFG["NEWS_NAME"])}</h1>'
        '<p class="answer">Short, sourced updates on mortgage rates, the housing market, and Texas and Oklahoma real estate rules, '
        "each with a link to the primary source and to the calculator or guide it affects.</p>"
        f'<ul class="news-list">{items}</ul><p class="meta">Feeds: <a href="/news/feed.json">JSON Feed</a> &middot; <a href="/rss.xml">RSS</a></p>{ad("end_content")}'
    )
    lds = [{"@context": "https://schema.org", "@type": "CollectionPage", "name": CFG["NEWS_NAME"], "url": BASE + "/news/"}]
    page("/news/", CFG["NEWS_NAME"], "Sourced real estate news for investors: mortgage rates, housing data, and Texas and Oklahoma property rules.", body, lds, [(NAME, "/"), ("News", "/news/")])

    feed = {
        "version": "https://jsonfeed.org/version/1.1",
        "title": f'{CFG["NEWS_NAME"]} ({NAME})',
        "home_page_url": BASE + "/news/",
        "feed_url": BASE + "/news/feed.json",
        "description": "Sourced real estate news for investors from realestate.samcbarth.com.",
        "language": "en-US",
        "icon": BASE + "/assets/og/default.jpg",
        "authors": [{"name": "Sam Barth", "url": "https://samcbarth.com"}],
        "items": [
            {
                "id": BASE + f'/news/{n["slug"]}/',
                "url": BASE + f'/news/{n["slug"]}/',
                "title": n["title"],
                "summary": n["summary"],
                "content_text": n["summary"],
                "image": BASE + f'/assets/og/news-{n["slug"]}.jpg',
                "date_published": n["date"] + "T12:00:00-06:00",
                "tags": n["tags"],
                "external_url": n["source_url"],
            }
            for n in NEWS
        ],
    }
    (ROOT / "news" / "feed.json").write_text(json.dumps(feed, indent=2, ensure_ascii=False), encoding="utf-8")


# --------------------------------------------------------------- og images
def og_images():
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("Pillow missing: skipping og images")
        return
    outdir = ROOT / "assets" / "og"
    outdir.mkdir(parents=True, exist_ok=True)

    def font(size, bold=True):
        for f in (["arialbd.ttf", "DejaVuSans-Bold.ttf"] if bold else ["arial.ttf", "DejaVuSans.ttf"]):
            for d in ["C:/Windows/Fonts/", "/usr/share/fonts/truetype/dejavu/", ""]:
                try:
                    return ImageFont.truetype(d + f, size)
                except OSError:
                    continue
        return ImageFont.load_default()

    def wrap(draw, text, fnt, width):
        words, lines, cur = text.split(), [], ""
        for w in words:
            t = (cur + " " + w).strip()
            if draw.textlength(t, font=fnt) <= width:
                cur = t
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
        return lines

    def card(name, kicker, title, force=False):
        jpg = outdir / f"{name}.jpg"
        if jpg.exists() and not force:
            return
        im = Image.new("RGB", (1200, 630), "#1f6f4a")
        d = ImageDraw.Draw(im)
        d.rectangle([0, 560, 1200, 630], fill="#174f36")
        d.text((70, 70), kicker.upper(), font=font(30), fill="#cfe9da")
        y = 140
        for line in wrap(d, title, font(62), 1060)[:5]:
            d.text((70, y), line, font=font(62), fill="#ffffff")
            y += 78
        d.text((70, 578), "realestate.samcbarth.com", font=font(28, False), fill="#ffffff")
        im.save(jpg, quality=85)
        im.save(outdir / f"{name}.webp", quality=80)

    card("default", NAME, "Real estate investing calculators and Texas and Oklahoma investor guides")
    for n in NEWS:
        card(f'news-{n["slug"]}', CFG["NEWS_NAME"], n["title"])


# --------------------------------------------------------------- home + pages
def build_home():
    calc_cards = "".join(
        f'<a class="card" href="/calculators/{c["slug"]}/"><span class="tag">Calculator</span><h3>{e(c["short"])}</h3><p>{e(c["meta"]["description"])}</p></a>'
        for c in CALC_LIST
    )
    guide_cards = "".join(
        f'<a class="card" href="/guides/{g["meta"]["state"]}/{g["slug"]}/"><span class="tag">{STATES[g["meta"]["state"]]}</span><h3>{e(g["meta"]["short"])}</h3><p>{e(g["meta"]["description"])}</p></a>'
        for g in GUIDES
    )
    news_items = "".join(
        f'<li><p class="meta">{n["date_human"]}</p><h3><a href="/news/{n["slug"]}/">{e(n["title"])}</a></h3></li>' for n in NEWS[:4]
    )
    body = (
        '<section class="hero"><h1>Run the numbers before you make the offer</h1>'
        f'<p>{e(NAME)} has free calculators for rentals, flips, BRRRR and wholesale deals, plus plain-English guides to buying '
        "tax-sale, foreclosure, probate and sheriff-sale property in Texas and Oklahoma.</p></section>"
        f'<h2>Calculators</h2><div class="grid">{calc_cards}</div>{ad("after_intro")}'
        f'<h2>Texas and Oklahoma investor guides</h2><p>Compare the two states side by side on the <a href="/guides/">comparison page</a>, or open a guide:</p>'
        f'<div class="grid">{guide_cards}</div>'
        '<h2>County resources</h2><p>Official offices and sale rules for the <a href="/counties/">20 largest Texas and Oklahoma counties</a>, '
        'from <a href="/counties/texas/harris/">Harris</a> and <a href="/counties/texas/dallas/">Dallas</a> to '
        '<a href="/counties/oklahoma/oklahoma/">Oklahoma County</a> and <a href="/counties/oklahoma/tulsa/">Tulsa</a>.</p>'
        f'<h2>{e(CFG["NEWS_NAME"])}</h2><ul class="news-list">{news_items}</ul><p><a href="/news/">All news</a></p>{ad("end_content")}'
    )
    lds = [{
        "@context": "https://schema.org", "@type": "WebSite", "name": NAME, "url": BASE + "/",
        "description": CFG["TAGLINE"], "inLanguage": "en-US",
        "publisher": {"@type": "Person", "name": "Sam Barth", "url": "https://samcbarth.com"},
    }]
    page("/", f"{NAME}: Real Estate Investing Calculators and TX/OK Guides",
         "Free real estate investing calculators (cash flow, cap rate, flip, BRRRR, 70% rule) and guides to tax sales, foreclosures and probate property in Texas and Oklahoma.",
         body, lds, [(NAME, "/")], side=False)


def build_pages():
    for p in sorted((ROOT / "content" / "pages").glob("*.html")):
        meta, body = read_fragment(p)
        path = f"/{p.stem}/"
        if p.stem == "contact":
            body = body.replace("<!--contact-->", contact_block())
        content = f'<article class="prose"><h1>{e(meta["h1"])}</h1>{body}<p class="meta">Last updated {meta["updated"]}.</p></article>'
        page(path, meta["title"], meta["description"], content,
             [article_ld(meta["title"], meta["description"], path, meta["updated"], meta["updated"], "WebPage")],
             [(NAME, "/"), (meta["h1"], path)], side=False)


def contact_block():
    if CFG.get("HUBSPOT_FORM_ID"):
        return (
            '<div id="hs-form"></div><script src="https://js.hsforms.net/forms/embed/v2.js"></script>'
            f'<script>hbspt.forms.create({{region:"na1",portalId:"{e(CFG["HUBSPOT_PORTAL"])}",formId:"{e(CFG["HUBSPOT_FORM_ID"])}",target:"#hs-form"}});</script>'
        )
    if CFG.get("CONTACT_EMAIL"):
        em = e(CFG["CONTACT_EMAIL"])
        return f'<p>Email: <a href="mailto:{em}?subject=Deal%20Math%20question">{em}</a></p>'
    return '<p>You can reach Sam Barth through <a href="https://samcbarth.com/">samcbarth.com</a>.</p>'


def build_404():
    doc = head("Page not found", "That page does not exist.", "/404.html", []) + header("/404") + (
        '<div class="wrap layout"><main id="main" class="main prose"><h1>Page not found</h1>'
        '<p>That page does not exist. Try the <a href="/calculators/">calculators</a>, the '
        '<a href="/guides/">Texas and Oklahoma guides</a>, or the <a href="/">home page</a>.</p></main></div>'
    ) + footer()
    (ROOT / "404.html").write_text(doc.replace('<meta name="description"', '<meta name="robots" content="noindex">\n<meta name="description"', 1), encoding="utf-8")


# --------------------------------------------------------------- feeds etc
def write_static():
    (ROOT / "assets" / "config.js").write_text(
        "/* Generated by build.py from site.json. Edit site.json, then run python build.py. */\n"
        "window.SITE_CONFIG = " + json.dumps({
            "ADSENSE_CLIENT": CFG["ADSENSE_CLIENT"], "AD_SLOTS": CFG["AD_SLOTS"], "AMAZON_TAG": CFG["AMAZON_TAG"],
        }, indent=2) + ";\n", encoding="utf-8")
    urls = "".join(f"<url><loc>{BASE}{p}</loc><lastmod>{TODAY}</lastmod></url>\n" for p in SITEMAP)
    (ROOT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls + "</urlset>\n", encoding="utf-8")
    (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n", encoding="utf-8")
    (ROOT / "CNAME").write_text("realestate.samcbarth.com\n", encoding="utf-8")
    (ROOT / ".nojekyll").write_text("", encoding="utf-8")

    def rfc(d):
        return format_datetime(dt.datetime.fromisoformat(d + "T12:00:00-06:00"))
    items = []
    for n in NEWS:
        items.append((n["date"], n["title"], f'/news/{n["slug"]}/', n["summary"]))
    for g in GUIDES:
        m = g["meta"]
        items.append((m["published"], m["title"], f'/guides/{m["state"]}/{g["slug"]}/', m["description"]))
    items.sort(key=lambda x: x[0], reverse=True)
    rss_items = "".join(
        f"<item><title>{e(t)}</title><link>{BASE}{p}</link><guid>{BASE}{p}</guid><pubDate>{rfc(d)}</pubDate><description>{e(s)}</description></item>\n"
        for d, t, p, s in items
    )
    (ROOT / "rss.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel><title>{e(NAME)}</title><link>{BASE}/</link>'
        f"<description>{e(CFG['TAGLINE'])}</description><language>en-us</language>\n{rss_items}</channel></rss>\n", encoding="utf-8")

    lines = [f"# {NAME} (realestate.samcbarth.com)", "", f"> {CFG['TAGLINE']}. Free calculators with formulas and worked examples; "
             "Texas and Oklahoma guides that cite the statutes; county pages built only from official sources with last-checked dates.", ""]
    lines += ["## Calculators"] + [f"- [{c['short']}]({BASE}/calculators/{c['slug']}/): {c['meta']['description']}" for c in CALC_LIST]
    lines += ["", "## Guides"] + [f"- [{g['meta']['title']}]({BASE}/guides/{g['meta']['state']}/{g['slug']}/): {g['meta']['description']}" for g in GUIDES]
    lines += ["", "## Counties"] + [f"- [{c['name']}, {c['state']}]({BASE}/counties/{c['state'].lower()}/{c['slug']}/)" for c in COUNTIES]
    lines += ["", "## News", f"- [{CFG['NEWS_NAME']}]({BASE}/news/): JSON Feed at {BASE}/news/feed.json"]
    lines += ["", "## Policies", f"- [About]({BASE}/about/)", f"- [Privacy]({BASE}/privacy/)", f"- [Terms]({BASE}/terms/)", ""]
    (ROOT / "llms.txt").write_text("\n".join(lines), encoding="utf-8")


# --------------------------------------------------------------- main
def load():
    global CALC_LIST, GUIDES, NEWS, COUNTIES, COUNTY_DATA, TITLES
    CALC_LIST = []
    for p in sorted((ROOT / "content" / "calculators").glob("*.html")):
        meta, body = read_fragment(p)
        CALC_LIST.append({"slug": p.stem, "short": meta["short"], "meta": meta, "body": body, "order": meta.get("order", 99)})
    CALC_LIST.sort(key=lambda c: c["order"])
    GUIDES = []
    for p in sorted((ROOT / "content" / "guides").glob("*.html")):
        meta, body = read_fragment(p)
        GUIDES.append({"slug": p.stem.split("-", 1)[1], "meta": meta, "body": body, "order": meta.get("order", 99)})
    GUIDES.sort(key=lambda g: (g["meta"]["state"] != "texas", g["order"]))
    NEWS = []
    for p in sorted((ROOT / "content" / "news").glob("*.json")):
        n = json.loads(p.read_text(encoding="utf-8"))
        n["slug"] = p.stem[11:] if re.match(r"\d{4}-\d{2}-\d{2}-", p.stem) else p.stem
        d = dt.date.fromisoformat(n["date"])
        n["date_human"] = d.strftime("%B %d, %Y").replace(" 0", " ")
        NEWS.append(n)
    NEWS.sort(key=lambda n: n["date"], reverse=True)
    COUNTY_DATA = json.loads((ROOT / "data" / "counties.json").read_text(encoding="utf-8"))
    COUNTIES = COUNTY_DATA["counties"]

    TITLES = {}
    for c in CALC_LIST:
        TITLES[f'/calculators/{c["slug"]}/'] = (c["meta"]["h1"], c["meta"]["description"])
    for g in GUIDES:
        TITLES[f'/guides/{g["meta"]["state"]}/{g["slug"]}/'] = (g["meta"]["h1"], g["meta"]["description"])
    for c in COUNTIES:
        TITLES[f'/counties/{c["state"].lower()}/{c["slug"]}/'] = (f'{c["name"]}, {c["state"]}', "Official offices and sale rules")
    TITLES["/guides/"] = ("Texas vs Oklahoma comparison", "How distressed property sales differ between the two states")
    TITLES["/counties/"] = ("County resources", "Official links for the largest TX and OK counties")


def main():
    global CALC_IN, CALC_OUT, SITEMAP
    SITEMAP = []
    for d in GENERATED_DIRS:
        shutil.rmtree(ROOT / d, ignore_errors=True)
    load()
    CALC_IN, CALC_OUT = run_calcs()
    og_images()
    build_home()
    build_calculators()
    build_guides()
    build_counties()
    build_news()
    build_pages()
    build_404()
    write_static()
    print(f"Built {len(SITEMAP)} pages: {len(CALC_LIST)} calculators, {len(GUIDES)} guides, {len(COUNTIES)} counties, {len(NEWS)} news stories.")


if __name__ == "__main__":
    main()
