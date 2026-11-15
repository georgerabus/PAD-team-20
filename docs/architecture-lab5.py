#!/usr/bin/env python3
"""Generates docs/images/architecture-lab5.png: the Lab 5 deployment topology.

Hand-laid rather than auto-arranged, because the interesting part of this
system is which lane a line belongs to -- REST, WebSocket, broker, registry,
cache, warehouse, telemetry -- and an automatic layout puts them wherever it
likes.

Every box is a container in docker-compose.yml. Arrowheads are drawn as
polygons rather than SVG markers, and every label is a <text> element, so the
file renders the same in a browser, in Preview and in anything that embeds it.
"""

import math
import pathlib
import subprocess
import tempfile

W, H = 1880, 1114

INK = "#1F2933"
MUTED = "#64748B"
FAINT = "#94A3B8"

PANEL_F, PANEL_S = "#F8FAFC", "#E2E8F0"
PLAT_F, PLAT_S, PLAT_T = "#EEF2FF", "#818CF8", "#3730A3"
SVC_F, SVC_S, SVC_T = "#ECFDF5", "#34D399", "#065F46"
DB_F, DB_S, DB_T = "#F1F5F9", "#A3AEBE", "#475569"
BRK_F, BRK_S, BRK_T = "#FFFBEB", "#FBBF24", "#92400E"
MON_F, MON_S, MON_T = "#FDF4FF", "#D8B4FE", "#6B21A8"
CACHE_F, CACHE_S, CACHE_T = "#FEF2F2", "#F87171", "#991B1B"
DW_F, DW_S, DW_T = "#F0FDFA", "#2DD4BF", "#115E59"

C_REST = "#334155"
C_WS = "#0E7490"
C_BROKER = "#B45309"
C_DISC = "#4F46E5"
C_TEL = "#9333EA"
C_CACHE = "#DC2626"
C_DW = "#0F766E"

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

text(40, 44, "Student ID, please — Lab 5 deployment topology", 21, INK, "bold")
text(40, 68, "Every box is a container in docker-compose.yml. Ports are the published ones.",
     12.5, MUTED)

# --------------------------------------------------------------- column A ---
rect(70, 100, 200, 54, "#FFFFFF", FAINT, r=27)
text(170, 124, "Client", 14, INK, "bold", "middle")
text(170, 141, "browser · Postman", 11, MUTED, "normal", "middle")

GY, GH = 210, 118
rect(40, GY, 260, GH, PLAT_F, PLAT_S)
text(170, GY + 26, "Gateway", 15, PLAT_T, "bold", "middle")
text(170, GY + 45, "Python / FastAPI · one instance", 10.5, MUTED, "normal", "middle")
text(170, GY + 65, "published 8080 → public 8000", 11, INK, "normal", "middle", MONO)
text(170, GY + 82, "internal 8001 · no database", 11, INK, "normal", "middle", MONO)
text(170, GY + 97, "validates tokens · GET /logs, the system's log", 10.5, MUTED, "normal", "middle")
text(170, GY + 112, "caches GET answers and tokens", 10.5, MUTED, "normal", "middle")

# The cache: three Valkey nodes that only the Gateway uses. The Gateway picks
# the node for each key on a consistent-hashing ring of its own.
VX, VY, VW, VH = 80, 362, 180, 60
rect(VX + 7, VY + 7, VW, VH, "#FFFFFF", CACHE_S, r=7, sw=1)
rect(VX + 3.5, VY + 3.5, VW, VH, "#FFFFFF", CACHE_S, r=7, sw=1)
rect(VX, VY, VW, VH, CACHE_F, CACHE_S, r=7)
text(VX + VW / 2, VY + 22, "Valkey", 13, CACHE_T, "bold", "middle")
text(VX + VW / 2, VY + 38, "valkey-1 · valkey-2 · valkey-3", 9.5, INK, "normal", "middle", MONO)
text(VX + VW / 2, VY + 52, "allkeys-lru · nothing on disk", 9.5, MUTED, "normal", "middle")

SY, SH = 470, 130
rect(40, SY, 260, SH, PLAT_F, PLAT_S)
text(170, SY + 26, "Service Discovery", 15, PLAT_T, "bold", "middle")
text(170, SY + 45, "Python / FastAPI · registry in memory", 10.5, MUTED, "normal", "middle")
text(170, SY + 67, "POST /register", 11, INK, "normal", "middle", MONO)
text(170, SY + 84, "GET /status every 5s", 11, INK, "normal", "middle", MONO)
text(170, SY + 101, "GET /services · GET /metrics", 11, INK, "normal", "middle", MONO)
text(170, SY + 119, "removes what stops answering", 10.5, MUTED, "normal", "middle")

