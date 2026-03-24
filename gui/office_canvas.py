"""
Pixel office — top-down view with animated agents at desks.
Drawn entirely with tkinter Canvas + PhotoImage sprites.
"""
import tkinter as tk
import math, time
from gui import sprites

TILE = 32  # tile size in pixels
COLS, ROWS = 22, 14

# Office layout — character grid
# W=wall F=floor D=desk C=chair B=bookshelf P=plant p=picture c=clock
LAYOUT = [
    "WWWWWWWWWWWWWWWWWWWWWW",
    "WppFFFFFFFFFFFFFFFpcFW",
    "WFFDFDFDFDFFFFFFFRFFW",
    "WFFCFCFCFCFFFFFFFFFFF",
    "WFFFFFFFFFFFFFFFFFFFFFV",
    "WFFDFDFDFDFFFFFFFRFFW",
    "WFFCFCFCFCFFFFFFFFFFF",
    "WFFFFFFFFFFFFFFFFFFFFFFW",
    "WWWWWWWWFWWWWWWWWWWWWW",
    "WFFFBFBFBFFFFFFFFFFF",
    "WFFFFFFFFFFFFFFFFFFFFFV",
    "WFFFFFFFFFFFFFFFFFFFFFV",
    "WFFFFFFFFFFFFFFFFFFFFFV",
    "WWWWWWWWWWWWWWWWWWWWWW",
]

# Desk positions (tile col, tile row) — where agents sit (chair positions)
DESK_SLOTS = [
    (3, 3), (5, 3), (7, 3), (9, 3),   # row 1
    (3, 6), (5, 6), (7, 6), (9, 6),   # row 2
]

# Corresponding desk tile positions (for monitor drawing)
DESK_TILES = [
    (3, 2), (5, 2), (7, 2), (9, 2),
    (3, 5), (5, 5), (7, 5), (9, 5),
]

