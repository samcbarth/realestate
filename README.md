# Deal Math (realestate.samcbarth.com)

Real estate investing calculators, Texas and Oklahoma investor guides, county resource pages and a sourced news section. Static HTML built by `build.py`; part of the samcbarth.com network (rules in `C:\SamSites\NETWORK.md`).

## Build and preview

```
python build.py              # regenerates every page, feeds, sitemap, config.js
python tests/check_site.py   # link check, head tags, JSON-LD, no em dashes/emojis
python tests/check_site.py --external   # also requests every external link
python -m http.server 8821   # preview at http://localhost:8821
```

Requires Python 3 with Pillow (for the OG/news images) and Node (the build runs `assets/calc.js` in Node so each worked example uses the same math as the live calculator).

## Adding content

| What | Where | Notes |
|---|---|---|
| News story | `content/news/YYYY-MM-DD-slug.json` | Copy an existing file. Fields: `title`, `date`, `summary`, `body` (list of HTML paragraphs), `why`, `source_name`, `source_url`, `tags`, `related` (internal paths), optional `quote` (one short attributed line). Real, sourced facts only. Rebuild; it appears on `/news/`, in `/news/feed.json` and RSS, and gets an OG image. |
| Guide | `content/guides/<state>-<slug>.html` | JSON front matter in the first `<!-- -->` comment (`state`, `short`, `title`, `h1`, `description`, `answer`, `sources`, `faq`, `related`, dates). Put `<!--ad-->` where the mid-content ad should go. |
| Calculator | `content/calculators/<slug>.html` + a compute function in `assets/calc.js` + field spec in `CALC_SPECS` in `build.py` | Worked-example numbers use placeholders like `{{rental.noi|money}}` or `{{rental.in.price|money}}`. |
| County | `data/make_counties.py`, then run it with the Census CSV path to rewrite `data/counties.json` | Official sources only, each with a `last_checked` date. No auction dates. Never use data from the paid TX/OK directory project. |
| Policy pages | `content/pages/*.html` | about, contact, privacy, terms. |

Related links (`related`) must point at pages that exist or the build stops with an error.

## Config ids (all in `site.json`)

- `ADSENSE_CLIENT` (ca-pub-...) and `AD_SLOTS` (`after_intro`, `mid_content`, `end_content`, `sidebar`). While empty, ad slots render nothing. The build copies these into `assets/config.js`.
- `AMAZON_TAG`: unused for now (AdSense site).
- `TXOK_DIRECTORY_URL` / `TXOK_DIRECTORY_LABEL`: plain link to the paid TX/OK directory, shown on county pages only when the URL is set. Empty for now.
- `HUBSPOT_PORTAL` (20693956) and `HUBSPOT_FORM_ID`: when the form id is set, `/contact/` embeds the HubSpot form. Otherwise it uses `CONTACT_EMAIL`, and if that is empty too, it points to samcbarth.com.

`ads.txt` belongs at the root domain samcbarth.com (HubSpot), not here.

## Deploy

GitHub Pages from `main` root. `CNAME` contains `realestate.samcbarth.com`. DNS record Sam adds at Squarespace:

| Type | Host | Value |
|---|---|---|
| CNAME | `realestate` | `samcbarth.github.io` |

The GitHub repo has not been created; do not push without Sam's yes.

## Waiting on accounts

- AdSense approval: fill `ADSENSE_CLIENT` and slot ids, rebuild.
- HubSpot contact form id (or a public contact email) for `/contact/`.
- TX/OK directory public URL, if Sam wants the link shown.
