"""Builds every sponsorship prospectus from ONE template.

    python3 tools/build.py            writes the pages into this repo
    python3 tools/build.py <folder>   writes them somewhere else (the checks do this)

  tools/template.html      the 2027 Series + Winter prospectus, as written by hand. Change
                           wording, layout or benefits HERE, never in a built page: a built
                           page that differs from what this script makes fails the checks.
  tools/prospectuses.json  which pages exist (folder, summits, package), each summit's dates
                           and hotel, and the built-in availability snapshot.
  catalog.json             prices. A package's price is its summits' prices less its discount.

To add a prospectus: add a page to tools/prospectuses.json (and, for a new combination of
summits sold at a discount, a package to catalog.json), run this, run the checks, publish the
new folder. To change a price: edit catalog.json, run the sponsorship repo's
tests/apply-catalog.js (it updates the template too), then run this.
"""
import re, sys, os, json

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO = sys.argv[1] if len(sys.argv) > 1 else ROOT
os.makedirs(REPO, exist_ok=True)
SRC = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
CONF = json.load(open(os.path.join(HERE, "prospectuses.json"), encoding="utf-8"))
CATALOG = json.load(open(os.path.join(ROOT, "catalog.json"), encoding="utf-8"))
PACKAGES = {p["key"]: p for p in CATALOG.get("packages", [])}


def must(pattern, text, count=1, flags=0):
    n = len(re.findall(pattern, text, flags))
    if n != count:
        raise SystemExit("expected %d match(es) for %r, found %d" % (count, pattern[:80], n))


def sub1(pattern, repl, text, flags=0, count=1):
    must(pattern, text, count, flags)
    return re.sub(pattern, repl, text, flags=flags)


def rep1(old, new, text, count=1):
    n = text.count(old)
    if n != count:
        raise SystemExit("expected %d of %r, found %d" % (count, old[:80], n))
    return text.replace(old, new)


# ---------------------------------------------------------------------------
# 1. The summit-aware availability code, shared by all three pages.
# ---------------------------------------------------------------------------
AVAIL_START = "  function applyAvailability(rows){"
AVAIL_END = "  (function liveAvailability(){"

