#!/usr/bin/env python3
"""Generates docs/architecture-lab4.svg: the Lab 4 deployment topology.

Hand-laid rather than auto-arranged, because the interesting part of this
system is which lane a line belongs to -- REST, WebSocket, broker, registry,
telemetry -- and an automatic layout puts them wherever it likes.

Every box is a container in docker-compose.yml. Arrowheads are drawn as
polygons rather than SVG markers, and every label is a <text> element, so the
file renders the same in a browser, in Preview and in anything that embeds it.
"""

import math
import pathlib
import subprocess
import tempfile

W, H = 1880, 980

INK = "#1F2933"
MUTED = "#64748B"
FAINT = "#94A3B8"

PANEL_F, PANEL_S = "#F8FAFC", "#E2E8F0"
PLAT_F, PLAT_S, PLAT_T = "#EEF2FF", "#818CF8", "#3730A3"
SVC_F, SVC_S, SVC_T = "#ECFDF5", "#34D399", "#065F46"
DB_F, DB_S, DB_T = "#F1F5F9", "#A3AEBE", "#475569"
BRK_F, BRK_S, BRK_T = "#FFFBEB", "#FBBF24", "#92400E"
MON_F, MON_S, MON_T = "#FDF4FF", "#D8B4FE", "#6B21A8"

C_REST = "#334155"
C_WS = "#0E7490"
C_BROKER = "#B45309"
C_DISC = "#4F46E5"
C_TEL = "#9333EA"

FONT = "'Helvetica Neue',Helvetica,Arial,sans-serif"
MONO = "'SF Mono',Menlo,Consolas,monospace"

