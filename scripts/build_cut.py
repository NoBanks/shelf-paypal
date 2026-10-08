"""Assemble the demo film from raw Playwright recordings with ffmpeg (captions baked in, 1920x1080, 24fps).

Edit SEGMENTS below. Each segment: source file (or 'card'), in/out seconds, caption, optional crop.
Usage: python -m scripts.build_cut <footage_dir> <out.mp4> [--music track.wav]
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

FF = r"C:\Users\machi\Downloads\ffmpeg-8.0.1-essentials_build_CLEAN\bin\ffmpeg.exe"
FONT = "C\\:/Windows/Fonts/bahnschrift.ttf"
FONT_BODY = "C\\:/Windows/Fonts/arial.ttf"
BG = "0x0c120e"
MINT = "0x7fd4a8"
W, H, FPS = 1920, 1080, 24


def esc(t: str) -> str:
    return t.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\u2019").replace("%", "\\%")


def card(lines: list[tuple[str, int, str]], dur: float) -> tuple[str, str]:
    """A title/end card. lines: (text, fontsize, color). Returns (input_args, filter)."""
    inp = f"-f lavfi -t {dur} -r {FPS} -i color=c={BG}:s={W}x{H}"
    n = len(lines)
    draws = []
    total = sum(fs * 1.4 for _, fs, _ in lines)
    y = (H - total) / 2
    for text, fs, color in lines:
        draws.append(f"drawtext=fontfile='{FONT}':text='{esc(text)}':fontsize={fs}:fontcolor={color}:x=(w-text_w)/2:y={int(y)}")
        y += fs * 1.4
    return inp, ",".join(draws)


def seg(src: str, t_in: float, t_out: float, caption: str, crop: str | None = None) -> tuple[str, str]:
    inp = f"-ss {t_in} -t {t_out - t_in} -i \"{src}\""
    f = []
    if crop:
        f.append(f"crop={crop}")
    f.append(f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color={BG},fps={FPS},setsar=1")
    if caption:
        f.append(f"drawtext=fontfile='{FONT}':text='{esc(caption)}':fontsize=44:fontcolor=white:"
                 f"box=1:boxcolor={BG}@0.78:boxborderw=18:x=(w-text_w)/2:y=h-150")
    return inp, ",".join(f)


def build(footage: pathlib.Path, out: pathlib.Path, music: str | None = None) -> None:
    M = str(footage / "main_flow.mp4")
    P = str(footage / "paypal_window.mp4")
    ship_dir = sorted(footage.parent.glob("*_ship"))
    S = str(ship_dir[-1] / "ship.mp4") if ship_dir and (ship_dir[-1] / "ship.mp4").exists() else None

    SEGMENTS = [
        card([("SHELF x PayPal", 120, MINT), ("Photos in, PayPal money out.", 56, "white"),
              ("An agent crew that lists your stuff, prices it honestly, and closes the sale.", 34, "0x94b3a2")], 4.0),
        seg(M, 2.5, 9.0, "Everyone owns a shelf of money. The agents do the selling."),
        seg(M, 9.0, 13.0, "Flaws disclosed, right above the PayPal button."),
        seg(P, 0.0, 6.0, "A buyer clicks Pay with PayPal.", crop="520:800:0:0"),
        seg(P, 6.0, 13.0, "Orders v2: create the order, buyer approves.", crop="520:800:0:0"),
        seg(P, 13.0, 21.0, "Complete Purchase. PayPal captures it.", crop="520:800:0:0"),
        seg(M, 120.5, 126.5, "The sale books itself. PayPal capture id on screen."),
        seg(M, 128.0, 130.5, "Seller sees PAID, net after fees, buyer email."),
    ]
    if S:
        SEGMENTS.append(seg(S, 2.0, 12.0, "Type the tracking number. SHOPKEEPER posts it to PayPal, buyer notified."))
    else:
        SEGMENTS.append(seg(M, 130.5, 139.5, "Type the tracking number. Ship it. PayPal notifies the buyer."))
    SEGMENTS += [
        seg(M, 144.5, 150.5, "Every dollar lands in a ledger keyed by the PayPal capture id."),
        seg(M, 158.0, 162.0, "SHOPKEEPER wrote the buyer note. BOOKKEEPER reconciles against PayPal."),
        card([("Google ADK + Gemini crew", 56, "white"), ("PayPal Orders v2, JS SDK v6, webhooks", 56, "white"),
              ("57 offline tests. Live on Render.", 56, "white")], 4.0),
        card([("SHELF x PayPal", 110, MINT), ("shelf-paypal.onrender.com", 60, "white"),
              ("an agent crew by NoBanks Nearby", 36, "0x94b3a2")], 5.0),
    ]

    inputs, filters, labels = [], [], []
    for i, (inp, f) in enumerate(SEGMENTS):
        inputs.append(inp)
        filters.append(f"[{i}:v]{f}[v{i}]")
        labels.append(f"[v{i}]")
    n = len(SEGMENTS)
    fc = ";".join(filters) + ";" + "".join(labels) + f"concat=n={n}:v=1:a=0[outv]"
    cmd = f'"{FF}" -y -loglevel error ' + " ".join(inputs)
    if music:
        cmd += f' -i "{music}"'
    cmd += f' -filter_complex "{fc}" -map "[outv]"'
    if music:
        cmd += f' -map {n}:a -shortest -c:a aac -b:a 192k'
    cmd += f' -c:v libx264 -preset medium -crf 19 -pix_fmt yuv420p -r {FPS} "{out}"'
    print(cmd[:300], "...")
    subprocess.run(cmd, shell=True, check=True)
    probe = subprocess.run(f'"{FF}" -i "{out}"', shell=True, capture_output=True, text=True).stderr
    print([l.strip() for l in probe.splitlines() if "Duration" in l])


if __name__ == "__main__":
    footage = pathlib.Path(sys.argv[1])
    out = pathlib.Path(sys.argv[2])
    music = sys.argv[4] if len(sys.argv) > 4 and sys.argv[3] == "--music" else None
    build(footage, out, music)