NEW_AVAIL = r'''  /* ---- which summit each program on this page sells (November 2026) ---------
     The Spring and Fall 2027 prospectuses are their own pages, built from this
     one. A slot belongs to a summit: a Series sponsor holds it at Winter, Spring
     and Fall, a single-summit sponsor only at theirs. The Availability flow sends
     each taken slot's Program (and, for a custom Series package, its per-summit
     Summit Lines), so each page counts only what is gone at its own summit. A
     Series tier needs the slot free at all three. */
  var SEASONS = ["Winter","Spring","Fall"];
  /* the summits each program sells: a Series needs the slot free at all three, a package
     (Spring & Fall) at each of its own */
  var PROGRAM_SEASONS = {winter:["Winter"], spring:["Spring"], fall:["Fall"], series:SEASONS, springfall:["Spring","Fall"]};
  var DAY_ABBR = {Monday:"Mon", Tuesday:"Tue", Wednesday:"Wed", Thursday:"Thu", Friday:"Fri"};

  function seasonOf(v){
    var m = /(Winter|Spring|Fall|Series)/i.exec(cellText(v));
    return m ? m[1].charAt(0).toUpperCase() + m[1].slice(1).toLowerCase() : "";
  }
  /* Summit Lines: a custom Series package's own slot at each summit, as JSON
     [{"s":"Spring","tier":"PLATINUM","opp":"AI Demo / Case Study Sponsor","day":""}] */
  function parseLines(v){
    var s = cellText(v).trim();
    if(!s) return null;
    try{ var a = JSON.parse(s); return (Array.isArray(a) && a.length) ? a : null; }catch(e){ return null; }
  }
  function slotKey(tier, opp){
    return /^\s*diamond\s*$/i.test(cellText(tier)) ? "diamond" : oppKey(cellText(opp));
  }
  /* every slot one row takes: [{season, key, day}] */
  function slotsOf(r, legacy){
    var key = slotKey(r.tier, r.opportunity);
    var day = dayName(r.day) || dayName(r.opportunity);
    var all = function(){ return SEASONS.map(function(s){ return {season:s, key:key, day:day}; }); };
    if(legacy) return all();
    var se = seasonOf(r.program);
    if(se === "Series"){
      var lines = parseLines(r.lines);
      if(!lines) return all();
      return lines.map(function(l){
        return {season: seasonOf(l.s), key: slotKey(l.tier, l.opp), day: dayName(l.day) || dayName(l.opp)};
      });
    }
    return se ? [{season:se, key:key, day:day}] : [];
  }

  function applyAvailability(rows){
    if(!Array.isArray(rows)) return false;
    /* Before the flow sent Program, every row counted everywhere. That is still
       right for a Winter + Series page, but a Spring or Fall page can't tell a
       Winter-only sale from its own, so it keeps its built-in snapshot. */
    var legacy = !rows.some(function(r){ return r && Object.prototype.hasOwnProperty.call(r, "program"); });
    if(legacy && rows.length && !LEGACY_OK) return false;

    var taken = {}, days = {};
    SEASONS.forEach(function(s){ taken[s] = {}; days[s] = {}; });
    rows.forEach(function(r){
      if(!r) return;
      slotsOf(r, legacy).forEach(function(sl){
        if(!sl.key || !taken[sl.season]) return;
        taken[sl.season][sl.key] = (taken[sl.season][sl.key] || 0) + 1;
        if(sl.day) (days[sl.season][sl.key] = days[sl.season][sl.key] || {})[sl.day] = 1;
      });
    });
    function seasonsFor(prog){ return PROGRAM_SEASONS[prog] || []; }
    function countFor(prog, key){
      return Math.max.apply(null, seasonsFor(prog).map(function(s){ return taken[s][key] || 0; }));
    }
    function daysFor(prog, key){
      var out = {};
      seasonsFor(prog).forEach(function(s){ Object.keys(days[s][key] || {}).forEach(function(d){ out[d] = 1; }); });
      return out;
    }

    PROGRAM_ORDER.forEach(function(prog){
      TIER_ORDER.forEach(function(tid){
        var t = TIERS[prog][tid];
        if(!t) return;
        if(!t.opportunities){
          /* Diamond: the tier is the slot */
          if(t.cap !== undefined && t.oppName){
            var d = noteFor(t.cap, countFor(prog, "diamond"));
            t.avail = d.sold ? "Sold" : (d.note + " · exclusive");
            t.soldOut = d.sold;
          }
          return;
        }
        t.opportunities.forEach(function(o){
          var k = oppKey(o.name);
          if(o.days){
            var gone = daysFor(prog, k);
            var sold = o.days.filter(function(d){ return gone[d]; });
            o.soldDays = sold;
            /* a slot held with no day chosen yet (a custom Series line) still counts */
            var r2 = noteFor(o.days.length, Math.max(sold.length, countFor(prog, k)));
            o.note = r2.note; o.sold = r2.sold;
          } else {
            var r3 = noteFor(o.cap, countFor(prog, k));
            o.note = r3.note; o.sold = r3.sold;
          }
        });
      });
    });

    /* repaint the reserve page, the tier pages and the snapshot table */
    renderTiers(); renderOpportunities(); updateSummary();
    function lookup(prog, k){
      var hit = null;
      TIER_ORDER.forEach(function(tid){
        var t = TIERS[prog][tid]; if(!t || hit) return;
        if(!t.opportunities){
          if(t.oppName && (oppKey(t.oppName) === k || oppKey(t.name) === k))
            hit = {note: t.soldOut ? "Sold" : String(t.avail).split(" · ")[0], sold: !!t.soldOut};
          return;
        }
        t.opportunities.forEach(function(o){ if(!hit && oppKey(o.name) === k) hit = o; });
      });
      return hit;
    }
    document.querySelectorAll(".snap-table tbody tr[data-opp]").forEach(function(tr){
      var k = oppKey(tr.getAttribute("data-opp"));
      var tds = tr.querySelectorAll("td");
      SNAP_COLS.forEach(function(prog, i){
        var o = lookup(prog, k);
        if(o && tds[2 + i]) tds[2 + i].outerHTML = statusCell(o);
      });
    });
    PROGRAM_ORDER.forEach(function(prog){
      var page = document.getElementById(prog);
      if(!page) return;
      page.querySelectorAll(".opp-table tbody tr").forEach(function(tr){
        var tds = tr.querySelectorAll("td");
        if(tds.length < 2) return;
        var o = lookup(prog, oppKey(tds[0].textContent));
        if(!o) return;
        var h;
        if(o.note === "Unlimited") h = "Unlimited";
        else if(o.sold) h = "Sold";
        else {
          var m = /^(\d+ available), (\d+ sold)$/.exec(o.note);
          h = m ? '<span class="part-available">' + m[1] + '</span>, <span class="part-sold">' + m[2] + '</span>' : o.note;
          if(o.days) h += '<span class="opp-days">' + o.days.map(function(d){
            return '<span class="' + ((o.soldDays || []).indexOf(d) >= 0 ? "taken" : "") + '">' + (DAY_ABBR[d] || d) + '</span>';
          }).join("") + '</span>';
        }
        tds[1].innerHTML = h;
        tr.classList.toggle("sold", !!o.sold);
      });
    });
    var stamp = document.getElementById("avail-stamp");
    if(stamp){
      stamp.textContent = "Checked against MISMO's sponsorship record just now.";
      stamp.style.display = "";
    }
    return true;
  }

'''


