"""
Pixel art sprites — drawn programmatically into tkinter PhotoImage.
No image files needed. Each sprite is a character grid mapped to colors.
"""
import tkinter as tk

SCALE = 3  # each pixel = 3x3 screen pixels

# Color palette
P = {
    '.': None,
    'K': '#2c2137',  # outline
    'S': '#f2d2a9',  # skin
    'D': '#dbb88a',  # skin shadow
    'W': '#ffffff',  # whites
    'E': '#2c2137',  # eyes
    'M': '#c47862',  # mouth
    'H': '#4a2a0a',  # hair dark brown
    'L': '#7c4a1e',  # hair light brown
    'R': '#a33b2c',  # hair red
    'G': '#3a3a3a',  # hair gray/black
    'n': '#8b6914',  # pants/neutral
    'x': '#5c4033',  # shoes
}

# Agent body (shirt) colors
SHIRT_COLORS = [
    '#4a90d9',  # blue
    '#e74c3c',  # red
    '#2ecc71',  # green
    '#f39c12',  # orange
    '#9b59b6',  # purple
    '#1abc9c',  # teal
    '#e67e22',  # dark orange
    '#3498db',  # light blue
]

HAIR_STYLES = ['H', 'L', 'R', 'G']

# Agent sitting at desk, facing down (8x12)
AGENT_SIT_0 = [
    "..KKKK..",
    ".K{h}{h}{h}{h}K.",
    ".K{h}{h}{h}{h}K.",
    "KSSDSSDSK"[:8],
    "KSEWWESK",
    "KSSDDSSK",
    ".KSMMMK.",
    "..KKKK..",
    ".K{b}{b}{b}{b}K.",
    ".SK{b}{b}KS.",
    "..K{b}{b}K..",
    "..KnnK..",
]

AGENT_SIT_1 = [  # typing frame
    "..KKKK..",
    ".K{h}{h}{h}{h}K.",
    ".K{h}{h}{h}{h}K.",
    "KSSDSSDSK"[:8],
    "KSEWWESK",
    "KSSDDSSK",
    ".KSMMMK.",
    "..KKKK..",
    ".K{b}{b}{b}{b}K.",
    "SK{b}{b}{b}{b}KS",
    "..K{b}{b}K..",
    "..KnnK..",
]

def _build_sprite_data(template, hair_char, body_color):
    """Replace {h} and {b} in template with actual color chars."""
    rows = []
    for row in template:
        r = row.replace("{h}", hair_char).replace("{b}", "B")
        rows.append(r)
    return rows

def create_agent_sprite(root, color_idx=0, hair_idx=0, frame=0):
    """Create a PhotoImage for an agent sprite."""
    tmpl = AGENT_SIT_0 if frame == 0 else AGENT_SIT_1
    hair = HAIR_STYLES[hair_idx % len(HAIR_STYLES)]
    body_col = SHIRT_COLORS[color_idx % len(SHIRT_COLORS)]

    rows = _build_sprite_data(tmpl, hair, body_col)
    h = len(rows)
    w = max(len(r) for r in rows)

    img = tk.PhotoImage(width=w*SCALE, height=h*SCALE, master=root)

    palette = dict(P)
    palette['B'] = body_col
    palette[hair] = P.get(hair, '#4a2a0a')

    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            color = palette.get(ch)
            if color:
                # draw SCALE x SCALE block
                x0, y0 = x*SCALE, y*SCALE
                # use put with row data for efficiency
                for dy in range(SCALE):
                    img.put(color, to=(x0, y0+dy, x0+SCALE, y0+dy+1))
    return img

