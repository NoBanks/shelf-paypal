"""Record the full demo on a live SHELF: real photos in -> crew feed -> seller price + approve ->
storefront -> PayPal checkout -> paid -> ship -> ledger. Playwright video, headed Chromium.

Usage: python -m scripts.record_full [base_url]
Uses demo_inventory photos for one print (back of frame uploaded FIRST on purpose).
"""
import json
import os
import pathlib
import sys
import time

from playwright.sync_api import sync_playwright

B = (sys.argv[1] if len(sys.argv) > 1 else "https://shelf-paypal.onrender.com").rstrip("/")
INV = pathlib.Path("demo_inventory")
PHOTOS = [str((INV / n).resolve()) for n in ("lone-journey-1c.jpg", "lone-journey-1a.jpg", "lone-journey-1b.jpg")]
NOTES = "5x5 framed art print, black frame. Lone Journey series, piece #44ED2E, 1 of 1. My own artwork."
PRICE = "35"
HOME = pathlib.Path.home()
BUYER = {k: v.strip().strip("'") for k, v in (l.split("=", 1) for l in (HOME / ".paypal" / "sandbox.env").read_text().splitlines() if "=" in l)}
ADMIN = (HOME / ".paypal" / "shelf-admin-token.txt").read_text().strip()
OUT = pathlib.Path(os.environ.get("SHELF_FOOTAGE_DIR", r"C:\Users\machi\OneDrive\Documents\PayPal AI Hackathon\evidence\footage")) / (time.strftime("%Y-%m-%d_%H%M") + "_full")
OUT.mkdir(parents=True, exist_ok=True)
log = []
T0 = time.time()


def shot(name):
    log.append({"t": round(time.time() - T0, 1), "shot": name})
    print(f"[{log[-1]['t']:6.1f}s] {name}", flush=True)


def current_pp(ctx, main):
    live = [x for x in ctx.pages if not x.is_closed() and "sandbox.paypal.com" in x.url]
    if live:
        return live[-1]
    if any("sandbox.paypal.com" in fr.url for fr in main.frames):
        return main
    return None


def find(getter, sels, timeout=20000, exact_button=None):
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
    pg.goto(B + "/healthz", timeout=120000)

    # 1. dashboard: photos in with seller notes + price
    pg.goto(B + "/", wait_until="networkidle", timeout=120000); pg.wait_for_timeout(2500); shot("dashboard")
    pg.set_input_files("#photos", PHOTOS); pg.wait_for_timeout(1800); shot("photos selected (back of frame first)")
    pg.click("#notes"); pg.type("#notes", NOTES, delay=25); pg.wait_for_timeout(600)
    pg.click("#sprice"); pg.type("#sprice", PRICE, delay=120); pg.wait_for_timeout(1000)
    with pg.expect_response(lambda r: r.url.endswith("/api/items") and r.request.method == "POST") as ri:
        pg.click("#upbtn")
    iid = ri.value.json()["item_id"]
    shot(f"uploaded {iid}; crew working")

    # 2. watch the live crew feed until the draft is ready
    t_up = time.time()
    while time.time() - t_up < 300:
        st = pg.evaluate(f"() => {{ const c = document.getElementById('card-{iid}'); return c ? c.querySelector('.status').innerText : '' }}")
        if st and st.lower() != "processing":
            break
        time.sleep(1.5)
    shot(f"draft ready after {time.time()-t_up:.0f}s")
    pg.wait_for_timeout(1500)
    pg.locator(f"#card-{iid}").scroll_into_view_if_needed(); pg.wait_for_timeout(5000)
    shot("draft card: AI suggestion + comps + seller price")
    pg.locator(f"#card-{iid} button:has-text('Approve')").click(); pg.wait_for_timeout(3500); shot("approved, live")

    # 3. storefront + item page
    pg.goto(B + "/store", wait_until="networkidle", timeout=120000); pg.wait_for_timeout(3500); shot("storefront: real prints")
    pg.goto(B + f"/store/{iid}", wait_until="networkidle", timeout=120000); pg.wait_for_timeout(2000)
    find(lambda: pg, ["#paypal-button:not([hidden])"], 30000); pg.wait_for_timeout(3500); shot("item page with PayPal button")

    # 4. PayPal checkout
    pg.click("#paypal-button"); shot("click Pay with PayPal")
    for _ in range(120):
        if P() is not None:
            break
        time.sleep(0.5)
    time.sleep(3)
    em = find(P, ["#email", "input[type='email']"], 45000)
    em.fill(BUYER["SANDBOX_BUYER_EMAIL"]); time.sleep(0.8)
    nx = find(P, ["#btnNext", "button:has-text('Next')"], 8000)
    if nx:
        nx.click(); time.sleep(2.5)
    pw = find(P, ["#password", "input[type='password']"], 45000)
    pw.fill(BUYER["SANDBOX_BUYER_PASSWORD"]); time.sleep(0.8)
    find(P, ["#btnLogin", "button:has-text('Log In')", "button[type='submit']"], 8000).click()
    time.sleep(7); shot("PayPal review screen")
    pay = None
    for _ in range(10):
        pay = find(P, ["#one-time-cta", "button:has-text('Pay Now')", "button:has-text('Complete Purchase')"], 8000, exact_button="Pay")
        if pay:
            break
        time.sleep(1.5)
    pay.scroll_into_view_if_needed(); time.sleep(1.5); pay.click(); shot("click Pay")
    for _ in range(90):
        if P() is None:
            break
        time.sleep(1)
    pg.wait_for_timeout(3500)
    shot("item page: " + pg.inner_text("#status")[:80].replace("\n", " "))
    pg.wait_for_timeout(3500)

    # 5. dashboard: paid -> ship
    pg.goto(B + "/", wait_until="networkidle", timeout=120000); pg.wait_for_timeout(2500)
    pg.locator(f"#card-{iid}").scroll_into_view_if_needed(); pg.wait_for_timeout(3500); shot("PAID card")
    pg.click(f"#trk-{iid}"); pg.type(f"#trk-{iid}", "9400 1118 9922 3197 4288 11", delay=50); pg.wait_for_timeout(800)
    pg.select_option(f"#car-{iid}", "USPS"); pg.wait_for_timeout(600)
    pg.click(f"#card-{iid} button:has-text('Ship it')"); pg.wait_for_timeout(5000)
    pg.locator(f"#card-{iid}").scroll_into_view_if_needed(); pg.wait_for_timeout(2500)
    shot("card: " + pg.inner_text(f"#card-{iid} .status"))

    # 6. ledger, then shopkeeper note
    pg.goto(B + "/ledger", wait_until="networkidle", timeout=120000); pg.wait_for_timeout(5000); shot("ledger")
    pg.wait_for_timeout(8000)
    pg.goto(B + "/", wait_until="networkidle", timeout=120000); pg.wait_for_timeout(2000)
    pg.locator(f"#card-{iid}").scroll_into_view_if_needed(); pg.wait_for_timeout(4000); shot("shopkeeper note")
    ctx.close(); b.close()

(OUT / "shots.json").write_text(json.dumps(log, indent=1))
print("ITEM:", iid)
print("FOOTAGE DIR:", OUT)
for f in sorted(OUT.glob("*.webm")):
    print("  ", f.name, f.stat().st_size // 1024, "KB")