def patch_availability(html, program_order, snap_cols, legacy_ok):
    a = html.index(AVAIL_START)
    b = html.index(AVAIL_END)
    cfg = ('  var PROGRAM_ORDER = %s;   // the programs this page sells\n'
           '  var SNAP_COLS = %s;       // the Availability table\'s status columns, left to right\n'
           '  var LEGACY_OK = %s;        // see applyAvailability\n'
           % (json.dumps(program_order), json.dumps(snap_cols), "true" if legacy_ok else "false"))
    return html[:a] + cfg + NEW_AVAIL + html[b:]


def set_package(html, key):
    return rep1("  var STORE_KEY =", '  var PACKAGE_KEY = %s;   // a discounted package of summits, or ""\n  var STORE_KEY =' % json.dumps(key), html)


# the payload's Program, in the Sponsorship Requests list's own wording
OLD_PROG = 'program: state.program === "series" ? "Summit Series" : "Winter Summit",'
NEW_PROG = ('program: ({series:"Summit Series", winter:"Winter Summit", spring:"Spring Summit", '
            'fall:"Fall Summit", springfall:"Summit Series"})[state.program] || "Winter Summit",\n'
            '      /* a package of some summits (Spring & Fall) goes to the list as a Series, and the\n'
            '         portal makes it a package of just these summits (November 2026) */\n'
            '      summits: (PROGRAM_SEASONS[state.program] || []).join(","),\n'
            '      package: PACKAGE_KEY,')


# ---------------------------------------------------------------------------
# 2. The existing 2027 page: summit-aware availability, nothing else visible.
# ---------------------------------------------------------------------------
main = patch_availability(SRC, ["winter", "series"], ["series", "winter"], True)
main = rep1(OLD_PROG, NEW_PROG, main)
main = set_package(main, "")
open(os.path.join(REPO, "index.html"), "w", encoding="utf-8").write(main)


# ---------------------------------------------------------------------------
# 3. A standalone single-summit page.
# ---------------------------------------------------------------------------
SUMMITS = {k.lower(): dict(v, Season=k) for k, v in CONF["summits"].items()}
# What is already taken at each summit, shown until the live availability arrives:
# summit key -> {opportunity: (count, [days])}
TAKEN = {k.lower(): {o: (v[0], v[1]) for o, v in t.items()} for k, t in CONF["taken"].items()}
DAY_ABBR = {"Monday": "Mon", "Tuesday": "Tue", "Wednesday": "Wed", "Thursday": "Thu"}


def note_for(cap, n):
    if cap is None:
        return "Unlimited", False
    left = max(0, cap - n)
    if left == 0:
        return "Sold", True
    return ("%d available, %d sold" % (left, n) if n else "%d available" % left), False


def tier_cell(note, sold, days, sold_days):
    if note == "Unlimited":
        return "Unlimited"
    if sold:
        return "Sold"
    m = re.match(r"^(\d+ available), (\d+ sold)$", note)
    h = ('<span class="part-available">%s</span>, <span class="part-sold">%s</span>' % m.groups()) if m else note
    if days:
        h += '<span class="opp-days">' + "".join(
            '<span class="%s">%s</span>' % ("taken" if d in sold_days else "", DAY_ABBR[d]) for d in days) + "</span>"
    return h