# --- Furniture colors ---
FLOOR_COL    = '#d4b896'
FLOOR_ALT    = '#caa87e'
WALL_COL     = '#8b7355'
WALL_TOP     = '#a08060'
DESK_COL     = '#9e7c4f'
DESK_DARK    = '#7a5c33'
MONITOR_BACK = '#555555'
MONITOR_SCR  = '#7ec8e3'
CHAIR_COL    = '#6b4423'
BOOK_COLS    = ['#e74c3c','#3498db','#2ecc71','#f1c40f','#9b59b6']
SHELF_COL    = '#7a5c33'
PLANT_POT    = '#8b4513'
PLANT_GREEN  = '#2d8b46'
PLANT_LIGHT  = '#44c767'
CARPET_COL   = '#6b7b8d'

def draw_desk(canvas, x, y, ts):
    """Draw a desk tile. ts=tile size in pixels."""
    canvas.create_rectangle(x+2, y+2, x+ts-2, y+ts-4, fill=DESK_COL, outline=DESK_DARK, width=1)
    # monitor
    mx, my = x+ts//4, y+2
    mw, mh = ts//2, ts//3
    canvas.create_rectangle(mx, my, mx+mw, my+mh, fill=MONITOR_BACK, outline='#333')
    canvas.create_rectangle(mx+2, my+2, mx+mw-2, my+mh-2, fill=MONITOR_SCR, outline='')
    # monitor stand
    canvas.create_rectangle(mx+mw//2-2, my+mh, mx+mw//2+2, my+mh+4, fill='#555', outline='')

def draw_chair(canvas, x, y, ts):
    s = ts//3
    cx, cy = x+ts//2-s//2, y+ts//4
    canvas.create_rectangle(cx, cy, cx+s, cy+s+2, fill=CHAIR_COL, outline='#4a2a0a')
    canvas.create_rectangle(cx-1, cy-2, cx+s+1, cy+2, fill=CHAIR_COL, outline='#4a2a0a')

def draw_bookshelf(canvas, x, y, ts):
    canvas.create_rectangle(x+2, y+2, x+ts-2, y+ts-2, fill=SHELF_COL, outline=DESK_DARK)
    # books
    bw = (ts-8)//5
    for i in range(5):
        c = BOOK_COLS[i % len(BOOK_COLS)]
        bx = x+4+i*bw
        canvas.create_rectangle(bx, y+4, bx+bw-1, y+ts//2, fill=c, outline='')
        canvas.create_rectangle(bx, y+ts//2+2, bx+bw-1, y+ts-6, fill=BOOK_COLS[(i+2)%5], outline='')

def draw_plant(canvas, x, y, ts):
    cx, cy = x+ts//2, y+ts//2
    # pot
    canvas.create_polygon(cx-6, cy+2, cx+6, cy+2, cx+4, cy+10, cx-4, cy+10, fill=PLANT_POT, outline='#5a2d0c')
    # leaves
    for dx, dy in [(-4,-6),(4,-6),(0,-10),(-6,-2),(6,-2)]:
        canvas.create_oval(cx+dx-3, cy+dy-3, cx+dx+3, cy+dy+3, fill=PLANT_GREEN, outline=PLANT_LIGHT)

def draw_picture(canvas, x, y, ts):
    """Small wall picture."""
    px, py = x+ts//4, y+ts//4
    pw, ph = ts//2, ts//3
    canvas.create_rectangle(px-1, py-1, px+pw+1, py+ph+1, fill='#654321', outline='#4a2a0a')
    canvas.create_rectangle(px, py, px+pw, py+ph, fill='#b8d4e3', outline='')
    # simple landscape
    canvas.create_rectangle(px, py+ph//2, px+pw, py+ph, fill='#5a8f3c', outline='')

def draw_clock(canvas, x, y, ts):
    cx, cy = x+ts//2, y+ts//3
    r = ts//4
    canvas.create_oval(cx-r, cy-r, cx+r, cy+r, fill='#ffffff', outline='#333', width=2)
    canvas.create_line(cx, cy, cx, cy-r+3, fill='#333', width=2)
    canvas.create_line(cx, cy, cx+r-4, cy, fill='#333', width=1)
