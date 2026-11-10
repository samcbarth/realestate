"""One-off helper that writes data/counties.json from the Census Vintage 2025 county
estimates file plus hand-checked official links. Re-run only after re-checking sources.
Usage: python data/make_counties.py path/to/co-est2025-alldata.csv
"""
import csv
import json
import pathlib
import sys

CHECKED = "2026-11-09"
CENSUS_CSV = "https://www2.census.gov/programs-surveys/popest/datasets/2020-2025/counties/totals/co-est2025-alldata.csv"
CENSUS_PAGE = "https://www.census.gov/programs-surveys/popest/data/tables.html"

TX = [  # fips, slug, seat, official links
    ("201", "harris", "Houston", [
        ("Harris County official website", "https://www.harriscountytx.gov/"),
        ("Harris Central Appraisal District", "https://hcad.org/"),
        ("Harris County Tax Assessor-Collector", "https://www.hctax.net/"),
        ("Harris County Clerk (foreclosure notices are filed with the county clerk)", "https://www.cclerk.hctx.net/")]),
    ("113", "dallas", "Dallas", [
        ("Dallas County official website", "https://www.dallascounty.org/"),
        ("Dallas Central Appraisal District", "https://www.dallascad.org/"),
        ("Dallas County Tax Office", "https://www.dallascounty.org/departments/tax/")]),
    ("439", "tarrant", "Fort Worth", [
        ("Tarrant County official website", "https://www.tarrantcountytx.gov/"),
        ("Tarrant Appraisal District", "https://www.tad.org/"),
        ("Tarrant County Tax Assessor-Collector", "https://www.tarrantcountytx.gov/en/tax.html")]),
    ("029", "bexar", "San Antonio", [
        ("Bexar County official website", "https://www.bexar.org/"),
        ("Bexar Appraisal District", "https://bcad.org/"),
        ("Bexar County tax information", "https://www.bexar.org/1529")]),
    ("453", "travis", "Austin", [
        ("Travis County official website", "https://www.traviscountytx.gov/"),
        ("Travis Central Appraisal District", "https://traviscad.org/"),
        ("Travis County Tax Office", "https://tax-office.traviscountytx.gov/")]),
    ("085", "collin", "McKinney", [
        ("Collin County official website", "https://www.collincountytx.gov/"),
        ("Collin Central Appraisal District", "https://collincad.org/"),
        ("Collin County Tax Assessor-Collector", "https://www.collincountytx.gov/Tax-Assessor"),
        ("Collin County Clerk", "https://www.collincountytx.gov/county-clerk")]),
    ("121", "denton", "Denton", [
        ("Denton County official website", "https://www.dentoncounty.gov/"),
        ("Denton Central Appraisal District", "https://www.dentoncad.com/"),
        ("Denton County Tax Assessor/Collector", "https://www.dentoncounty.gov/778/Tax-Assessor-Collector"),
        ("Denton County foreclosure information", "https://www.dentoncounty.gov/1176/Foreclosure-Information"),
        ("Denton County sheriff's sale", "https://www.dentoncounty.gov/1180/Sheriffs-Sale")]),
    ("157", "fort-bend", "Richmond", [
        ("Fort Bend County official website", "https://www.fortbendcountytx.gov/"),
        ("Fort Bend Central Appraisal District", "https://www.fbcad.org/"),
        ("Fort Bend County Tax Assessor-Collector", "https://www.fortbendcountytx.gov/government/departments/tax-assessor-collector"),
        ("Fort Bend County Clerk: search for foreclosures", "https://www.fortbendcountytx.gov/government/departments/county-clerk/search-for-foreclosures")]),
    ("215", "hidalgo", "Edinburg", [
        ("Hidalgo County official website", "https://www.hidalgocounty.us/"),
        ("Hidalgo County Appraisal District", "https://www.hidalgoad.org/"),
        ("Hidalgo County tax rates", "https://www.hidalgocounty.us/128/Tax-Rates")]),
    ("141", "el-paso", "El Paso", [
        ("El Paso County official website", "https://www.epcounty.com/"),
        ("El Paso Central Appraisal District", "https://epcad.org/")]),
    ("339", "montgomery", "Conroe", [
        ("Montgomery County official website", "https://www.mctx.org/"),
        ("Montgomery Central Appraisal District", "https://mcad-tx.org/"),
        ("Montgomery County Tax Office", "https://www.mctotx.org/"),
        ("Montgomery County Clerk", "https://countyclerk.mctx.org/")]),
    ("491", "williamson", "Georgetown", [
        ("Williamson County official website", "https://www.wilcotx.gov/"),
        ("Williamson Central Appraisal District", "https://www.wcad.org/")]),
]