def snap_cell(note, sold):
    if note == "Unlimited":
        return '<td class="status-unlimited">Unlimited</td>'
    if sold:
        return '<td class="status-sold">Sold</td>'
    m = re.match(r"^(\d+ available), (\d+ sold)$", note)
    if m:
        return '<td><span class="part-available">%s</span>, <span class="part-sold">%s</span></td>' % m.groups()
    return '<td class="status-available">%s</td>' % note


def money(n):
    return "${:,.0f}".format(n)


def tier_price(tier_key, pkg):
    t = [x for x in CATALOG["tiers"] if x["key"] == tier_key][0]
    if not pkg:
        return t["single"]
    return round(t["single"] * len(pkg["summits"]) * (1 - pkg["discount"]))


def build(spec):
    key = spec["program"]
    seasons = spec["summits"]
    pkg = PACKAGES[spec["package"]] if spec.get("package") else None
    Ss = [SUMMITS[x.lower()] for x in seasons]
    S = Ss[0]
    Season = " & ".join(seasons)                              # "Spring" or "Spring & Fall"
    Summit = "Summit" if len(seasons) == 1 else "Summits"
    pct = int(round(pkg["discount"] * 100)) if pkg else 0
    TierLabel = ("%s Tiers" if pkg else "%s Summit Tiers") % Season
    lowest = min(tier_price(t["key"], pkg) for t in CATALOG["tiers"])
    # at a package, a slot is gone if it is gone at any of its summits
    taken = {}
    for x in seasons:
        for o, (n, days) in TAKEN.get(x.lower(), {}).items():
            n0, d0 = taken.get(o, (0, []))
            taken[o] = (max(n0, n), sorted(set(d0) | set(days), key=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"].index))
    h = SRC

    # --- tab title, masthead
    h = rep1("<title>MISMO 2027 Summit Sponsorship Prospectus</title>",
             "<title>MISMO %s 2027 %s Sponsorship Prospectus</title>" % (Season, Summit), h)
    h = rep1('<span class="eyebrow-m">2027 Summit Series</span>',
             '<span class="eyebrow-m">%s 2027 %s</span>' % (Season, Summit), h)

    # --- left nav: no Series pages, the Winter button becomes this summit's
    h = sub1(r'\n    <button type="button" data-hq="series-overview".*?</button>\n    <button type="button" data-hq="series".*?</button>',
             "", h, flags=re.S)
    h = sub1(r'<button type="button" data-hq="winter" title="Winter Summit Tiers">\s*<svg viewBox="0 0 24 24" aria-hidden="true">.*?</svg>\s*<span>Winter Tiers</span></button>',
             '<button type="button" data-hq="%s" title="%s Summit Tiers">\n      <svg viewBox="0 0 24 24" aria-hidden="true">%s</svg>\n      <span>%s Tiers</span></button>'
             % (key, Season, S["icon"], Season), h, flags=re.S)
    if pkg:
        h = h.replace('title="%s Summit Tiers"' % Season, 'title="%s Tiers"' % Season, 1)
    h = rep1("var PROGRAM_PAGE = {winter:'winter', series:'series'};",
             "var PROGRAM_PAGE = {%s:'%s'};" % (key, key), h)
    h = rep1("var PROGRAM_NAME = {winter:'Winter Summit', series:'2027 Summit Series'};",
             "var PROGRAM_NAME = {%s:'%s %s'};" % (key, Season, Summit), h)

    # --- cover
    h = rep1('<span class="line">2027</span>\n    <span class="line accent">Summit Sponsorship</span>',
             '<span class="line">%s 2027</span>\n    <span class="line accent">Summit Sponsorship</span>' % Season, h)
    if pkg:
        first = ('      <div class="cover-program">\n'
                 '        <div class="cp-label">MISMO 2027 %s Summits</div>\n' % Season +
                 "".join('        <div class="cp-row"><span class="cp-k">%s</span><span class="cp-v">%s &middot; %s</span></div>\n'
                         % (x, SUMMITS[x.lower()]["short"], SUMMITS[x.lower()]["city"]) for x in seasons) +
                 '        <div class="cp-row"><span class="cp-k">Savings</span><span class="cp-v">%d%% off individual rates</span></div>\n'
                 '      </div>\n' % pct)
    else:
        first = ('      <div class="cover-program">\n'
                 '        <div class="cp-label">MISMO 2027 %(Season)s Summit</div>\n'
                 '        <div class="cp-row"><span class="cp-k">Date</span><span class="cp-v">%(long)s</span></div>\n'
                 '        <div class="cp-row"><span class="cp-k">Location</span><span class="cp-v">%(venue)s</span></div>\n'
                 '        <div class="cp-row"><span class="cp-k">Format</span><span class="cp-v">In-person &amp; virtual</span></div>\n'
                 '      </div>\n') % dict(S, Season=Season)
    h = sub1(r'<div class="cover-programs">.*?</div>\n    </div>\n    <div class="cover-contact">',
             ('<div class="cover-programs">\n' + first.replace('%', '%%') +
              '      <div class="cover-program">\n'
              '        <div class="cp-label">Sponsorship</div>\n'
              '        <div class="cp-row"><span class="cp-k">Tiers</span><span class="cp-v">Diamond, Platinum, Gold, Silver, Bronze</span></div>\n'
              '        <div class="cp-row"><span class="cp-k">From</span><span class="cp-v">%s</span></div>\n'
              '        <div class="cp-row"><span class="cp-k">Days</span><span class="cp-v">Monday&ndash;Thursday</span></div>\n'
              '      </div>\n'
              '    </div>\n    <div class="cover-contact">') % money(lowest),
             h, flags=re.S)

    # --- contents
    h = sub1(r'      <a class="toc-row" href="#series-overview">.*?\n      <a class="toc-row" href="#winter">.*?</a>\n',
             '      <a class="toc-row featured" href="#%s"><span class="toc-num">05</span><span class="toc-name">%s</span><span class="toc-dots"></span><span class="toc-page">Page 07</span></a>\n'
             % (key, TierLabel), h, flags=re.S)
    for name, num, page in [("availability", "06", "08"), ("reserve", "07", "09"), ("summary", "08", "10"), ("contract", "09", "11")]:
        h = sub1(r'(<a class="toc-row" href="#%s"><span class="toc-num">)\d\d(</span>.*?<span class="toc-page">Page )\d\d' % name,
                 r'\g<1>%s\g<2>%s' % (num, page), h)

    # --- about: the Series is sold on its own prospectus
    h = rep1("<p>Sponsor once, or join Winter, Spring, and Fall as part of the 2027 Series.</p>",
             ("<p>Sponsor both the %s Summits as one package and save %d%%.</p>" % (" and ".join(seasons), pct)) if pkg else
             "<p>Sponsor the %s Summit, and ask us about the rest of the 2027 Summits.</p>" % Season, h)

    # --- drop the Series overview and Series tiers pages
    h = sub1(r"<!-- 04 SUMMIT SERIES OVERVIEW -->.*?(?=<!-- 06 WINTER TIERS -->)", "", h, flags=re.S)

    # --- the tier page
    h = rep1("<!-- 06 WINTER TIERS -->\n<div class=\"page\" id=\"winter\">",
             "<!-- 05 %s TIERS -->\n<div class=\"page\" id=\"%s\">" % (Season.upper(), key), h)
    h = rep1('<span class="rh-label">Winter Summit Tiers</span>', '<span class="rh-label">%s</span>' % TierLabel, h)
    h = rep1('<div class="kicker"><span class="num">07</span> SPONSORSHIP TIERS</div>\n    <h2 class="page-title">Winter Summit</h2>\n    <div class="program-tag"><span class="pill">SINGLE EVENT</span> January 11&ndash;14, 2027 &middot; New Orleans, LA</div>',
             ('<div class="kicker"><span class="num">05</span> SPONSORSHIP TIERS</div>\n    <h2 class="page-title">%s Summits</h2>\n    <div class="program-tag"><span class="pill">BOTH SUMMITS</span> %s &middot; %d%% package discount included</div>'
              % (Season, " + ".join(seasons), pct)) if pkg else
             '<div class="kicker"><span class="num">05</span> SPONSORSHIP TIERS</div>\n    <h2 class="page-title">%s Summit</h2>\n    <div class="program-tag"><span class="pill">SINGLE EVENT</span> %s &middot; %s</div>'
             % (Season, S["long"], S["city"]), h)

    # tier tables: status cells from what is taken at this summit
    a = h.index('<div class="page" id="%s">' % key)
    b = h.index("<!-- 07 AVAILABILITY -->")
    page = h[a:b]
    caps = {}
    for m in re.finditer(r'\{id:"[a-z]+", name:"([^"]+)", cap:(null|\d+)[^}]*\}', SRC[SRC.index("  var TIERS = {"):SRC.index("    series: {")]):
        dm = re.search(r'days:\[([^\]]*)\]', m.group(0))
        caps[m.group(1)] = (None if m.group(2) == "null" else int(m.group(2)),
                            re.findall(r'"(\w+)"', dm.group(1)) if dm else None)

    def status(name):
        cap, days = caps[name]
        n, sd = taken.get(name, (0, []))
        if days:
            note, sold = note_for(len(days), max(n, len(sd)))
        else:
            note, sold = note_for(cap, n)
        return note, sold, days, sd

    def row(m):
        name = m.group(2)
        if name == "Diamond Exclusive":
            return '<tr><td>Diamond Exclusive</td><td>1 available</td></tr>'
        note, sold, days, sd = status(name)
        cls = ' class="sold"' if sold else (' class="unlimited"' if note == "Unlimited" else "")
        return '<tr%s><td>%s</td><td>%s</td></tr>' % (cls, name, tier_cell(note, sold, days, sd))
    page = re.sub(r'<tr( class="[a-z]+")?><td>([^<]+)</td><td>.*?</td></tr>', row, page)
    if pkg:
        page = re.sub(r'(<div class="t-name">(\w+) Sponsor</div>\s*<div class="t-price">)[^<]*(</div>)',
                      lambda m: m.group(1) + money(tier_price(m.group(2).lower(), pkg)) + m.group(3), page)
    h = h[:a] + page + h[b:]

    # --- availability snapshot: one column, this summit
    h = rep1('<div class="kicker"><span class="num">08</span> AVAILABILITY SNAPSHOT</div>',
             '<div class="kicker"><span class="num">06</span> AVAILABILITY SNAPSHOT</div>', h)
    h = rep1("A quick read on what's already spoken for, across both programs.",
             ("A quick read on what's already spoken for at the %s Summits, including slots held by 2027 Summit Series sponsors. A package needs the slot free at both." % " and ".join(seasons)) if pkg else
             "A quick read on what's already spoken for at the %s Summit, including slots held by 2027 Summit Series sponsors." % Season, h)
    h = rep1("<thead><tr><th>Opportunity</th><th>Tier</th><th>Summit Series</th><th>Winter Summit</th></tr></thead>",
             "<thead><tr><th>Opportunity</th><th>Tier</th><th>%s %s</th></tr></thead>" % (Season, Summit), h)

    def snap(m):
        name, tier = m.group(1), m.group(2)
        if name == "Diamond Sponsor":
            cell = snap_cell("1 available", False)
        else:
            note, sold, _, _ = status(name)
            cell = snap_cell(note, sold)
        return '<tr data-opp="%s"><td>%s</td><td>%s</td>%s</tr>' % (name, name, tier, cell)
    h = re.sub(r'<tr data-opp="([^"]+)"><td>[^<]+</td><td>([^<]+)</td>.*?</tr>', snap, h)

    # --- reserve: one summit, so no program step
    h = rep1('<div class="kicker"><span class="num">09</span> RESERVE YOUR SPONSORSHIP</div>',
             '<div class="kicker"><span class="num">07</span> RESERVE YOUR SPONSORSHIP</div>', h)
    h = rep1("Select a program and tier, then the specific opportunity within it.",
             "Select a tier, then the specific opportunity within it.", h)
    h = rep1("<p>Select a Winter Summit or Summit Series tier, plus any opportunity within it.</p>",
             ("<p>Select a %s package tier, plus any opportunity within it. You hold the same opportunity at both summits.</p>" % Season) if pkg else
             "<p>Select a %s Summit tier, plus any opportunity within it.</p>" % Season, h)
    h = sub1(r'      <div class="form-block" id="block-program">.*?</div>\n      </div>\n\n', "", h, flags=re.S)
    h = rep1("<h3>2. Choose a tier<", "<h3>1. Choose a tier<", h)
    h = rep1("<h3>3. Choose your opportunity<", "<h3>2. Choose your opportunity<", h)
    h = rep1("<h3>4. Your details<", "<h3>3. Your details<", h)

    h = rep1('<div class="kicker"><span class="num">10</span> YOUR SPONSORSHIP SUMMARY</div>',
             '<div class="kicker"><span class="num">08</span> YOUR SPONSORSHIP SUMMARY</div>', h)
    h = rep1('<div class="kicker"><span class="num">11</span> SPONSOR CONTRACT</div>',
             '<div class="kicker"><span class="num">09</span> SPONSOR CONTRACT</div>', h)

    # running-foot page numbers after the two dropped pages
    for old, new in [("09", "07"), ("10", "08"), ("11", "09"), ("12", "10"), ("13", "11")]:
        h = rep1('<span class="rf-num">%s</span>' % old, '<span class="rf-num">@@%s</span>' % new, h)
    h = h.replace('<span class="rf-num">@@', '<span class="rf-num">')

    # --- tier data: this summit only, with its own snapshot
    t0 = h.index("  var TIERS = {\n")
    w0 = h.index("    winter: {\n", t0)
    s0 = h.index("    series: {\n", t0)
    t1 = h.index("  };\n", s0)
    block = h[w0:s0].rstrip()
    if block.endswith("},"):
        block = block[:-1]
    block = block.replace("    winter: {\n", "    %s: {\n" % key, 1)
    block = rep1('programLabel: "MISMO Winter Summit 2027 · Jan 11–14, 2027 · New Orleans, LA",',
                 ('programLabel: "MISMO %s 2027 Summits · %s · %d%% package discount",' % (Season, " and ".join("%s (%s)" % (x["short_js"], x["city"]) for x in Ss), pct)) if pkg else
                 'programLabel: "MISMO %s Summit 2027 · %s · %s",' % (Season, S["short_js"], S["city"]), block)
    if pkg:
        for tk in ["diamond", "platinum", "gold", "silver", "bronze"]:
            block = sub1(r'(\n      %s: \{ name:"[^"]+", price:")[^"]*(")' % tk, r'\g<1>%s\g<2>' % money(tier_price(tk, pkg)), block)

    def opp(m):
        line = m.group(0)
        name = re.search(r'name:"([^"]+)"', line).group(1)
        note, sold, days, sd = status(name)
        line = re.sub(r'note:"[^"]*"', 'note:"%s"' % note, line)
        line = re.sub(r'sold:(true|false)', 'sold:%s' % ("true" if sold else "false"), line)
        if days:
            line = re.sub(r'soldDays:\[[^\]]*\]', "soldDays:[%s]" % ",".join('"%s"' % d for d in sd), line)
        return line
    block = re.sub(r'\{id:"[a-z]+", name:"[^"]+"[^}]*\}', opp, block)
    h = h[:w0] + block + "\n" + h[t1:]

    h = rep1('return { tiers: TIERS, tierOrder: TIER_ORDER, order: ["winter","series"] };',
             'return { tiers: TIERS, tierOrder: TIER_ORDER, order: ["%s"] };' % key, h)
    h = rep1('var state = { program:"winter",', 'var state = { program:"%s",' % key, h)
    h = rep1('var STORE_KEY = "mismo2027.reserve.v1";', 'var STORE_KEY = "mismo2027.%s.reserve.v1";' % key, h)
    h = rep1(OLD_PROG, NEW_PROG, h)
    h = patch_availability(h, [key], [key], False)
    h = set_package(h, spec.get("package") or "")

    # nothing Winter- or Series-specific may survive
    left = [x for x in re.findall(r".{0,60}(?:New Orleans|InterContinental|January 11|Jan 11|Winter Summit|winter:|\"winter\"|Series Tiers|#series).{0,40}", h)
            if "PROGRAM_SEASON" not in x and "Winter Summit\", spring" not in x and "Winter Summit\"," not in x]
    if left:
        print("CHECK", key, *left, sep="\n  ")

    out = os.path.join(REPO, spec["folder"])
    os.makedirs(out, exist_ok=True)
    open(os.path.join(out, "index.html"), "w", encoding="utf-8").write(h)
    print("wrote", out, len(h))


for pg in CONF["pages"]:
    build(pg)
