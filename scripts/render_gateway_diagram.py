"""Render the proposed topology; requires Pillow. Run from repository root."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

im = Image.new('RGB', (1600, 1050), '#f5f7fb')
d = ImageDraw.Draw(im)
try:
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 23)
    title = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 34)
except OSError:
    font = ImageFont.load_default(size=23)
    title = ImageFont.load_default(size=34)

def box(rect, label, fill='#e0ebfa'):
    d.rounded_rectangle(rect, radius=16, fill=fill, outline='#335574', width=2)
    d.multiline_text((rect[0]+18,rect[1]+18), label, font=font, fill='#152638', spacing=8)

def arrow(points):
    d.line(points, fill='#335574', width=4)
    x,y=points[-1]; px,py=points[-2]
    if x>px: tip=[(x,y),(x-14,y-8),(x-14,y+8)]
    elif x<px: tip=[(x,y),(x+14,y-8),(x+14,y+8)]
    elif y>py: tip=[(x,y),(x-8,y-14),(x+8,y-14)]
    else: tip=[(x,y),(x-8,y+14),(x+8,y+14)]
    d.polygon(tip, fill='#335574')

d.text((45,30),'Lab 2 target architecture - integration pending',font=title,fill='#152638')
d.text((45,85),'Solid arrows describe the intended flow, not a verified running deployment.',font=font,fill='#43566d')
box((50,150,360,245),'Client')
box((480,150,980,270),'Gateway public HTTP :8000\nREST + POST /ws/negotiate')
arrow([(360,195),(480,195)])
box((480,380,980,490),'Service REST listeners\nPrivate - no host port publishing')
arrow([(730,270),(730,380)])
d.text((750,294),'Identity headers; no Bearer',font=font,fill='#152638')
box((1080,380,1550,505),'Gateway internal HTTP :8001\nService-to-service REST\nNot published')
arrow([(980,410),(1080,410)])
arrow([(1080,465),(980,465)])
box((50,380,400,530),'Session WS-only :3011\nPlanned image 2.1.0\nREST remains private :3001', '#fff0cc')
arrow([(140,245),(140,380)])
d.text((50,285),'Direct socket + session token',font=font,fill='#152638')
box((50,640,400,780),'DM WS-only listener\nPort/image pending\n2.1.0 still shares REST/WS', '#fff0cc')
arrow([(70,245),(25,245),(25,685),(50,685)])
box((480,600,1550,785),'Services: Player, Session, Applicant, Credential, Server Rules,\nUniversity Record, Moderation, Discord DMs\n\nEach owns a separate PostgreSQL database on a private network.')
arrow([(730,490),(730,600)])
d.text((50,840),'WS exception: Session and DM validate the session JWT directly at handshake.',font=font,fill='#152638')
d.text((50,885),'Session: query token or Bearer. DM: query token required. Gateway returns no token.',font=font,fill='#152638')
d.text((50,940),'Yellow = owner delivery pending. Existing Compose REST exposure must be migrated together.',font=font,fill='#785300')
Path('docs/images').mkdir(exist_ok=True)
im.save('docs/images/gateway-lab2-target.png')
