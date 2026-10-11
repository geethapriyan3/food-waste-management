#!/usr/bin/env python3
"""NourishLoop - a single-file local food donation and rescue app.

Run: python nourishloop.py
Requires Python 3.9+. Uses only the standard library. Data is saved in nourishloop.db.
"""
from datetime import datetime
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse
import sqlite3
import webbrowser

DB = Path(__file__).with_name("nourishloop.db")
CATEGORIES = ("Fresh produce", "Bakery", "Packaged food", "Cooked meals", "Dairy", "Other")

def connect():
    db = sqlite3.connect(DB, timeout=10)
    db.row_factory = sqlite3.Row
    return db

def initialize():
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS donations (
          id INTEGER PRIMARY KEY, title TEXT NOT NULL, donor TEXT NOT NULL,
          category TEXT NOT NULL, quantity TEXT NOT NULL, location TEXT NOT NULL,
          pickup_by TEXT NOT NULL, notes TEXT NOT NULL DEFAULT '', contact TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'Available', claimed_by TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS reports (
          id INTEGER PRIMARY KEY, business TEXT NOT NULL, location TEXT NOT NULL,
          details TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS needs (
          id INTEGER PRIMARY KEY, organization TEXT NOT NULL, meals TEXT NOT NULL,
          location TEXT NOT NULL, details TEXT NOT NULL, contact TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        """)
        if not db.execute("SELECT COUNT(*) FROM donations").fetchone()[0]:
            now = datetime.now().isoformat(timespec="minutes")
            samples = [
                ("Fresh veggie boxes", "Green Harvest Market", "Fresh produce", "45 meal portions", "Anna Nagar", "Today 19:30", "Washed seasonal vegetables; bring reusable crates.", "market@example.org", "Available", "", now),
                ("Bakery surplus", "Daily Crust Bakery", "Bakery", "30 meal portions", "T. Nagar", "Today 20:00", "Assorted breads, packed today. Contains wheat.", "bakery@example.org", "Available", "", now),
                ("Community lunch packs", "Gather & Give Events", "Cooked meals", "80 meal portions", "Adyar", "Tomorrow 09:00", "Vegetarian meals, chilled promptly after service.", "events@example.org", "Available", "", now),
            ]
            db.executemany("INSERT INTO donations(title,donor,category,quantity,location,pickup_by,notes,contact,status,claimed_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)", samples)

def esc(value):
    return escape(str(value or ""), quote=True)

def contact_url(value):
    value = str(value or "").strip()
    return ("mailto:" if "@" in value else "tel:") + quote(value, safe="@.+-_")

def options(values, selected=""):
    return "".join(f'<option value="{esc(v)}" {"selected" if v == selected else ""}>{esc(v)}</option>' for v in values)

CSS = """<style>
:root{--ink:#233a32;--muted:#718078;--green:#176447;--deep:#0e5139;--paper:#f7f6ef;--line:#e4e8dd;--orange:#e78158}
*{box-sizing:border-box;scroll-behavior:smooth}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.55 Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif}a{color:inherit}.wrap{max-width:1160px;margin:auto;padding:0 24px}
header{background:#ffffffef;border-bottom:1px solid var(--line);position:sticky;top:0;z-index:5;backdrop-filter:blur(12px)}.nav{min-height:70px;display:flex;align-items:center;justify-content:space-between;gap:18px}.brand{font-size:21px;font-weight:850;letter-spacing:-.8px;text-decoration:none}.brand b{color:var(--green)}nav{display:flex;gap:22px}nav a{text-decoration:none;color:var(--muted);font-weight:650;font-size:13px}nav a:hover{color:var(--green)}
.hero{padding:62px 0 24px;display:grid;grid-template-columns:1.15fr .85fr;gap:36px;align-items:center}.eyebrow{color:var(--green);font-size:11px;font-weight:850;letter-spacing:1.45px;text-transform:uppercase}h1{font-size:clamp(42px,6vw,68px);line-height:.99;letter-spacing:-3px;margin:14px 0 16px}h2{font-size:26px;letter-spacing:-.8px;margin:0 0 5px}.sub{color:var(--muted);max-width:590px;font-size:16px}.hero-art{min-height:250px;border-radius:28px;background:radial-gradient(circle at 75% 20%,#e8f2c7 0 12%,transparent 13%),linear-gradient(145deg,#1c684a,#0d4937);color:white;padding:26px;position:relative;overflow:hidden;display:flex;flex-direction:column;justify-content:space-between;box-shadow:0 18px 45px #134c3520}.hero-art:after{content:'✳';position:absolute;right:25px;top:35px;font-size:120px;color:#ffffff1a}.hero-art strong{font-size:clamp(37px,5vw,54px);line-height:1;letter-spacing:-2px;position:relative;z-index:1}.hero-art span{color:#e0efcc;position:relative;z-index:1}.plate{font-size:54px;position:absolute;right:42px;bottom:40px;z-index:1}
.paths{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:14px 0 28px}.path{background:white;border:1px solid var(--line);border-radius:18px;padding:19px 20px;display:flex;align-items:center;justify-content:space-between;gap:14px;text-decoration:none;transition:.18s}.path:hover{transform:translateY(-2px);box-shadow:0 12px 24px #20352d0c}.path h3{margin:0 0 2px;font-size:17px}.path p{margin:0;color:var(--muted);font-size:13px}.pathicon{font-size:25px;background:#edf4e2;border-radius:13px;width:48px;height:48px;display:grid;place-items:center;flex:none}
.steps{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:0 0 38px}.step{padding:15px 16px;background:#eef3e8;border-radius:14px}.step b{display:block;color:var(--green);font-size:13px}.step span{font-size:12px;color:var(--muted)}.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:0 0 46px}.stat,.card,.formbox{background:white;border:1px solid var(--line);border-radius:18px;padding:19px}.stat b{font-size:25px;display:block}.stat span,.small{color:var(--muted);font-size:13px}section{scroll-margin-top:90px}.sectionhead{display:flex;justify-content:space-between;align-items:end;gap:16px;margin:42px 0 17px}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.card{display:flex;flex-direction:column;min-height:240px;box-shadow:0 5px 18px #233a3208}.tag{display:inline-block;background:#edf4df;color:var(--green);font-size:11px;font-weight:850;padding:5px 10px;border-radius:20px;width:max-content}.card h3{font-size:20px;line-height:1.25;margin:13px 0 4px}.meta{color:var(--muted);font-size:13px;margin:3px 0}.card .bottom{margin-top:auto;padding-top:15px}
button,.button{border:0;background:var(--green);color:white;font:inherit;font-size:13px;font-weight:780;padding:11px 16px;border-radius:11px;cursor:pointer;text-decoration:none;display:inline-block;transition:background .15s,transform .15s}button:hover,.button:hover{background:var(--deep);transform:translateY(-1px)}button:focus-visible,.button:focus-visible,a:focus-visible,input:focus-visible,select:focus-visible,textarea:focus-visible{outline:3px solid #98bc5d;outline-offset:2px}.secondary{background:#edf4e9;color:var(--green)}.secondary:hover{background:#dcebd5;color:var(--deep)}.formbox{margin:42px 0;padding:25px;box-shadow:0 7px 24px #233a3208}.formgrid{display:grid;grid-template-columns:repeat(2,1fr);gap:14px;margin-top:17px}label{display:grid;gap:6px;font-size:13px;font-weight:720}input,select,textarea{font:inherit;padding:11px 12px;border:1px solid #d6ded4;border-radius:10px;background:white;color:var(--ink);width:100%}input::placeholder,textarea::placeholder{color:#9aa79f}textarea{min-height:88px;resize:vertical}.span2{grid-column:span 2}.hint{font-size:12px;color:var(--muted);margin:8px 0}.flash{background:#edf5db;border:1px solid #d0e4ad;padding:12px 16px;border-radius:12px;margin:16px auto 0;color:#33542c;font-weight:650}.filters{display:flex;gap:9px;flex-wrap:wrap;margin:13px 0 16px}.filters input{max-width:260px}.filters select{max-width:190px}.filters a{border:1px solid var(--line);padding:8px 12px;border-radius:10px;background:white;font-size:13px;text-decoration:none;color:var(--muted)}.list{display:grid;gap:10px}.row{background:white;border:1px solid var(--line);padding:15px 17px;border-radius:14px;display:flex;justify-content:space-between;gap:20px;align-items:center}.notice{border-left:3px solid var(--orange);padding:12px 15px;background:#fff1e8;border-radius:0 11px 11px 0;color:#6c5144;font-size:13px;margin-top:15px}footer{margin-top:52px;padding:25px 0;border-top:1px solid var(--line);color:var(--muted);font-size:12px}
@media(max-width:760px){.hero{grid-template-columns:1fr;padding-top:36px;gap:22px}.hero-art{min-height:200px}.grid{grid-template-columns:1fr 1fr}nav{gap:11px}nav a{font-size:12px}}
@media(max-width:540px){.wrap{padding:0 16px}.nav{min-height:62px}.brand span{display:none}nav{gap:10px}nav a{font-size:11px}nav a:nth-child(4){display:none}h1{letter-spacing:-2px}.paths{grid-template-columns:1fr}.grid,.formgrid{grid-template-columns:1fr}.span2{grid-column:auto}.row,.sectionhead{align-items:flex-start;flex-direction:column}.stats .stat{padding:12px}.stat b{font-size:20px}.formbox{padding:18px}.steps{grid-template-columns:1fr}}
</style>"""

def layout(content, message=""):
    flash = f'<div class="flash" role="status">{esc(message)}</div>' if message else ""
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#176447"><title>NourishLoop | Food rescue, made local</title>{CSS}</head><body>
    <header><div class="wrap nav"><a class="brand" href="/">Nourish<b>Loop</b> <span style="font-size:11px;color:#829188">LOCAL FOOD RESCUE</span></a><nav><a href="/#listings">Find food</a><a href="/#donate">Donate food</a><a href="/#need">Post a need</a><a href="/#report">Report surplus</a></nav></div></header>
    <main class="wrap">{flash}{content}</main><footer><div class="wrap">NourishLoop connects local food donors with community organizations. Confirm food condition, allergens, safe handling and pickup directly before handover. Local demo only: it does not verify organizations or send messages.</div></footer></body></html>'''

def home(query="", category="", message=""):
    with connect() as db:
        rows = db.execute("SELECT * FROM donations WHERE status='Available' ORDER BY id DESC").fetchall()
        available = len(rows)
        waiting = db.execute("SELECT COUNT(*) FROM donations WHERE status='Claimed'").fetchone()[0]
        completed = db.execute("SELECT COUNT(*) FROM donations WHERE status='Picked up'").fetchone()[0]
        needs_count = db.execute("SELECT COUNT(*) FROM needs").fetchone()[0]
        needs = db.execute("SELECT * FROM needs ORDER BY id DESC LIMIT 8").fetchall()
        reports = db.execute("SELECT * FROM reports ORDER BY id DESC LIMIT 6").fetchall()
        handovers = db.execute("SELECT * FROM donations WHERE status IN ('Claimed','Picked up') ORDER BY id DESC LIMIT 20").fetchall()
    filtered = [r for r in rows if query.lower() in (r['title']+" "+r['donor']+" "+r['location']+" "+r['notes']).lower() and (not category or r['category']==category)]
    cards = "".join(f'''<article class="card"><span class="tag">{esc(r['category'])}</span><h3>{esc(r['title'])}</h3><div class="meta">{esc(r['donor'])} · {esc(r['location'])}</div><div class="meta"><b>{esc(r['quantity'])}</b> · Pickup by {esc(r['pickup_by'])}</div><p class="small">{esc(r['notes'])}</p><div class="bottom"><p class="hint">Donor: <a href="{esc(contact_url(r['contact']))}">{esc(r['contact'])}</a></p><form method="post" action="/claim" onsubmit="return confirm('Request this food and start coordinating pickup with the donor?')"><input type="hidden" name="id" value="{r['id']}"><label>Your organization<input name="organization" required maxlength="100" placeholder="NGO / community kitchen"></label><button style="margin-top:9px">Request this food</button></form></div></article>''' for r in filtered)
    if not cards:
        cards = '<div class="card"><h3>No available matches</h3><p class="small">Try another search or check back soon.</p></div>'
    need_rows = "".join(f'<div class="row"><div><b>{esc(r["organization"])}</b> · {esc(r["meals"])}<div class="small">{esc(r["location"])} · {esc(r["details"])}</div></div><a href="{esc(contact_url(r["contact"]))}" class="button secondary">Contact organization</a></div>' for r in needs) or '<p class="small">No open requests yet.</p>'
    handover_rows = []
    for r in handovers:
        if r["status"] == "Claimed":
            actions = f'<a class="button secondary" href="{esc(contact_url(r["contact"]))}">Contact donor</a> <form style="display:inline" method="post" action="/pickup"><input type="hidden" name="id" value="{r["id"]}"><button>Mark picked up</button></form>'
        else:
            actions = '<span class="tag">Handover complete</span>'
        handover_rows.append(f'<div class="row"><div><b>{esc(r["title"])}</b> · {esc(r["status"])}<div class="small">Donor: {esc(r["donor"])} · NGO: {esc(r["claimed_by"])} · Pickup: {esc(r["pickup_by"])}</div></div><div>{actions}</div></div>')
    handover_rows = "".join(handover_rows) or '<p class="small">No reservations yet. Request a listing to start a handover.</p>'
    report_rows = "".join(f'<div class="row"><div><b>{esc(r["business"])}</b><div class="small">{esc(r["location"])} · {esc(r["details"])} · {esc(r["created_at"][:16])}</div></div></div>' for r in reports) or '<p class="small">No surplus leads logged.</p>'
    content = f'''<section class="hero"><div><div class="eyebrow">Good food deserves a destination</div><h1>More meals shared.<br>Less food wasted.</h1><p class="sub">A local food rescue board connecting businesses with surplus to NGOs and community kitchens ready to serve it.</p></div><div class="hero-art"><div class="eyebrow" style="color:#d9ee9b">Nourish your neighborhood</div><strong>{available}<br><span style="font-size:22px;letter-spacing:0;color:#e0efcc">donations ready to share</span></strong><div class="plate">🥬</div></div></section>
    <section class="paths" aria-label="Choose how to help"><a class="path" href="/#donate"><span><h3>I have food to share</h3><p>Offer surplus food for a local pickup.</p></span><span class="pathicon">🥕</span></a><a class="path" href="/#listings"><span><h3>I'm looking for food</h3><p>Browse offers and request a donation.</p></span><span class="pathicon">🍲</span></a></section>
    <section class="steps" aria-label="How it works"><div class="step"><b>01 · OFFER OR FIND</b><span>Post available food or browse local listings.</span></div><div class="step"><b>02 · REQUEST & CONNECT</b><span>An NGO requests food and contacts the donor.</span></div><div class="step"><b>03 · PICK UP & CONFIRM</b><span>Coordinate safe pickup and mark the handover complete.</span></div></section>
    <section class="stats"><div class="stat"><b>{available}</b><span>Available listings</span></div><div class="stat"><b>{waiting}</b><span>Awaiting pickup</span></div><div class="stat"><b>{completed}</b><span>Picked up</span></div></section>
    <section id="listings"><div class="sectionhead"><div><div class="eyebrow">Step 1 · Browse and request</div><h2>Food available nearby</h2></div><span class="small">Choose a listing to start a handover</span></div><form class="filters" method="get" action="/"><input name="q" value="{esc(query)}" placeholder="Search food or location"><select name="category"><option value="">All food types</option>{options(CATEGORIES,category)}</select><button>Search listings</button><a href="/">Clear filters</a></form><div class="grid">{cards}</div><div class="notice">Before requesting, confirm allergens, storage, packaging and safe pickup arrangements directly with the donor.</div></section>
    <section id="donate" class="formbox"><div class="eyebrow">Step 1 · For donors</div><h2>Offer surplus food</h2><p class="small">Share clear quantities, a practical pickup deadline and a contact address. Only offer food that can be safely donated.</p><form method="post" action="/donate" class="formgrid"><label>Food title<input name="title" maxlength="100" required placeholder="e.g. boxed vegetarian lunches"></label><label>Donor / business<input name="donor" maxlength="100" required></label><label>Food type<select name="category">{options(CATEGORIES)}</select></label><label>Quantity<input name="quantity" maxlength="80" required placeholder="e.g. 25 portions / 8 kg"></label><label>Pickup location<input name="location" maxlength="120" required></label><label>Pickup by<input name="pickup_by" maxlength="80" required placeholder="Date and time, e.g. 7 Oct 6 PM"></label><label>Contact email or phone<input name="contact" maxlength="120" required></label><label class="span2">Food details, allergens and storage<textarea name="notes" maxlength="500" placeholder="Ingredients, allergens, packed/prepared time, storage conditions"></textarea></label><div class="span2"><button>Publish donation</button></div></form></section>
    <section id="need" class="formbox"><div class="eyebrow">For NGOs and community kitchens</div><h2>Post your food need</h2><p class="small">Let nearby donors know what your organization can collect and when.</p><form method="post" action="/need" class="formgrid"><label>Organization<input name="organization" maxlength="100" required></label><label>Meals / quantity needed<input name="meals" maxlength="80" required placeholder="e.g. 40 meals this evening"></label><label>Pickup area<input name="location" maxlength="120" required></label><label>Contact email or phone<input name="contact" maxlength="120" required></label><label class="span2">What would help?<textarea name="details" maxlength="500" placeholder="Preferred food types, timing, transport capacity"></textarea></label><div class="span2"><button>Post food need</button></div></form></section>
    <section><div class="sectionhead"><div><div class="eyebrow">Step 3 · Complete the handover</div><h2>Reservation and pickup status</h2></div></div><div class="list">{handover_rows}</div><p class="hint">After the donor and NGO coordinate a safe handover, mark the donation as picked up.</p></section>
    <section><div class="sectionhead"><div><div class="eyebrow">Community requests · {needs_count} total</div><h2>Organizations looking for food</h2></div></div><div class="list">{need_rows}</div></section>
    <section id="report" class="formbox"><div class="eyebrow">Prevent the next surplus from going to waste</div><h2>Report a surplus lead</h2><p class="small">Record additional surplus. This local demo does not automatically alert partner organizations.</p><form method="post" action="/report" class="formgrid"><label>Business / event<input name="business" maxlength="100" required></label><label>Location<input name="location" maxlength="120" required></label><label class="span2">What food and when will it be available?<textarea name="details" maxlength="500" required></textarea></label><div class="span2"><button>Log surplus lead</button></div></form></section>
    <section><div class="sectionhead"><div><div class="eyebrow">Community activity</div><h2>Latest surplus leads</h2></div></div><div class="list">{report_rows}</div></section>'''
    return layout(content, message)

class Handler(BaseHTTPRequestHandler):
    def send_page(self, body, status=200):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def form(self):
        size = min(int(self.headers.get("Content-Length", "0")), 20000)
        return {k:v[0].strip() for k,v in parse_qs(self.rfile.read(size).decode("utf-8", "replace"), keep_blank_values=True).items()}

    def do_GET(self):
        p = urlparse(self.path)
        if p.path != "/":
            self.send_page(layout("<h1>Page not found</h1><p><a href='/'>Return home</a></p>"),404)
            return
        query = parse_qs(p.query)
        note = ""
        for part in self.headers.get("Cookie", "").split(";"):
            if part.strip().startswith("nl_notice="):
                note = unquote(part.strip().split("=",1)[1]); break
        self.send_page(home(query.get("q",[""])[0][:100], query.get("category",[""])[0], note))

    def do_POST(self):
        path = urlparse(self.path).path
        data = self.form()
        now = datetime.now().isoformat(timespec="minutes")
        try:
            with connect() as db:
                if path == "/donate":
                    required = ("title","donor","category","quantity","location","pickup_by","contact")
                    if any(not data.get(k) for k in required) or data.get("category") not in CATEGORIES:
                        raise ValueError("Complete all required donation fields and choose a valid food type.")
                    db.execute("INSERT INTO donations(title,donor,category,quantity,location,pickup_by,notes,contact,created_at) VALUES(?,?,?,?,?,?,?,?,?)",(data['title'][:100],data['donor'][:100],data['category'],data['quantity'][:80],data['location'][:120],data['pickup_by'][:80],data.get('notes','')[:500],data['contact'][:120],now))
                    message = "Donation published. Thank you for sharing food locally."
                elif path == "/claim":
                    if not data.get("organization"):
                        raise ValueError("Enter your organization name to request this donation.")
                    cur = db.execute("UPDATE donations SET status='Claimed',claimed_by=? WHERE id=? AND status='Available'",(data['organization'][:100],int(data.get('id','0'))))
                    if not cur.rowcount:
                        raise ValueError("That donation is already requested or no longer available.")
                    message = "Request recorded. Contact the donor to confirm a safe pickup."
                elif path == "/pickup":
                    cur = db.execute("UPDATE donations SET status='Picked up' WHERE id=? AND status='Claimed'",(int(data.get('id','0')),))
                    if not cur.rowcount:
                        raise ValueError("This donation is not awaiting pickup.")
                    message = "Handover marked complete. Thank you for rescuing food."
                elif path == "/need":
                    if any(not data.get(k) for k in ("organization","meals","location","contact")):
                        raise ValueError("Complete the organization, quantity, location and contact fields.")
                    db.execute("INSERT INTO needs(organization,meals,location,details,contact,created_at) VALUES(?,?,?,?,?,?)",(data['organization'][:100],data['meals'][:80],data['location'][:120],data.get('details','')[:500],data['contact'][:120],now))
                    message = "Food need posted. Local donors can now see it and contact you."
                elif path == "/report":
                    if any(not data.get(k) for k in ("business","location","details")):
                        raise ValueError("Complete the business, location and surplus details.")
                    db.execute("INSERT INTO reports(business,location,details,created_at) VALUES(?,?,?,?)",(data['business'][:100],data['location'][:120],data['details'][:500],now))
                    message = "Surplus lead logged. Thank you for helping prevent food waste."
                else:
                    self.send_page(layout("<h1>Page not found</h1>"),404); return
            self.send_response(303)
            self.send_header("Location", "/")
            self.send_header("Set-Cookie", "nl_notice="+quote(message,safe="")+"; Path=/; SameSite=Lax; Max-Age=15")
            self.send_header("Content-Length", "0")
            self.end_headers()
        except (ValueError, sqlite3.Error) as error:
            self.send_page(home(message=str(error)),400)

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args))

def run():
    initialize()
    server = None
    for port in range(8000, 8010):
        try:
            server = ThreadingHTTPServer(("127.0.0.1",port),Handler)
            break
        except OSError:
            continue
    if server is None:
        raise SystemExit("Ports 8000-8009 are busy. Close another NourishLoop window and try again.")
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    print("NourishLoop is ready: " + url)
    print("Data is stored in: " + str(DB))
    print("Keep this window open while using the app. Press Ctrl+C to stop.")
    try:
        webbrowser.open(url)
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nNourishLoop stopped.")
    finally:
        server.server_close()

if __name__ == "__main__":
    run()
