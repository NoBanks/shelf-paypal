"""Record raw demo footage of the full SHELF x PayPal flow (Playwright video, headed Chromium).

Usage: python -m scripts.record_demo [base_url]   (default http://127.0.0.1:8899)
Reads the sandbox buyer login from ~/.paypal/sandbox.env and the seller token from
~/.paypal/shelf-admin-token.txt. Output: $SHELF_FOOTAGE_DIR/<timestamp>/*.webm + shots.json
(one video per page, the PayPal window is recorded separately when it opens as a popup).
"""
import json
import os
import pathlib
import sys
import time

from playwright.sync_api import sync_playwright

B = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("SHELF_URL", "http://127.0.0.1:8899")).rstrip("/")
ITEM = os.environ.get("SHELF_DEMO_ITEM", "it_demo_lamp")
HOME = pathlib.Path.home()
BUYER = {k: v.strip().strip("'") for k, v in (l.split("=", 1) for l in (HOME / ".paypal" / "sandbox.env").read_text().splitlines() if "=" in l)}
ADMIN = (HOME / ".paypal" / "shelf-admin-token.txt").read_text().strip()
OUT = pathlib.Path(os.environ.get("SHELF_FOOTAGE_DIR", "evidence/footage")) / time.strftime("%Y-%m-%d_%H%M")
OUT.mkdir(parents=True, exist_ok=True)
log = []
T0 = time.time()


def shot(name):
    log.append({"t": round(time.time() - T0, 1), "shot": name})
    print(f"[{log[-1]['t']:6.1f}s] {name}", flush=True)


def current_pp(ctx, main):
    """The PayPal checkout: a separate window (latest open one) or an inline frame in the main page."""
    live = [x for x in ctx.pages if not x.is_closed() and "sandbox.paypal.com" in x.url]
    if live:
        return live[-1]
    if any("sandbox.paypal.com" in fr.url for fr in main.frames):
        return main
    return None


def text_of(pg, n=300):
    try:
        return " | ".join(l.strip() for l in pg.inner_text("body").splitlines() if l.strip())[:n]
    except Exception as e:
        return f"(no body: {e})"


def find(getter, sels, timeout=20000, exact_button=None):
    """Poll for the first visible element matching any selector, re-resolving the page each loop."""
    end = time.time() + timeout / 1000
    while time.time() < end:
        cur = getter()
        if cur is not None:
            for fr in cur.frames:
                for s in sels:
                    loc = fr.locator(s)
                    try:
                        if loc.count() and loc.first.is_visible():
                            return loc.first
                    except Exception:
                        pass
                if exact_button:
                    try:
                        cand = fr.get_by_role("button", name=exact_button, exact=True)
                        if cand.count() and cand.first.is_visible():
                            return cand.first
                    except Exception:
                        pass
        time.sleep(0.4)
    return None