OK = [
    ("109", "oklahoma", "Oklahoma City", [
        ("Oklahoma County official website", "https://www.oklahomacounty.org/"),
        ("Oklahoma County Assessor", "https://www.oklahomacounty.org/Elected-Offices/Assessor"),
        ("Oklahoma County Treasurer", "https://www.oklahomacounty.org/Elected-Offices/Treasurer"),
        ("Oklahoma County Clerk", "https://www.oklahomacounty.org/Elected-Offices/County-Clerk"),
        ("Oklahoma County Sheriff", "https://www.oklahomacounty.org/Elected-Offices/Sheriff")]),
    ("143", "tulsa", "Tulsa", [
        ("Tulsa County official website", "https://www.tulsacounty.org/"),
        ("Tulsa County Assessor", "https://assessor.tulsacounty.org/"),
        ("Tulsa County Treasurer", "https://www2.tulsacounty.org/treasurer/")]),
    ("027", "cleveland", "Norman", [
        ("Cleveland County official website", "https://www.clevelandcountyok.com/"),
        ("Cleveland County Assessor", "https://www.clevelandcountyok.com/129/County-Assessor"),
        ("Cleveland County Treasurer", "https://www.clevelandcountyok.com/177/County-Treasurer"),
        ("Cleveland County Clerk", "https://www.clevelandcountyok.com/130/County-Clerk")]),
    ("017", "canadian", "El Reno", [
        ("Canadian County official website", "https://www.canadiancounty.org/"),
        ("Canadian County Assessor", "https://www.canadiancounty.org/948/Assessor-Matt-Wehmuller"),
        ("Canadian County Treasurer", "https://www.canadiancounty.org/104/Treasurer"),
        ("Canadian County: how property tax is figured", "https://www.canadiancounty.org/1008/How-property-tax-is-figured")]),
    ("031", "comanche", "Lawton", [
        ("Comanche County official website", "https://www.comanchecountyok.gov/"),
        ("Comanche County property tax roll (linked from the county site)", "https://oktaxrolls.com/searchTaxRoll/Comanche"),
        ("Comanche County Sheriff", "https://www.comanchecountyok.gov/227/Sheriff")]),
    ("131", "rogers", "Claremore", [
        ("Rogers County official website", "https://www.rogerscounty.org/")]),
    ("145", "wagoner", "Wagoner", [
        ("Wagoner County official website", "https://www.wagonercounty.ok.gov/")]),
    ("119", "payne", "Stillwater", [
        ("Payne County official website", "https://www.paynecounty.org/"),
        ("Payne County Assessor", "http://paynecountyassessor.org/"),
        ("Payne County Clerk", "https://www.countyclerk.paynecounty.org/"),
        ("Payne County Treasurer tax roll (linked from the county site)", "https://oktaxrolls.com/county/Payne"),
        ("Payne County Sheriff's Office sheriff sale listings", "https://www.paynecountyok.gov/sheriff-sale")]),
]

