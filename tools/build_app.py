"""Builds the phone version of the prospectuses for the MyMISMO app: app/index.html.

    python3 tools/build_app.py            after tools/build.py (build.py runs this itself)
    python3 tools/build_app.py <folder>   reads and writes the pages in another folder

Nothing in the app is typed by hand. It is made from:
  the built pages        (index.html, spring-2027/, fall-2027/, spring-fall-2027/): each program's
                         tiers, prices, benefits, opportunities and built-in availability, the
                         Intake and Availability flow addresses
  tools/template.html    the contract wording (and its version), the audience figures, the quotes
                         and the MISMO logo
  tools/prospectuses.json and catalog.json   each summit's dates and city, package discounts
  tools/app-template.html   the app's own layout and script

Which programs the app offers is set in the Sponsorship Portal (Prospectuses tab, Publish on
MyMISMO) and reaches the app through the public /sponsors/prospectus-app.json (written by the
website's sponsors job). See README.md.
"""
import hashlib, html as H, json, os, re, subprocess, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def must1(pattern, text, flags=re.S):
    m = re.findall(pattern, text, flags)
    if len(m) != 1:
        raise SystemExit("build_app: expected 1 match for %r, found %d" % (pattern[:70], len(m)))
    return m[0]


def tiers_of(page_html):
    """The page's TIERS object, read by node (it is JavaScript, not JSON)."""
    a = page_html.index("  var TIERS = {\n")
    b = page_html.index("\n  };\n", a) + 5
    src = page_html[a:b] + "\nprocess.stdout.write(JSON.stringify(TIERS));\n"
    out = subprocess.run(["node", "-e", src], capture_output=True, text=True)
    if out.returncode:
        raise SystemExit("build_app: could not read TIERS: " + out.stderr[:400])
    return json.loads(out.stdout)