class OfficeCanvas(tk.Canvas):
    def __init__(self, parent, agent_runner, config, **kw):
        self.cw = COLS * TILE
        self.ch = ROWS * TILE
        super().__init__(parent, width=self.cw, height=self.ch,
                         bg=sprites.FLOOR_COL, highlightthickness=0, **kw)
        self.runner = agent_runner
        self.config = config
        self.agent_sprites = {}   # agent_id -> {img0, img1, canvas_id, bubble_id}
        self._frame = 0
        self._draw_background()
        self._create_agent_sprites()
        self._animate()

    def _draw_background(self):
        """Draw static office elements."""
        for r, row in enumerate(LAYOUT):
            for c in range(min(len(row), COLS)):
                ch = row[c]
                x, y = c * TILE, r * TILE

                if ch == 'W':
                    self.create_rectangle(x, y, x+TILE, y+TILE,
                        fill=sprites.WALL_COL, outline=sprites.WALL_TOP, width=1)
                elif ch in ('F', 'C', ' ', 'V'):
                    # floor — simple tile pattern
                    col = sprites.FLOOR_COL if (r+c) % 2 == 0 else sprites.FLOOR_ALT
                    self.create_rectangle(x, y, x+TILE, y+TILE, fill=col, outline='')
                elif ch == 'D':
                    col = sprites.FLOOR_COL if (r+c) % 2 == 0 else sprites.FLOOR_ALT
                    self.create_rectangle(x, y, x+TILE, y+TILE, fill=col, outline='')
                    sprites.draw_desk(self, x, y, TILE)
                elif ch == 'B':
                    col = sprites.FLOOR_COL if (r+c) % 2 == 0 else sprites.FLOOR_ALT
                    self.create_rectangle(x, y, x+TILE, y+TILE, fill=col, outline='')
                    sprites.draw_bookshelf(self, x, y, TILE)
                elif ch == 'R' or ch == 'r':
                    col = sprites.FLOOR_COL if (r+c) % 2 == 0 else sprites.FLOOR_ALT
                    self.create_rectangle(x, y, x+TILE, y+TILE, fill=col, outline='')
                    sprites.draw_plant(self, x, y, TILE)
                elif ch == 'p':
                    self.create_rectangle(x, y, x+TILE, y+TILE,
                        fill=sprites.WALL_COL, outline=sprites.WALL_TOP, width=1)
                    sprites.draw_picture(self, x, y, TILE)
                elif ch == 'c':
                    self.create_rectangle(x, y, x+TILE, y+TILE,
                        fill=sprites.WALL_COL, outline=sprites.WALL_TOP, width=1)
                    sprites.draw_clock(self, x, y, TILE)
                else:
                    col = sprites.FLOOR_COL if (r+c) % 2 == 0 else sprites.FLOOR_ALT
                    self.create_rectangle(x, y, x+TILE, y+TILE, fill=col, outline='')

        # draw chairs at desk slots
        for col, row in DESK_SLOTS:
            x, y = col * TILE, row * TILE
            sprites.draw_chair(self, x, y, TILE)

        # hallway door
        dx, dy = 8*TILE, 8*TILE
        self.create_rectangle(dx+4, dy+2, dx+TILE-4, dy+TILE-2,
            fill='#654321', outline='#4a2a0a', width=2)
        self.create_oval(dx+TILE-10, dy+TILE//2-2, dx+TILE-6, dy+TILE//2+2,
            fill='#c4a44a', outline='')

    def _create_agent_sprites(self):
        """Create sprite images for each configured agent."""
        agents = self.config.get("agents", [])
        for i, agent in enumerate(agents):
            self._add_agent_sprite(agent, i)

    def _add_agent_sprite(self, agent, slot_idx=None):
        aid = agent["id"]
        if slot_idx is None:
            slot_idx = agent.get("desk", len(self.agent_sprites))
        slot_idx = slot_idx % len(DESK_SLOTS)

        ci = agent.get("color_idx", slot_idx) % len(sprites.SHIRT_COLORS)
        hi = slot_idx % len(sprites.HAIR_STYLES)

        img0 = sprites.create_agent_sprite(self, ci, hi, 0)
        img1 = sprites.create_agent_sprite(self, ci, hi, 1)

        col, row = DESK_SLOTS[slot_idx]
        px = col * TILE + TILE//2 - (8*sprites.SCALE)//2
        py = row * TILE + TILE//2 - (12*sprites.SCALE)//2

        cid = self.create_image(px, py, image=img0, anchor='nw')

        # name label
        nid = self.create_text(px + (8*sprites.SCALE)//2, py + 12*sprites.SCALE + 4,
            text=agent["name"][:8], fill='#ffffff', font=('Courier', 7, 'bold'))
        # name background
        bb = self.bbox(nid)
        if bb:
            nbg = self.create_rectangle(bb[0]-2, bb[1]-1, bb[2]+2, bb[3]+1,
                fill='#2c2137', outline='')
            self.tag_lower(nbg, nid)

        # status bubble (hidden initially)
        bid = self.create_text(px + (8*sprites.SCALE)//2, py - 8,
            text="", fill='#2c2137', font=('Courier', 7), state='hidden')
        bbgid = self.create_rectangle(0,0,0,0, fill='#ffffffdd', outline='#999', state='hidden')

        self.agent_sprites[aid] = {
            'img0': img0, 'img1': img1, 'canvas_id': cid,
            'bubble_id': bid, 'bubble_bg': bbgid,
            'slot': slot_idx, 'px': px, 'py': py,
        }

    def refresh_agents(self):
        """Rebuild agent sprites from config."""
        for aid, data in list(self.agent_sprites.items()):
            self.delete(data['canvas_id'])
            self.delete(data['bubble_id'])
            self.delete(data['bubble_bg'])
        self.agent_sprites.clear()

        # also delete name labels/backgrounds — simplest to clear and redraw
        # Instead, let's track all items. For now, destroy and recreate.
        self.delete('all')
        self._draw_background()
        self._create_agent_sprites()

    def _animate(self):
        """Animation tick — swap frames, update bubbles."""
        self._frame = 1 - self._frame
        agents = self.config.get("agents", [])

        for agent in agents:
            aid = agent["id"]
            if aid not in self.agent_sprites:
                continue
            data = self.agent_sprites[aid]
            state = self.runner.get_state(aid)
            status = self.runner.get_status(aid)

            # swap sprite frame when working
            if state in ("thinking", "working"):
                img = data['img1'] if self._frame else data['img0']
                self.itemconfig(data['canvas_id'], image=img)
                # show bubble
                self.itemconfig(data['bubble_id'], text=status[:15], state='normal')
                self.itemconfig(data['bubble_bg'], state='normal')
                bb = self.bbox(data['bubble_id'])
                if bb:
                    self.coords(data['bubble_bg'], bb[0]-3, bb[1]-2, bb[2]+3, bb[3]+2)
                    self.tag_lower(data['bubble_bg'], data['bubble_id'])
            else:
                self.itemconfig(data['canvas_id'], image=data['img0'])
                if state == "error":
                    self.itemconfig(data['bubble_id'], text="⚠ Error", state='normal', fill='#e74c3c')
                    bb = self.bbox(data['bubble_id'])
                    if bb:
                        self.coords(data['bubble_bg'], bb[0]-3, bb[1]-2, bb[2]+3, bb[3]+2)
                        self.itemconfig(data['bubble_bg'], state='normal')
                elif status == "Done":
                    self.itemconfig(data['bubble_id'], text="✓", state='normal', fill='#2ecc71')
                    bb = self.bbox(data['bubble_id'])
                    if bb:
                        self.coords(data['bubble_bg'], bb[0]-3, bb[1]-2, bb[2]+3, bb[3]+2)
                        self.itemconfig(data['bubble_bg'], state='normal')
                else:
                    self.itemconfig(data['bubble_id'], state='hidden')
                    self.itemconfig(data['bubble_bg'], state='hidden')

        self.after(500, self._animate)