# --------------------------------------------------------- services panel ---
PX, PY, PW, PH = 340, 100, 930, 520
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
    (PY + 272, [
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
        # The database: three Patroni nodes behind one HAProxy, drawn as one
        # stack, like a service's replicas.
        dy = by + 92
        line(f"M {cx+CW/2},{by+69} V {dy}", DB_S, 1.2)
        cylinder(cx + 28 + 7, dy + 7, CW - 56, 48, "#FFFFFF", DB_S, 1)
        cylinder(cx + 28 + 3.5, dy + 3.5, CW - 56, 48, "#FFFFFF", DB_S, 1)
        cylinder(cx + 28, dy, CW - 56, 48, DB_F, DB_S)
        text(cx + CW / 2, dy + 32, db, 10, DB_T, "normal", "middle", MONO)
        text(cx + CW / 2, dy + 72, "Patroni × 3 · HAProxy", 9.5, FAINT, "normal", "middle")
        svc[name] = (cx, by, CW, 62)

text(PX + 20, PY + PH - 34,
     "Each database: Patroni, a primary and two replicas, one of them synchronous; HAProxy under "
     "the old name — 5432 primary, 5433 replicas", 10.5, FAINT)
text(PX + 20, PY + PH - 16,
     "a service and its database share a private network  ·  two replicas of each service "
     "by default", 10.5, FAINT)

# etcd: the three members every Patroni node keeps its lease in.
EX, EY, EW, EH = PX + PW - 196, PY + PH - 62, 176, 44
rect(EX + 6, EY + 6, EW, EH, "#FFFFFF", DB_S, r=7, sw=1)
rect(EX + 3, EY + 3, EW, EH, "#FFFFFF", DB_S, r=7, sw=1)
rect(EX, EY, EW, EH, DB_F, DB_S, r=7)
text(EX + EW / 2, EY + 19, "etcd × 3", 12, DB_T, "bold", "middle")
text(EX + EW / 2, EY + 35, "elects each cluster's primary", 9.5, MUTED, "normal", "middle")

# ----------------------------------------------------------------- broker ---
BX, BY, BW, BH = 340, PY + PH + 52, 600, 136
rect(BX, BY, BW, BH, BRK_F, BRK_S, r=12)
text(BX + 28, BY + 36, "Message Broker", 16, BRK_T, "bold")
text(BX + 28, BY + 60, "HTTP 8000   ·   gRPC 9001", 12, INK, "normal", "start", MONO)
text(BX + 28, BY + 82, "one queue per topic · retries · dead letters", 11.5, MUTED)
text(BX + 28, BY + 102, "picks the instance, gives up on a failing one", 10.5, MUTED)
text(BX + 28, BY + 122, "saga coordinator: POST /sagas · GET /sagas/{id}", 10.5, BRK_T,
     "normal", "start", MONO)
cylinder(BX + BW - 150, BY + 24, 120, 76, "#FFFFFF", BRK_S)
text(BX + BW - 90, BY + 66, "broker-data", 10, BRK_T, "normal", "middle", MONO)
text(BX + BW - 90, BY + 118, "queues and sagas", 10, FAINT, "normal", "middle")
text(BX + BW - 90, BY + 131, "survive a restart", 10, FAINT, "normal", "middle")

# ------------------------------------------------------------- warehouse ---
# The ETL reads every database's replicas and loads a star schema; Grafana
# reads it. Under the services because that is where its data comes from.
WX, WY, WW, WH = 980, BY, 290, 136
rect(WX, WY, WW, WH, DW_F, DW_S, r=12)
text(WX + WW - 16, WY + 24, "Data warehouse", 14, DW_T, "bold", "end")

ETL = (WX + 16, WY + 38, 124, 66)
rect(*ETL, "#FFFFFF", DW_S, r=8)
text(WX + 78, WY + 60, "ETL", 13, DW_T, "bold", "middle")
text(WX + 78, WY + 76, "Python · every 5 min", 9.5, MUTED, "normal", "middle")
text(WX + 78, WY + 92, "POST /etl/run", 9.5, INK, "normal", "middle", MONO)

cylinder(WX + 166, WY + 36, 108, 70, "#FFFFFF", DW_S)
text(WX + 220, WY + 74, "warehouse-db", 10, DW_T, "normal", "middle", MONO)
text(WX + 220, WY + 90, "star schema", 9.5, MUTED, "normal", "middle")
arrow(f"M {WX+140},{WY+71} H {WX+160}", C_DW, (WX + 166, WY + 71), 0, 2.0, size=8)

text(WX + 16, WY + 120, "never a name, a secret or free text", 9.5, MUTED)

# ------------------------------------------------------------- monitoring ---
MX, MY, MW, MH = 1310, 100, 530, BY + BH - 100
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

GR = (MX + 110, MY + 390, 270, 92)
rect(*GR, "#FFFFFF", MON_S, r=8)
text(MX + 245, MY + 422, "Grafana", 15, MON_T, "bold", "middle")
text(MX + 245, MY + 442, "localhost:3300", 11, INK, "normal", "middle", MONO)
text(MX + 245, MY + 460, "System Overview · Logs · Warehouse", 10, MUTED, "normal", "middle")

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

# Gateway -> Valkey: GET answers and verified tokens, on the Gateway's ring
arrow(f"M 170,{GY+GH} V {VY-6}", C_CACHE, (170, VY), 90, 2.0, size=9)
label(180, GY + GH + 21, ["consistent-hash ring"], 10, C_CACHE, "start")

# services <-> broker
arrow(f"M 620,{PY+PH} V {BY-6}", C_BROKER, (620, BY), 90, 3.2, size=12)
label(620, PY + PH + 30, ["requests · events"], 11, C_BROKER, "middle")
arrow(f"M 840,{BY} V {PY+PH+6}", C_BROKER, (840, PY + PH), 270, 3.2, size=12)
label(840, PY + PH + 30, ["POST /broker/deliver  ·  gRPC 9001"], 11, C_BROKER, "middle")

# every database's replicas -> the ETL
arrow(f"M {WX+60},{PY+PH} V {WY+32}", C_DW, (WX + 60, WY + 38), 90, 2.0, "8 4", 9)
label(WX + 60, PY + PH + 30, ["replicas :5433 · read-only etl"], 10.5, C_DW, "middle")

# warehouse-db -> Grafana, read as grafana_reader
arrow(f"M {WX+WW},{WY+71} H {MX+40} V {MY+460} H {GR[0]-6}", C_DW, (GR[0], MY + 460), 0,
      2.0, "8 4", 9)
label(MX + 48, MY + 560, ["read as", "grafana_reader"], 10, C_DW, "start")

# Gateway <-> Service Discovery, past the cache on its right
arrow(f"M 286,{GY+GH} V {SY-6}", C_DISC, (286, SY), 90, 1.6, "5 4", 9)
label(286, SY - 22, ["GET /services"], 10.5, C_DISC, "middle")
arrow(f"M 64,{SY} C 44,{SY-40} 44,{GY+GH+40} 62,{GY+GH+6}", C_DISC, (66, GY + GH), 300, 1.6,
      "5 4", 8)
label(50, VY + 30, ["GET", "/status"], 9.5, C_DISC, "middle")

# services <-> Service Discovery, through the panel's left margin
arrow(f"M {PX},{SY+70} C 322,{SY+70} 318,{SY+78} 307,{SY+83}", C_DISC, (300, SY + 86), 160,
      1.6, "5 4", 9)
label(400, SY + 62, ["POST /register, with topics"], 10.5, C_DISC, "middle")
arrow(f"M 300,{SY+24} C 322,{SY+24} 320,{SY-8} 333,{SY-10}", C_DISC, (340, SY - 11), 352,
      1.6, "5 4", 9)
label(398, SY - 26, ["GET /status, every 5s"], 10.5, C_DISC, "middle")

# broker -> Service Discovery
arrow(f"M {BX},{BY+64} H 214 V {SY+SH+6}", C_DISC, (214, SY + SH), 270, 1.6, "5 4", 9)
label(276, BY + 30, ["GET /services", "GET /topics"], 10.5, C_DISC, "middle")

# every container -> Promtail
arrow(f"M {PX+PW},{PY+76} H {MX+24}", C_TEL, (MX + 30, PY + 76), 0, 1.6, "2 4", 9)
label(MX - 24, PY + 64, ["stdout of every container"], 10.5, C_TEL, "middle")

# every service -> Tempo: its spans
arrow(f"M {PX+PW},{MY+184} H {MX+274}", C_TEL, (MX + 280, MY + 184), 0, 1.6, "2 4", 9)
label(MX - 24, MY + 172, ["spans"], 10.5, C_TEL, "middle")

# Under the broker and the warehouse, three lines run the width of the drawing.
YB0, YB1, YB2 = BY + BH + 22, BY + BH + 40, BY + BH + 58

# The broker -> Loki: every service's lines, sent as LogBatch events on the
# `logs` topic, written into Loki as source="broker".
arrow(f"M {BX+BW-40},{BY+BH} V {YB0} H {MX-22} V {MY+270} H {MX+54}", C_TEL,
      (MX + 60, MY + 270), 0, 1.6, "2 4", 9)
label(MX + 22, MY + 262, ["logs topic"], 10.5, C_TEL, "middle")

# Loki -> the Gateway: GET /logs reads the system's log from Loki. Round the
# bottom of the drawing, clear of the services panel.
arrow(f"M {MX+60},{MY+230} H {MX-10} V {YB1} H 24 V 262 H 34", C_TEL, (40, 262), 0, 1.6, "2 4", 9)
label(620, YB1 - 8, ["GET /logs on the Gateway reads from Loki what came through the broker"],
      11, C_TEL, "middle")

# Service Discovery -> Prometheus, round the right edge and into its side
arrow(f"M 118,{SY+SH} V {YB2} H {W-24} V {MY+95} H {MX+506}", C_TEL, (MX + 500, MY + 95), 180,
      1.6, "2 4", 9)
label(770, YB2, ["GET /metrics  —  Service Discovery has already asked every instance for "
                 "GET /status, so one scrape covers the whole system"], 11, C_TEL, "middle")

# The services panel's heading, last, so the WebSocket lines pass behind it.
label(PX + 20, PY + 26, ["Eight domain services"], 14, INK, "start", weight="bold")
label(PX + 186, PY + 26,
      ["·  top row: while a shift is running   ·   "
       "bottom row: deciding on one applicant"], 11.5, MUTED, "start")

# ------------------------------------------------------------------ legend ---
LY = YB2 + 32
rect(40, LY, W - 80, 196, "#FFFFFF", PANEL_S, r=10)
text(64, LY + 30, "Reading the lines", 13, INK, "bold")

legend = [
    (C_REST, None, 3.0, "REST, synchronous. The Gateway picks one instance of the service it routes to."),
    (C_WS, "7 5", 1.8, "WebSocket, straight to the service. The Gateway negotiates the URL, then stands aside."),
    (C_BROKER, None, 3.0, "Through the broker. The caller names an operation; the broker chooses the instance."),
    (C_DISC, "5 4", 1.6, "The registry. Who is running, who is still answering, which topics each one takes."),
    (C_CACHE, None, 2.0, "The cache. The Gateway alone uses it; a node that stops answering leaves the ring."),
    (C_DW, "8 4", 2.0, "The warehouse. The ETL reads every database's replicas; Grafana reads what it loaded."),
    (C_TEL, "2 4", 1.6, "Telemetry: logs, spans and metrics. Loki and Promtail always run; the rest only with the monitoring profile."),
]
for i, (color, dash, sw, caption) in enumerate(legend):
    ly = LY + 58 + i * 18
    line(f"M 64,{ly} H 118", color, sw, dash)
    head(126, ly, 0, color, 9)
    text(142, ly + 4, caption, 11, INK)

text(952, LY + 30, "What is not drawn", 13, INK, "bold")
notes = [
    "Which service calls which. All but two go through the broker now; the table in the README names each one, with its operation and transport.",
    "The saga's steps. Applicant creates each applicant by saga, through the broker's coordinator, into Credential, University Record and Applicant.",
    "The networks: one per service with its database, backend where the Gateway, the broker and Service Discovery meet them, one for etcd, one for the warehouse.",
    "Inside a database stack: three Patroni nodes and an HAProxy that asks each node's REST API which one is the primary.",
    "The ETL registers and logs like a service. Replicas past the default two: an instance registers itself, and Promtail finds it.",
    "The Gateway never registers, because it is the thing that reads the registry. Service Discovery probes it anyway, through METRICS_EXTRA_INSTANCES.",
]
for i, n in enumerate(notes):
    text(952, LY + 58 + i * 18 + 4, "·   " + n, 10.5, MUTED)

add("</svg>")

here = pathlib.Path(__file__).resolve().parent
png = here / "images" / "architecture-lab5.png"

# This file is the source; images/architecture-lab5.png is the only artifact
# kept beside it. The SVG in between is written to a temporary directory and
# thrown away, so there is never a second copy of the drawing to fall behind
# this one. Drawn at 2x, because GitHub and a lab report both scale a large
# raster down more kindly than they scale a small one up.
svg = "\n".join(out).replace(f'width="{W}" height="{H}"',
                             f'width="{W*2}" height="{H*2}"', 1)
with tempfile.TemporaryDirectory() as tmp:
    scratch = pathlib.Path(tmp) / "architecture-lab5.svg"
    scratch.write_text(svg)
    # sips ships with macOS; rsvg-convert or Inkscape would do as well.
    subprocess.run(["sips", "-s", "format", "png", str(scratch), "--out", str(png)],
                   check=True, capture_output=True)
print(f"wrote {png.relative_to(here.parent)} ({W*2}x{H*2})")