with sync_playwright() as p:
    b = p.chromium.launch(headless=False, args=["--window-size=1300,860"])
    ctx = b.new_context(viewport={"width": 1280, "height": 800}, record_video_dir=str(OUT),
                        record_video_size={"width": 1280, "height": 800})
    ctx.add_init_script(f"localStorage.setItem('shelf_admin', {json.dumps(ADMIN)})")
    pg = ctx.new_page()
    P = lambda: current_pp(ctx, pg)

    # 1. storefront
    pg.goto(B + "/store", wait_until="networkidle", timeout=120000); shot("storefront grid"); pg.wait_for_timeout(3500)
    pg.hover(f"a[href='/store/{ITEM}']"); pg.wait_for_timeout(1200)

    # 2. item page + PayPal button
    pg.goto(B + f"/store/{ITEM}", wait_until="networkidle", timeout=120000); shot("item page loads")
    find(lambda: pg, ["#paypal-button:not([hidden])"], 30000); pg.wait_for_timeout(2500); shot("PayPal button visible")
    pg.mouse.move(760, 600); pg.wait_for_timeout(800)

    # 3. click Pay with PayPal, drive the PayPal checkout
    pg.click("#paypal-button"); shot("click Pay with PayPal")
    for _ in range(120):
        if P() is not None:
            break
        time.sleep(0.5)
    if P() is None:
        pg.screenshot(path=str(OUT / "no_paypal_window.png"))
        raise SystemExit("no PayPal window")
    time.sleep(3)
    shot("PayPal checkout open: " + (P().url[:60] if P() is not pg else "inline"))

    em = find(P, ["#email", "input[type='email']"], 45000)
    if em is None:
        cur = P()
        print("NO EMAIL FIELD. window:", cur.url[:80] if cur else None, "| text:", text_of(cur) if cur else "", flush=True)
        raise SystemExit("no email field")
    em.fill(BUYER["SANDBOX_BUYER_EMAIL"]); time.sleep(0.8)
    nx = find(P, ["#btnNext", "button:has-text('Next')"], 8000)
    if nx:
        nx.click(); time.sleep(2.5)
    pw = find(P, ["#password", "input[type='password']"], 45000)
    if pw is None:
        print("NO PASSWORD FIELD. text:", text_of(P()), flush=True)
        raise SystemExit("no password field")
    pw.fill(BUYER["SANDBOX_BUYER_PASSWORD"]); time.sleep(0.8)
    lg = find(P, ["#btnLogin", "button:has-text('Log In')", "button[type='submit']"], 8000)
    lg.click(); time.sleep(7); shot("PayPal review screen")

    pay = None
    for attempt in range(10):
        pay = find(P, ["#one-time-cta", "button:has-text('Pay Now')", "button:has-text('Complete Purchase')"], 8000, exact_button="Pay")
        if pay:
            break
        cur = P()
        if cur is not None:
            try:
                cur.mouse.wheel(0, 400)
            except Exception:
                pass
            print("  still looking for Pay; text:", text_of(cur, 160), flush=True)
        time.sleep(1.5)
    if pay is None:
        raise SystemExit("Pay button not found")
    pay.scroll_into_view_if_needed(); time.sleep(1.5); pay.click(); shot("click Pay")

    for _ in range(90):
        if P() is None:
            break
        time.sleep(1)
    shot("PayPal checkout closed")
    pg.wait_for_timeout(3000)
    try:
        shot("item page status: " + pg.inner_text("#status")[:90])
    except Exception:
        pass
    pg.wait_for_timeout(4000)

    # 4. dashboard: paid card, ship it
    pg.goto(B + "/", wait_until="networkidle", timeout=120000); pg.wait_for_timeout(3500); shot("dashboard with PAID card")
    pg.click(f"#trk-{ITEM}"); pg.wait_for_timeout(500)
    pg.type(f"#trk-{ITEM}", "9400 1118 9922 3197 4288 11", delay=60); pg.wait_for_timeout(1200)
    pg.select_option(f"#car-{ITEM}", "USPS"); pg.wait_for_timeout(800)
    pg.click(f"#card-{ITEM} button:has-text('Ship it')"); shot("click Ship it")
    pg.wait_for_timeout(6000); shot("dashboard card: " + pg.inner_text(f"#card-{ITEM} .status"))

    # 5. ledger
    pg.goto(B + "/ledger", wait_until="networkidle", timeout=120000); pg.wait_for_timeout(5000); shot("ledger with capture id")

    # 6. shopkeeper note on the card (give the agent time)
    pg.wait_for_timeout(10000)
    pg.goto(B + "/", wait_until="networkidle", timeout=120000); pg.wait_for_timeout(4000); shot("dashboard again (shopkeeper note)")

    ctx.close()
    b.close()

(OUT / "shots.json").write_text(json.dumps(log, indent=1))
print("FOOTAGE DIR:", OUT)
for f in sorted(OUT.glob("*.webm")):
    print("  ", f.name, f.stat().st_size // 1024, "KB")