STATE_RULES = {
    "Texas": {
        "lead": "Texas sets the sale rules statewide, so they are the same in every county:",
        "items": [
            "Mortgage foreclosures are usually nonjudicial trustee sales. Notice must be posted at the courthouse and filed with the county clerk at least 21 days before the sale (Property Code 51.002). <a href=\"/guides/texas/foreclosure/\">Texas foreclosure guide</a>",
            "Sales are held on the first Tuesday of the month between 10 a.m. and 4 p.m. at the courthouse or an area the commissioners court designates, or online if the county authorizes it.",
            "Tax sales follow a court judgment or tax warrant and are run by the sheriff or a constable. Homestead and ag property can be redeemed for 2 years, other property for 180 days (Tax Code 34.21). <a href=\"/guides/texas/tax-sales/\">Texas tax sale guide</a>",
        ],
        "sources": [
            ["Texas Property Code, Chapter 51", "https://statutes.capitol.texas.gov/Docs/PR/htm/PR.51.htm"],
            ["Texas Tax Code, Chapter 34", "https://statutes.capitol.texas.gov/Docs/TX/htm/TX.34.htm"],
        ],
    },
    "Oklahoma": {
        "lead": "Oklahoma sets these rules statewide; each county's treasurer, sheriff and district court carry them out:",
        "items": [
            "Land with taxes unpaid 3 or more years is sold at the county treasurer's resale on the second Monday of June (68 O.S. 3105, 3125). <a href=\"/guides/oklahoma/tax-sales/\">Oklahoma tax sale guide</a>",
            "Mortgage foreclosures usually go through district court and end in a sheriff's sale held at least 30 days after the first published notice (12 O.S. 764). <a href=\"/guides/oklahoma/foreclosure/\">Oklahoma foreclosure guide</a>",
            "Unless appraisal was waived, sheriff's sale bids must reach two-thirds of the appraised value, and the court must confirm the sale. <a href=\"/guides/oklahoma/sheriff-sales/\">Oklahoma sheriff sale guide</a>",
        ],
        "sources": [
            ["Oklahoma Statutes 68 O.S. 3125 (via Justia)", "https://law.justia.com/codes/oklahoma/title-68/section-68-3125/"],
            ["Oklahoma Statutes 12 O.S. 764 (via Justia)", "https://law.justia.com/codes/oklahoma/title-12/section-12-764/"],
        ],
    },
}


def main(csv_path):
    rows = {(r["STATE"], r["COUNTY"]): r for r in csv.DictReader(open(csv_path, encoding="latin-1"))}
    out = []
    for state, abbr, st, lst in [("Texas", "TX", "48", TX), ("Oklahoma", "OK", "40", OK)]:
        for fips, slug, seat, links in lst:
            r = rows[(st, fips)]
            name = r["CTYNAME"]
            p25, p20 = int(r["POPESTIMATE2025"]), int(r["ESTIMATESBASE2020"])
            chg = (p25 - p20) / p20 * 100
            facts = [
                ["County seat", seat],
                ["Population, July 1, 2025 (Census estimate)", f"{p25:,}"],
                ["Population, April 1, 2020 (estimates base)", f"{p20:,}"],
                ["Change since 2020", f"{chg:+.1f}%"],
            ]
            if state == "Texas":
                facts += [
                    ["Property values set by", "The county appraisal district (linked below)"],
                    ["Foreclosure and tax sale day (state law)", "First Tuesday of the month, 10 a.m. to 4 p.m. (first Wednesday if that Tuesday is Jan. 1 or July 4)"],
                ]
                ans = (f"{name} is a Texas county with an estimated {p25:,} residents (Census Bureau, July 1, 2025); its county seat is {seat}. "
                       "Like every Texas county, it holds foreclosure and tax sales on the first Tuesday of the month between 10 a.m. and 4 p.m. "
                       "Property values come from the appraisal district, and foreclosure notices are filed with the county clerk.")
            else:
                facts += [
                    ["Property values set by", "The county assessor"],
                    ["Tax resale (state law)", "Second Monday of June, run by the county treasurer"],
                ]
                ans = (f"{name} is an Oklahoma county with an estimated {p25:,} residents (Census Bureau, July 1, 2025); its county seat is {seat}. "
                       "Its county treasurer holds the annual tax resale on the second Monday of June, and mortgage foreclosures there usually end in a "
                       "court-ordered sheriff's sale after appraisal and published notice.")
            out.append({
                "name": name, "slug": slug, "state": state, "abbr": abbr, "seat": seat,
                "pop2025": p25, "pop2020base": p20, "answer": ans, "facts": facts,
                "links": [list(x) for x in links], "last_checked": CHECKED,
                "sources": [
                    ["U.S. Census Bureau, Vintage 2025 county population estimates (co-est2025-alldata.csv)", CENSUS_CSV],
                    ["U.S. Census Bureau population estimates tables", CENSUS_PAGE],
                    [links[0][0], links[0][1]],
                ],
            })
    doc = {
        "note": "Official facts only. Every county lists sources and a last_checked date. Do not add auction dates or data from the paid TX/OK directory.",
        "state_rules": STATE_RULES,
        "counties": out,
    }
    p = pathlib.Path(__file__).with_name("counties.json")
    p.write_text(json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8")
    print(len(out), "counties written to", p)


if __name__ == "__main__":
    main(sys.argv[1])