out = []
add = out.append


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text(x, y, s, size=12, fill=INK, weight="normal", anchor="start", font=FONT):
    add(f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" '
        f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{esc(s)}</text>')


def rect(x, y, w, h, fill, stroke, r=8, sw=1.4, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" ry="{r}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')


def cylinder(x, y, w, h, fill, stroke, sw=1.3):
    rx, ry = w / 2, 9
    add(f'<path d="M {x},{y+ry} V {y+h-ry} A {rx},{ry} 0 0 0 {x+w},{y+h-ry} V {y+ry}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
    add(f'<ellipse cx="{x+rx}" cy="{y+ry}" rx="{rx}" ry="{ry}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')


def line(d, stroke, sw=1.6, dash=None):
    da = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{sw}" '
        f'stroke-linecap="round" stroke-linejoin="round"{da}/>')


def head(x, y, deg, color, size=10):
    """An arrowhead with its tip at (x, y), pointing along deg (0 = right)."""
    a = math.radians(deg)
    tri = [(0, 0), (-size, size * 0.42), (-size, -size * 0.42)]
    pts = [(x + px * math.cos(a) - py * math.sin(a),
            y + px * math.sin(a) + py * math.cos(a)) for px, py in tri]
    d = " ".join(f"{px:.1f},{py:.1f}" for px, py in pts)
    add(f'<polygon points="{d}" fill="{color}"/>')


def arrow(d, stroke, tip, deg, sw=1.6, dash=None, size=10):
    line(d, stroke, sw, dash)
    head(tip[0], tip[1], deg, stroke, size)


def label(x, y, lines, size=11.5, fill=None, anchor="middle", font=FONT, weight="normal"):
    """Text on a white plate, so a line may pass underneath it."""
    fill = fill or MUTED
    wch = size * 0.57
    wmax = max(len(l) for l in lines) * wch
    lh = size + 3
    bh = lh * len(lines) + 5
    bx = {"middle": x - wmax / 2, "start": x, "end": x - wmax}[anchor] - 5
    add(f'<rect x="{bx:.1f}" y="{y-size:.1f}" width="{wmax+10:.1f}" height="{bh:.1f}" '
        f'rx="3" ry="3" fill="#FFFFFF" fill-opacity="0.94"/>')
    for i, l in enumerate(lines):
        text(x, y + i * lh, l, size=size, fill=fill, anchor=anchor, font=font, weight=weight)


# ---------------------------------------------------------------- canvas ----
add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
    f'viewBox="0 0 {W} {H}">')
add(f'<rect width="{W}" height="{H}" fill="#FFFFFF"/>')

text(40, 44, "Student ID, please — Lab 4 deployment topology", 21, INK, "bold")
text(40, 68, "Every box is a container in docker-compose.yml. Ports are the published ones.",
     12.5, MUTED)

# --------------------------------------------------------------- column A ---
rect(70, 100, 200, 54, "#FFFFFF", FAINT, r=27)
text(170, 124, "Client", 14, INK, "bold", "middle")
text(170, 141, "browser · Postman", 11, MUTED, "normal", "middle")

rect(40, 210, 260, 104, PLAT_F, PLAT_S)
text(170, 236, "Gateway", 15, PLAT_T, "bold", "middle")
text(170, 255, "Python / FastAPI · one instance", 10.5, MUTED, "normal", "middle")
text(170, 275, "published 8080 → public 8000", 11, INK, "normal", "middle", MONO)
text(170, 292, "internal 8001 · no database", 11, INK, "normal", "middle", MONO)
text(170, 307, "validates tokens · GET /logs, the system's log", 10.5, MUTED, "normal", "middle")

rect(40, 400, 260, 130, PLAT_F, PLAT_S)
text(170, 426, "Service Discovery", 15, PLAT_T, "bold", "middle")
text(170, 445, "Python / FastAPI · registry in memory", 10.5, MUTED, "normal", "middle")
text(170, 467, "POST /register", 11, INK, "normal", "middle", MONO)
text(170, 484, "GET /status every 5s", 11, INK, "normal", "middle", MONO)
text(170, 501, "GET /services · GET /metrics", 11, INK, "normal", "middle", MONO)
text(170, 519, "removes what stops answering", 10.5, MUTED, "normal", "middle")

# --------------------------------------------------------- services panel ---
PX, PY, PW, PH = 340, 100, 930, 432
rect(PX, PY, PW, PH, PANEL_F, PANEL_S, r=12)
# (the panel's heading is drawn last, over the lines that cross it)

COLS = [460, 660, 860, 1060]
CW = 180

ROWS = [
    (PY + 62, [
        ("Session", "shift, roles, current applicant", "session-db"),
        ("Discord DMs", "channels per session", "dm-db"),
        ("Player", "accounts, friends, XP", "player-db"),
        ("Moderation", "accept / reject / flag / ban", "moderation-db"),
    ]),
    (PY + 252, [
        ("Applicant", "who is at the door", "applicant-db"),
        ("Credential", "are the documents sound", "credential-db"),
        ("University Record", "the hidden truth", "university-record-db"),
        ("Server Rules", "the rules of the day", "server-rules-db"),
    ]),
]

svc = {}
for by, cells in ROWS:
    for cx, (name, blurb, db) in zip(COLS, cells):
        rect(cx + 7, by + 7, CW, 62, "#FFFFFF", SVC_S, r=7, sw=1)
        rect(cx + 3.5, by + 3.5, CW, 62, "#FFFFFF", SVC_S, r=7, sw=1)
        rect(cx, by, CW, 62, SVC_F, SVC_S, r=7)
        text(cx + CW / 2, by + 25, name, 13, SVC_T, "bold", "middle")
        text(cx + CW / 2, by + 42, blurb, 10, MUTED, "normal", "middle")
        text(cx + CW - 10, by + 56, "× 2", 10, SVC_S, "bold", "end")
        dy = by + 92
        line(f"M {cx+CW/2},{by+69} V {dy}", DB_S, 1.2)
        cylinder(cx + 28, dy, CW - 56, 48, DB_F, DB_S)
        text(cx + CW / 2, dy + 32, db, 10, DB_T, "normal", "middle", MONO)
        svc[name] = (cx, by, CW, 62)

text(PX + 20, PY + PH - 14,
     "postgres:17, one per service, data in a named volume  ·  a service and its database "
     "share a private network", 10.5, FAINT)
text(PX + PW - 20, PY + PH - 14, "two replicas each by default", 10.5, FAINT, "normal", "end")

# ----------------------------------------------------------------- broker ---
BX, BY, BW, BH = 340, 584, 930, 128
rect(BX, BY, BW, BH, BRK_F, BRK_S, r=12)
text(BX + 28, BY + 36, "Message Broker", 16, BRK_T, "bold")
text(BX + 28, BY + 60, "HTTP 8000   ·   gRPC 9001", 12, INK, "normal", "start", MONO)
text(BX + 28, BY + 82, "one queue per topic · retries · dead letters", 11.5, MUTED)
text(BX + 28, BY + 102, "picks the instance and gives up on a failing one — so no service "
     "carries a circuit breaker of its own", 10.5, MUTED)
cylinder(BX + BW - 160, BY + 24, 120, 76, "#FFFFFF", BRK_S)
text(BX + BW - 100, BY + 70, "broker-data", 10, BRK_T, "normal", "middle", MONO)
text(BX + BW - 100, BY + 116, "queues survive a restart", 10, FAINT, "normal", "middle")

# ------------------------------------------------------------- monitoring ---
MX, MY, MW, MH = 1310, 100, 530, 612
rect(MX, MY, MW, MH, MON_F, MON_S, r=12, dash="6 4")
text(MX + 24, MY + 26, "Logs, traces, monitoring", 14, MON_T, "bold")
text(MX + 24, MY + 44, "Loki and Promtail always run; the rest with --profile monitoring", 10, MUTED,
     "normal", "start")

PT = (MX + 30, MY + 56, 220, 78)
rect(*PT, "#FFFFFF", MON_S, r=8)
text(MX + 140, MY + 84, "Promtail", 13, MON_T, "bold", "middle")
text(MX + 140, MY + 102, "lists containers through", 10, MUTED, "normal", "middle")
text(MX + 140, MY + 116, "the Docker API", 10, MUTED, "normal", "middle")

PR = (MX + 280, MY + 56, 220, 78)
rect(*PR, "#FFFFFF", MON_S, r=8)
text(MX + 390, MY + 84, "Prometheus", 13, MON_T, "bold", "middle")
text(MX + 390, MY + 102, "scrape_interval 5s", 10, MUTED, "normal", "middle", MONO)
text(MX + 390, MY + 116, "one target, not eight", 10, MUTED, "normal", "middle")

cylinder(MX + 60, MY + 210, 160, 76, "#FFFFFF", MON_S)
text(MX + 140, MY + 256, "Loki", 13, MON_T, "bold", "middle")
text(MX + 140, MY + 306, "loki-data", 10, FAINT, "normal", "middle", MONO)

rect(MX + 110, MY + 390, 270, 92, "#FFFFFF", MON_S, r=8)
text(MX + 245, MY + 422, "Grafana", 15, MON_T, "bold", "middle")
text(MX + 245, MY + 442, "localhost:3300", 11, INK, "normal", "middle", MONO)
text(MX + 245, MY + 460, "System Overview · Logs dashboards", 10, MUTED, "normal", "middle")

TE = (MX + 280, MY + 150, 220, 68)
rect(*TE, "#FFFFFF", MON_S, r=8)
text(MX + 390, MY + 176, "Tempo", 13, MON_T, "bold", "middle")
text(MX + 390, MY + 194, "one request as a timeline", 10, MUTED, "normal", "middle")
text(MX + 390, MY + 208, "OTLP/HTTP :4318", 10, MUTED, "normal", "middle", MONO)

text(MX + 24, MY + MH - 46, "Logs and metrics join on instance_id, the container id:", 10.5, MUTED)
text(MX + 24, MY + MH - 30, "it is on every log line and on every reading. traceId joins", 10.5, MUTED)
text(MX + 24, MY + MH - 14, "a line to its trace, and the trace to every line it wrote.", 10.5, MUTED)

arrow(f"M {MX+140},{MY+134} V {MY+204}", MUTED, (MX + 140, MY + 210), 90, 1.4)
label(MX + 176, MY + 174, ["push"], 10, MUTED, "middle")
arrow(f"M {MX+140},{MY+286} C {MX+140},{MY+350} {MX+180},{MY+356} {MX+205},{MY+384}",
      MUTED, (MX + 210, MY + 390), 55, 1.4)
arrow(f"M {MX+300},{MY+134} C {MX+300},{MY+150} {MX+250},{MY+150} {MX+250},{MY+190} "
      f"V {MY+330} C {MX+250},{MY+360} {MX+240},{MY+370} {MX+235},{MY+384}",
      MUTED, (MX + 233, MY + 390), 105, 1.4)
arrow(f"M {MX+390},{MY+218} C {MX+390},{MY+320} {MX+330},{MY+340} {MX+300},{MY+384}",
      MUTED, (MX + 296, MY + 390), 125, 1.4)

# ------------------------------------------------------------------ edges ---
# Client -> Gateway
arrow("M 170,154 V 204", C_REST, (170, 210), 90, 2.4)
label(238, 186, ["REST", "published 8080"], 11, C_REST, "middle")

# Client -> Session and Discord DMs: straight to the service, past the Gateway
sx = svc["Session"][0] + CW / 2 - 34
dx = svc["Discord DMs"][0] + CW / 2 - 24
arrow(f"M 272,124 C 360,118 410,140 {sx},{PY+56}", C_WS, (sx + 4, PY + 60), 62, 1.8, "7 5", 9)
arrow(f"M 272,112 C 430,66 580,74 {dx},{PY+56}", C_WS, (dx + 4, PY + 60), 68, 1.8, "7 5", 9)
label(398, 150, ["WS 3011-3013"], 11, C_WS, "middle")
label(640, 86, ["WS 3002-3004"], 11, C_WS, "middle")

# Gateway -> services, and back in through the internal listener: the calls
# between services that did not move to the broker are still REST through 8001.
arrow("M 300,242 H 442", C_REST, (450, 242), 0, 3.2, size=12)
label(376, 230, ["REST · to one instance"], 10.5, C_REST, "middle")
arrow("M 450,288 H 308", C_REST, (300, 288), 180, 2.0)
label(378, 308, ["internal 8001", "service to service"], 10.5, C_REST, "middle")

# services <-> broker
arrow("M 620,532 V 578", C_BROKER, (620, 584), 90, 3.2, size=12)
label(620, 562, ["requests · events"], 11, C_BROKER, "middle")
arrow("M 980,584 V 538", C_BROKER, (980, 532), 270, 3.2, size=12)
label(980, 562, ["POST /broker/deliver  ·  gRPC 9001"], 11, C_BROKER, "middle")

# Gateway <-> Service Discovery
arrow("M 150,314 V 394", C_DISC, (150, 400), 90, 1.6, "5 4", 9)
label(150, 360, ["GET /services"], 11, C_DISC, "middle")
arrow("M 76,400 C 54,368 54,344 74,320", C_DISC, (78, 314), 310, 1.6, "5 4", 8)
label(54, 358, ["GET", "/status"], 9.5, C_DISC, "middle")

# services <-> Service Discovery, through the panel's left margin
arrow(f"M {PX},470 C 322,470 318,478 307,483", C_DISC, (300, 486), 160, 1.6, "5 4", 9)
label(400, 462, ["POST /register, with topics"], 10.5, C_DISC, "middle")
arrow(f"M 300,424 C 322,424 320,392 333,390", C_DISC, (340, 389), 352, 1.6, "5 4", 9)
label(398, 374, ["GET /status, every 5s"], 10.5, C_DISC, "middle")

# broker -> Service Discovery
arrow(f"M {BX},{BY+64} H 214 V 536", C_DISC, (214, 530), 270, 1.6, "5 4", 9)
label(276, 602, ["GET /services", "GET /topics"], 10.5, C_DISC, "middle")

# every container -> Promtail
arrow(f"M {PX+PW},{PY+76} H {MX+24}", C_TEL, (MX + 30, PY + 76), 0, 1.6, "2 4", 9)
label(MX - 24, PY + 64, ["stdout of every container"], 10.5, C_TEL, "middle")

# every service -> Tempo: its spans
arrow(f"M {PX+PW},{MY+184} H {MX+274}", C_TEL, (MX + 280, MY + 184), 0, 1.6, "2 4", 9)
label(MX - 24, MY + 172, ["spans"], 10.5, C_TEL, "middle")

# Loki -> the Gateway: GET /logs reads the system's log from Loki. Round the
# bottom of the drawing, clear of the services panel.
arrow(f"M {MX+60},{MY+230} H {MX-10} V 740 H 24 V 262 H 34", C_TEL, (40, 262), 0, 1.6, "2 4", 9)
label(700, 732, ["GET /logs on the Gateway reads from Loki what came through the broker"], 11, C_TEL, "middle")

# The broker -> Loki: every service's lines, sent as LogBatch events on the
# `logs` topic, written into Loki as source="broker".
arrow(f"M {BX+BW},{BY+40} H {MX-22} V {MY+270} H {MX+54}", C_TEL, (MX + 60, MY + 270), 0, 1.6, "2 4", 9)
label(MX + 22, MY + 262, ["logs topic"], 10.5, C_TEL, "middle")

# Service Discovery -> Prometheus
# Up the panel's right margin and into Prometheus's side, clear of Tempo.
arrow(f"M 118,530 V 756 H {MX+520} V {MY+95} H {MX+506}", C_TEL, (MX + 500, MY + 95), 180, 1.6, "2 4", 9)
label(770, 756, ["GET /metrics  —  Service Discovery has already asked every instance for "
                 "GET /status, so one scrape covers the whole system"], 11, C_TEL, "middle")

# The services panel's heading, last, so the WebSocket lines pass behind it.
label(PX + 20, PY + 26, ["Eight domain services"], 14, INK, "start", weight="bold")
label(PX + 186, PY + 26,
      ["·  top row: while a shift is running   ·   "
       "bottom row: deciding on one applicant"], 11.5, MUTED, "start")

# ------------------------------------------------------------------ legend ---
LY = 798
rect(40, LY, W - 80, 142, "#FFFFFF", PANEL_S, r=10)
text(64, LY + 30, "Reading the lines", 13, INK, "bold")

legend = [
    (C_REST, None, 3.0, "REST, synchronous. The Gateway picks one instance of the service it routes to."),
    (C_WS, "7 5", 1.8, "WebSocket, straight to the service. The Gateway negotiates the URL, then stands aside."),
    (C_BROKER, None, 3.0, "Through the broker. The caller names an operation; the broker chooses the instance."),
    (C_DISC, "5 4", 1.6, "The registry. Who is running, who is still answering, which topics each one takes."),
    (C_TEL, "2 4", 1.6, "Telemetry: logs, spans and metrics. Loki and Promtail always run; the rest only with the monitoring profile."),
]
for i, (color, dash, sw, caption) in enumerate(legend):
    ly = LY + 58 + i * 18
    line(f"M 64,{ly} H 118", color, sw, dash)
    head(126, ly, 0, color, 9)
    text(142, ly + 4, caption, 11, INK)

text(952, LY + 30, "What is not drawn", 13, INK, "bold")
notes = [
    "Which service calls which. Five of those calls go through the broker now; the table in the README names each one, with its operation and transport.",
    "The nine Compose networks: one per service, shared with its database alone, plus backend, where the Gateway, the broker and Service Discovery meet them.",
    "Replicas past the default two. docker compose up -d --scale player=4 changes nothing here: an instance registers itself, and Promtail finds it.",
    "The Gateway never registers, because it is the thing that reads the registry. Service Discovery probes it anyway, through METRICS_EXTRA_INSTANCES.",
]
for i, n in enumerate(notes):
    text(952, LY + 58 + i * 18 + 4, "·   " + n, 10.5, MUTED)

add("</svg>")

here = pathlib.Path(__file__).resolve().parent
png = here / "images" / "architecture-lab4.png"

# This file is the source; images/architecture-lab4.png is the only artifact
# kept beside it. The SVG in between is written to a temporary directory and
# thrown away, so there is never a second copy of the drawing to fall behind
# this one. Drawn at 2x, because GitHub and a lab report both scale a large
# raster down more kindly than they scale a small one up.
svg = "\n".join(out).replace(f'width="{W}" height="{H}"',
                             f'width="{W*2}" height="{H*2}"', 1)
with tempfile.TemporaryDirectory() as tmp:
    scratch = pathlib.Path(tmp) / "architecture-lab4.svg"
    scratch.write_text(svg)
    # sips ships with macOS; rsvg-convert or Inkscape would do as well.
    subprocess.run(["sips", "-s", "format", "png", str(scratch), "--out", str(png)],
                   check=True, capture_output=True)
print(f"wrote {png.relative_to(here.parent)} ({W*2}x{H*2})")