def text(s):
    return H.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def build(repo):
    tpl = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
    app = open(os.path.join(HERE, "app-template.html"), encoding="utf-8").read()
    conf = json.load(open(os.path.join(HERE, "prospectuses.json"), encoding="utf-8"))
    catalog = json.load(open(os.path.join(ROOT, "catalog.json"), encoding="utf-8"))
    pkgs = {p["key"]: p for p in catalog.get("packages", [])}

    main = open(os.path.join(repo, "index.html"), encoding="utf-8").read()
    pages = {"": main}
    for pg in conf["pages"]:
        pages[pg["folder"]] = open(os.path.join(repo, pg["folder"], "index.html"), encoding="utf-8").read()

    submit = must1(r'var SUBMIT_ENDPOINT = "([^"]*)";', main)
    secret = must1(r'var SUBMIT_SECRET = "([^"]*)";', main)
    avail = must1(r'var AVAIL_ENDPOINT = "([^"]*)";', main)

    # ---- the programs, in the order the app lists them
    S = conf["summits"]
    pct = lambda d: int(round(d * 100))
    series_pct = 10   # catalog.json seriesNote: three single-summit prices less 10%
    meta = {
        "series": {"name": "2027 Summit Series", "short": "Series", "when": "Winter, Spring and Fall 2027",
                   "where": "New Orleans, Salt Lake City and Bethesda", "save": series_pct,
                   "blurb": "Your brand at all three 2027 Summits, with the same opportunity at each.",
                   "summits": ["Winter", "Spring", "Fall"], "folder": ""},
        "winter": {"name": "Winter Summit", "short": "Winter", "when": "January 11–14, 2027",
                   "where": "New Orleans, LA", "venue": "InterContinental New Orleans", "city": "New Orleans, LA", "save": 0,
                   "blurb": "Open the year with the industry in New Orleans.", "summits": ["Winter"], "folder": ""},
    }
    for pg in conf["pages"]:
        k = pg["program"]
        if len(pg["summits"]) == 1:
            s = S[pg["summits"][0]]
            meta[k] = {"name": "%s Summit" % pg["summits"][0], "short": pg["summits"][0], "when": text(s["long"]),
                       "where": s["city"], "venue": text(s["venue"]).split(",")[0], "city": s["city"], "save": 0,
                       "blurb": "One summit, one city: %s." % s["city"], "summits": pg["summits"], "folder": pg["folder"]}
        else:
            p = pkgs[pg["package"]]
            meta[k] = {"name": "%s Summits" % " & ".join(pg["summits"]), "short": " & ".join(pg["summits"]),
                       "when": " and ".join(text(S[x]["long"]).replace(", 2027", "") for x in pg["summits"]) + ", 2027",
                       "where": " and ".join(S[x]["city"].split(",")[0] for x in pg["summits"]), "save": pct(p["discount"]),
                       "blurb": "The same opportunity at both summits, for sponsors joining after Winter.",
                       "summits": pg["summits"], "folder": pg["folder"], "package": pg["package"]}
    order = ["series", "winter"] + [pg["program"] for pg in conf["pages"]]

    programs = {}
    for k in order:
        m = meta[k]
        page = pages[m["folder"]]
        t = tiers_of(page)[k]
        if len(m["summits"]) == 1:
            m["opens"] = catalog["summits"][m["summits"][0]]["opens"]   # the summit's Monday, for the day picker
        m = dict(m, package=m.get("package", ""), label=t.pop("programLabel"), tiers=t,
                 icon=(S[m["summits"][0]]["icon"] if len(m["summits"]) == 1 and m["summits"][0] in S else ""))
        m.pop("folder")
        programs[k] = m
    groups = {"series-winter": ["series", "winter"]}
    for pg in conf["pages"]:
        groups[pg["folder"].replace("-2027", "")] = [pg["program"]]

    # ---- words and pictures from the template
    contract = must1(r'(<div class="contract-box" data-contract-version="[^"]+">.*?\n    </div>)\n', tpl)
    version = must1(r'data-contract-version="([^"]+)"', contract)
    paras = re.findall(r"<p>.*?</p>", contract, re.S)
    stats = [{"n": text(n), "l": text(l)} for n, l in
             re.findall(r'<div class="stat"><div class="stat-num">(.*?)</div><div class="stat-label">(.*?)</div></div>',
                        must1(r'<div class="stat-grid">(.*?)\n    </div>', tpl))]
    quotes = []
    for q in re.findall(r'<div class="quote">(.*?)\n      </div>\n', must1(r'<div class="quote-stack">(.*?\n)    </div>\n', tpl), re.S):
        img = re.search(r'<img src="(data:image/[^"]+)"', q)
        who = re.search(r'<div class="q-attr"><strong>(.*?)</strong> &middot; (.*?)</div>', q)
        quotes.append({"img": img.group(1) if img else "", "text": text(must1(r"<p>(.*?)</p>", q)),
                       "who": text(who.group(1)), "role": text(who.group(2))})
    if not quotes or not stats:
        raise SystemExit("build_app: no quotes or audience figures found in template.html")
    who_rows = [{"k": text(k), "n": int(n), "o": int(o)} for k, n, o in
                re.findall(r"<title>([^<&]+?) &mdash; (\d+) people from (\d+) organizations</title>", tpl)]
    logo = must1(r'(<symbol id="mismo-logo".*?</symbol>)', tpl)

    data = {"programs": programs, "order": order, "groups": groups, "contractVersion": version,
            "stats": stats, "quotes": quotes, "room": who_rows}
    js = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

    out = app
    for k, v in [("@@DATA@@", js), ("@@SUBMIT_ENDPOINT@@", submit), ("@@SUBMIT_SECRET@@", secret),
                 ("@@AVAIL_ENDPOINT@@", avail), ("@@CONTRACT@@", "\n".join("      " + p.strip() for p in paras)),
                 ("@@CONTRACT_VERSION@@", version), ("@@LOGO@@", logo)]:
        if out.count(k) < 1:
            raise SystemExit("build_app: the app template has no " + k)
        out = out.replace(k, v)
    # the version stamp: a fingerprint of everything above, so the same inputs make the same page
    fp = hashlib.sha1(out.encode("utf-8")).hexdigest()[:8]
    out = out.replace("@@BUILD@@", fp)
    d = os.path.join(repo, "app")
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(out)
    print("wrote", d, len(out), fp)


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else ROOT)
