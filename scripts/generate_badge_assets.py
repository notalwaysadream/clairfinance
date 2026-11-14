import math
import os
import random
from PIL import Image, ImageDraw, ImageFilter

def make_gradient(width, height, color1, color2, vertical=False):
    base = Image.new('RGB', (width, height), color1)
    top = Image.new('RGB', (width, height), color2)
    mask = Image.new('L', (width, height))
    mask_data = []
    for y in range(height):
        for x in range(width):
            ratio = (y / height) if vertical else (x / width)
            mask_data.append(int(255 * ratio))
    mask.putdata(mask_data)
    base.paste(top, (0, 0), mask)
    return base

def generate_calendar_banner():
    w, h = 1400, 500
    im = make_gradient(w, h, (10, 15, 30), (20, 25, 55))
    draw = ImageDraw.Draw(im, 'RGBA')
    
    for x in range(0, w, 50):
        alpha = int(25 + 30 * math.sin(x / 100))
        draw.line([(x, 0), (x, h)], fill=(34, 211, 238, alpha), width=1)
    for y in range(0, h, 50):
        alpha = int(25 + 30 * math.cos(y / 100))
        draw.line([(0, y), (w, y)], fill=(99, 102, 241, alpha), width=1)
        
    grid_left, grid_top = 750, 60
    cell_w, cell_h = 75, 55
    emojis_colors = [
        (34, 197, 94, 160), (34, 211, 238, 160), (168, 85, 247, 160),
        (245, 158, 11, 160), (99, 102, 241, 160)
    ]
    for r in range(5):
        for c in range(7):
            cx = grid_left + c * (cell_w + 10)
            cy = grid_top + r * (cell_h + 10)
            color = random.choice(emojis_colors) if (r * 7 + c) % 3 != 0 else (255, 255, 255, 30)
            draw.rounded_rectangle([cx, cy, cx + cell_w, cy + cell_h], radius=10, fill=(color[0], color[1], color[2], 40), outline=(color[0], color[1], color[2], 120), width=1)
            draw.ellipse([cx + cell_w - 18, cy + 8, cx + cell_w - 8, cy + 18], fill=color)
            
    points = []
    for x in range(0, w, 20):
        y = int(280 + 90 * math.sin(x * 0.008) + 40 * math.cos(x * 0.015))
        points.append((x, y))
    for i in range(len(points) - 1):
        draw.line([points[i], points[i+1]], fill=(34, 211, 238, 180), width=4)
        
    vignette = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    vdraw = ImageDraw.Draw(vignette)
    vdraw.rectangle([0, 0, w, h], fill=(0, 0, 0, 80))
    return Image.alpha_composite(im.convert('RGBA'), vignette).convert('RGB')

def generate_badge_banner():
    w, h = 1400, 500
    im = make_gradient(w, h, (15, 12, 28), (35, 20, 60))
    draw = ImageDraw.Draw(im, 'RGBA')
    
    cx, cy = 950, 250
    for i in range(36):
        angle = math.radians(i * 10)
        x2 = cx + 800 * math.cos(angle)
        y2 = cy + 800 * math.sin(angle)
        draw.line([(cx, cy), (x2, y2)], fill=(245, 158, 11, 20), width=12)
        
    random.seed(42)
    for _ in range(80):
        bx = random.randint(0, w)
        by = random.randint(0, h)
        br = random.randint(6, 45)
        bcol = random.choice([
            (245, 158, 11, 40), (236, 72, 153, 35), (99, 102, 241, 45), (34, 211, 238, 40)
        ])
        draw.ellipse([bx - br, by - br, bx + br, by + br], fill=bcol)
        
    sx, sy = 950, 250
    shield_pts = [
        (sx - 120, sy - 140), (sx + 120, sy - 140),
        (sx + 110, sy + 30), (sx, sy + 150), (sx - 110, sy + 30)
    ]
    draw.polygon(shield_pts, fill=(245, 158, 11, 60), outline=(251, 191, 36, 200), width=4)
    star_pts = []
    for step in range(10):
        ang = step * math.pi / 5 - math.pi / 2
        r = 55 if step % 2 == 0 else 24
        star_pts.append((sx + r * math.cos(ang), sy + r * math.sin(ang) - 10))
    draw.polygon(star_pts, fill=(255, 255, 255, 190), outline=(245, 158, 11, 255), width=2)
    return im.convert('RGB')

def generate_spider_badge():
    w, h = 1200, 750
    im = make_gradient(w, h, (9, 12, 25), (23, 64, 121))
    draw = ImageDraw.Draw(im, 'RGBA')
    cx, cy = 880, 360
    for ring in range(30, 600, 45):
        pts = []
        for i in range(16):
            ang = math.radians(i * (360 / 16))
            r_dist = ring + 8 * math.sin(i * 2)
            pts.append((cx + r_dist * math.cos(ang), cy + r_dist * math.sin(ang)))
        draw.polygon(pts, fill=None, outline=(229, 35, 53, 90), width=2)
    for i in range(16):
        ang = math.radians(i * (360 / 16))
        draw.line([(cx, cy), (cx + 700 * math.cos(ang), cy + 700 * math.sin(ang))], fill=(229, 35, 53, 110), width=2)
    for x in range(650, w, 28):
        for y in range(0, h, 28):
            draw.regular_polygon((x, y, 12), n_sides=6, rotation=0, fill=(229, 35, 53, 18), outline=(23, 64, 121, 55))
    draw.ellipse([cx - 24, cy - 40, cx + 24, cy + 40], fill=(229, 35, 53, 230), outline=(255, 255, 255, 180), width=2)
    draw.ellipse([cx - 16, cy - 65, cx + 16, cy - 35], fill=(229, 35, 53, 230))
    for side in [-1, 1]:
        for idx, (lx1, ly1, lx2, ly2) in enumerate([(40, -50, 95, -80), (55, -20, 110, -25), (55, 20, 110, 45), (40, 50, 90, 95)]):
            draw.line([(cx + side * 15, cy + (idx - 1.5) * 18), (cx + side * lx1, cy + ly1), (cx + side * lx2, cy + ly2)], fill=(229, 35, 53, 240), width=4)
    return im.convert('RGB')

def generate_bloodborne_badge():
    w, h = 1200, 750
    im = make_gradient(w, h, (11, 9, 11), (40, 19, 25))
    draw = ImageDraw.Draw(im, 'RGBA')
    cx, cy = 880, 375
    for arch_r in range(60, 480, 35):
        draw.arc([cx - arch_r, cy - arch_r - 60, cx + arch_r, cy + arch_r + 140], start=180, end=360, fill=(157, 40, 61, 75), width=2)
        draw.line([(cx, cy - arch_r - 60), (cx, cy + arch_r + 140)], fill=(157, 40, 61, 35), width=1)
    hx, hy = cx, cy - 20
    draw.line([(hx, hy - 140), (hx, hy + 170)], fill=(157, 40, 61, 230), width=8)
    draw.line([(hx - 90, hy - 40), (hx + 90, hy - 40)], fill=(157, 40, 61, 230), width=6)
    draw.line([(hx - 60, hy + 30), (hx + 60, hy + 30)], fill=(157, 40, 61, 230), width=5)
    draw.arc([hx - 70, hy - 70, hx + 70, hy + 70], start=0, end=180, fill=(157, 40, 61, 230), width=6)
    draw.arc([hx - 100, hy - 10, hx + 100, hy + 140], start=180, end=360, fill=(157, 40, 61, 230), width=6)
    random.seed(666)
    for _ in range(120):
        px = random.randint(550, w)
        py = random.randint(0, h)
        pr = random.randint(2, 9)
        draw.ellipse([px - pr, py - pr, px + pr, py + pr], fill=(157, 40, 61, random.randint(30, 110)))
    return im.convert('RGB')

def generate_money_badge():
    w, h = 1200, 750
    im = make_gradient(w, h, (17, 21, 15), (45, 55, 38))
    draw = ImageDraw.Draw(im, 'RGBA')
    cx, cy = 880, 375
    R, r, p = 180, 65, 85
    points = []
    for step in range(720):
        t = step * math.pi / 90
        x = (R - r) * math.cos(t) + p * math.cos((R - r) * t / r)
        y = (R - r) * math.sin(t) - p * math.sin((R - r) * t / r)
        points.append((cx + x, cy + y))
    for i in range(len(points) - 1):
        draw.line([points[i], points[i+1]], fill=(196, 166, 96, 140), width=2)
    R2, r2, p2 = 240, 80, 70
    points2 = []
    for step in range(720):
        t = step * math.pi / 90
        x = (R2 - r2) * math.cos(t) + p2 * math.cos((R2 - r2) * t / r2)
        y = (R2 - r2) * math.sin(t) - p2 * math.sin((R2 - r2) * t / r2)
        points2.append((cx + x, cy + y))
    for i in range(len(points2) - 1):
        draw.line([points2[i], points2[i+1]], fill=(196, 166, 96, 90), width=1)
    draw.ellipse([cx - 160, cy - 160, cx + 160, cy + 160], outline=(196, 166, 96, 210), width=4)
    draw.ellipse([cx - 148, cy - 148, cx + 148, cy + 148], outline=(196, 166, 96, 120), width=1)
    draw.line([(cx - 45, cy - 60), (cx + 45, cy - 60)], fill=(196, 166, 96, 240), width=7)
    draw.line([(cx - 45, cy - 35), (cx + 35, cy - 35)], fill=(196, 166, 96, 240), width=7)
    draw.arc([cx - 50, cy - 60, cx + 30, cy + 10], start=270, end=90, fill=(196, 166, 96, 240), width=7)
    draw.line([(cx - 30, cy + 5), (cx + 45, cy + 75)], fill=(196, 166, 96, 240), width=8)
    random.seed(777)
    for _ in range(90):
        gx = random.randint(550, w)
        gy = random.randint(0, h)
        gr = random.randint(2, 6)
        draw.ellipse([gx - gr, gy - gr, gx + gr, gy + gr], fill=(212, 185, 115, random.randint(50, 160)))
    return im.convert('RGB')

def generate_cute_badge():
    w, h = 1200, 750
    im = make_gradient(w, h, (255, 245, 247), (245, 200, 210))
    draw = ImageDraw.Draw(im, 'RGBA')
    cx, cy = 880, 375
    random.seed(123)
    for _ in range(45):
        bx = random.randint(550, w)
        by = random.randint(0, h)
        br = random.randint(18, 90)
        col = random.choice([
            (233, 136, 166, 45), (255, 182, 193, 60), (255, 228, 225, 80), (221, 160, 221, 35)
        ])
        draw.ellipse([bx - br, by - br, bx + br, by + br], fill=col)
    def draw_star(sx, sy, r, fill):
        pts = []
        for step in range(8):
            ang = step * math.pi / 4
            dist = r if step % 2 == 0 else r * 0.4
            pts.append((sx + dist * math.cos(ang), sy + dist * math.sin(ang)))
        draw.polygon(pts, fill=fill)
    for star_pos, sz in [((cx - 100, cy - 120), 28), ((cx + 120, cy - 100), 32), ((cx - 90, cy + 130), 25), ((cx + 140, cy + 90), 22), ((cx, cy - 170), 20)]:
        draw_star(star_pos[0], star_pos[1], sz, (233, 136, 166, 180))
    draw.ellipse([cx - 110, cy - 50, cx - 10, cy + 50], fill=(233, 136, 166, 180), outline=(180, 80, 110, 100), width=3)
    draw.ellipse([cx + 10, cy - 50, cx + 110, cy + 50], fill=(233, 136, 166, 180), outline=(180, 80, 110, 100), width=3)
    draw.ellipse([cx - 28, cy - 28, cx + 28, cy + 28], fill=(255, 182, 193, 230), outline=(233, 136, 166, 255), width=3)
    draw.polygon([(cx - 15, cy + 15), (cx - 70, cy + 130), (cx - 40, cy + 130), (cx, cy + 30)], fill=(233, 136, 166, 180))
    draw.polygon([(cx + 15, cy + 15), (cx + 70, cy + 130), (cx + 40, cy + 130), (cx, cy + 30)], fill=(233, 136, 166, 180))
    return im.convert('RGB')

# ----------------- NEW VARIATIONS ----------------- #

def generate_cyberpunk_badge():
    w, h = 1200, 750
    # Deep cyber obsidian to dark electric navy
    im = make_gradient(w, h, (10, 10, 20), (25, 15, 45))
    draw = ImageDraw.Draw(im, 'RGBA')
    
    # Futuristic isometric circuit grid lines
    for x in range(600, w + 200, 40):
        draw.line([(x, 0), (x - 200, h)], fill=(0, 240, 255, 25), width=1)
    for y in range(0, h + 200, 40):
        draw.line([(600, y), (w, y - 100)], fill=(252, 238, 10, 25), width=1)
        
    cx, cy = 880, 360
    # Cyber HUD Reticle / Targeting Nodes
    for r in [60, 130, 200, 260]:
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(0, 240, 255, 90), width=2)
    # HUD tick marks
    for deg in range(0, 360, 15):
        rad = math.radians(deg)
        x1 = cx + 240 * math.cos(rad)
        y1 = cy + 240 * math.sin(rad)
        x2 = cx + 260 * math.cos(rad)
        y2 = cy + 260 * math.sin(rad)
        draw.line([(x1, y1), (x2, y2)], fill=(252, 238, 10, 160), width=2)
        
    # Cyberpunk Angular brackets
    bw, bh = 280, 200
    for side in [-1, 1]:
        bx = cx + side * bw
        draw.line([(bx, cy - bh), (bx - side * 40, cy - bh)], fill=(252, 238, 10, 220), width=4)
        draw.line([(bx, cy - bh), (bx, cy - bh + 50)], fill=(252, 238, 10, 220), width=4)
        draw.line([(bx, cy + bh), (bx - side * 40, cy + bh)], fill=(0, 240, 255, 220), width=4)
        draw.line([(bx, cy + bh), (bx, cy + bh - 50)], fill=(0, 240, 255, 220), width=4)
        
    # Tech Glitch bars
    random.seed(2077)
    for _ in range(35):
        gx = random.randint(650, w - 80)
        gy = random.randint(40, h - 40)
        gw = random.randint(40, 180)
        draw.rectangle([gx, gy, gx + gw, gy + 3], fill=(0, 240, 255, random.randint(60, 180)))
        if random.random() > 0.5:
            draw.rectangle([gx + 10, gy + 6, gx + gw - 30, gy + 8], fill=(252, 238, 10, random.randint(80, 210)))
            
    return im.convert('RGB')

def generate_neural_badge():
    w, h = 1200, 750
    # Deep matrix dark emerald
    im = make_gradient(w, h, (2, 18, 12), (10, 45, 30))
    
    # Composite the existing ai.png into the right side if present
    ai_path = 'frontend/assets/ai.png'
    if os.path.exists(ai_path):
        try:
            ai_im = Image.open(ai_path).convert('RGBA')
            ai_im.thumbnail((550, 550), Image.Resampling.LANCZOS)
            # Tint and blend onto base
            im_rgba = im.convert('RGBA')
            paste_x = w - ai_im.width - 40
            paste_y = (h - ai_im.height) // 2
            im_rgba.paste(ai_im, (paste_x, paste_y), ai_im)
            im = im_rgba.convert('RGB')
        except Exception as e:
            print('Could not blend ai.png:', e)
            
    draw = ImageDraw.Draw(im, 'RGBA')
    cx, cy = 880, 375
    # Synaptic Neural Network Nodes & Links
    random.seed(101)
    nodes = [(cx + random.randint(-220, 220), cy + random.randint(-220, 220)) for _ in range(25)]
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            d = math.hypot(nodes[i][0] - nodes[j][0], nodes[i][1] - nodes[j][1])
            if d < 120:
                draw.line([nodes[i], nodes[j]], fill=(16, 185, 129, int(150 * (1 - d / 120))), width=1)
    for nx, ny in nodes:
        draw.ellipse([nx - 5, ny - 5, nx + 5, ny + 5], fill=(52, 211, 153, 200), outline=(255, 255, 255, 180))
        
    return im.convert('RGB')

def generate_batman_badge():
    w, h = 1200, 750
    # Gotham night stealth graphite
    im = make_gradient(w, h, (3, 7, 18), (20, 28, 40))
    draw = ImageDraw.Draw(im, 'RGBA')
    
    cx, cy = 880, 360
    # Amber searchlight beacon glowing from lower corner
    beam_origin = (w - 50, h + 100)
    for rad_step in range(12):
        spread = 220 + rad_step * 25
        alpha = int(40 - rad_step * 3)
        draw.polygon([beam_origin, (cx - spread, cy - 180), (cx + spread, cy - 180)], fill=(245, 158, 11, alpha))
        
    # Tactical Carbon Fiber Hex Pattern
    for x in range(650, w, 22):
        for y in range(0, h, 22):
            draw.regular_polygon((x, y, 9), n_sides=6, rotation=30, fill=(31, 41, 55, 25), outline=(55, 65, 81, 40))
            
    # Bat Emblem Silhouette in amber glow
    # Curved wing top and scalloped wing bottom
    bat_pts = [
        (cx, cy - 70), (cx + 35, cy - 90), (cx + 70, cy - 40), (cx + 170, cy - 80),
        (cx + 200, cy - 20), (cx + 150, cy + 40), (cx + 100, cy + 20), (cx + 50, cy + 60),
        (cx, cy + 20),
        (cx - 50, cy + 60), (cx - 100, cy + 20), (cx - 150, cy + 40), (cx - 200, cy - 20),
        (cx - 170, cy - 80), (cx - 70, cy - 40), (cx - 35, cy - 90)
    ]
    draw.polygon(bat_pts, fill=(15, 23, 42, 240), outline=(245, 158, 11, 230), width=3)
    # Glowing bat chest emblem
    draw.ellipse([cx - 25, cy - 35, cx + 25, cy + 5], fill=(245, 158, 11, 80))
    
    return im.convert('RGB')

def generate_synthwave_badge():
    w, h = 1200, 750
    # Retro synthwave violet
    im = make_gradient(w, h, (18, 4, 40), (45, 10, 70))
    draw = ImageDraw.Draw(im, 'RGBA')
    
    # Glowing Neon Retro Sun in center-right
    cx, cy = 880, 280
    sun_r = 170
    draw.ellipse([cx - sun_r, cy - sun_r, cx + sun_r, cy + sun_r], fill=(255, 42, 133, 240))
    # Sun horizontal slice bars (Outrun style)
    for bar_y in range(cy - 20, cy + sun_r, 18):
        bar_h = 4 + int((bar_y - cy) * 0.08)
        draw.rectangle([cx - sun_r, bar_y, cx + sun_r, bar_y + bar_h], fill=(18, 4, 40, 255))
        
    # Perspective Grid Horizon
    horizon_y = cy + 100
    draw.line([(550, horizon_y), (w, horizon_y)], fill=(5, 217, 232, 230), width=3)
    # Perspective ground lines
    vp_x = cx
    for gx in range(500, w + 200, 45):
        draw.line([(vp_x, horizon_y), (gx, h)], fill=(5, 217, 232, 90), width=2)
    # Horizontal ground distance lines
    for gy in range(horizon_y + 15, h, 24):
        step_alpha = int(40 + (gy - horizon_y) * 0.4)
        draw.line([(550, gy), (w, gy)], fill=(5, 217, 232, min(step_alpha, 160)), width=1)
        
    return im.convert('RGB')

def generate_royal_badge():
    w, h = 1200, 750
    # Royal velvet purple to deep royal navy
    im = make_gradient(w, h, (10, 5, 21), (32, 10, 55))
    draw = ImageDraw.Draw(im, 'RGBA')
    
    cx, cy = 880, 360
    # Ornate Gold Heraldic Filigree Rings
    for r in [80, 150, 210, 260]:
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(250, 204, 21, 140), width=2)
    for d in range(0, 360, 30):
        rad = math.radians(d)
        fx = cx + 210 * math.cos(rad)
        fy = cy + 210 * math.sin(rad)
        draw.ellipse([fx - 8, fy - 8, fx + 8, fy + 8], fill=(250, 204, 21, 180), outline=(255, 255, 255, 220))
        
    # Royal Crown Motif in Center
    cw = 70
    crown_pts = [
        (cx - cw, cy + 30), (cx + cw, cy + 30),
        (cx + cw + 15, cy - 35), (cx + cw * 0.45, cy - 10),
        (cx, cy - 55),
        (cx - cw * 0.45, cy - 10), (cx - cw - 15, cy - 35)
    ]
    draw.polygon(crown_pts, fill=(250, 204, 21, 230), outline=(255, 255, 255, 220), width=3)
    # Crown jewels
    draw.ellipse([cx - 8, cy - 63, cx + 8, cy - 47], fill=(239, 68, 68, 255))
    draw.ellipse([cx - cw - 22, cy - 42, cx - cw - 8, cy - 28], fill=(59, 130, 246, 255))
    draw.ellipse([cx + cw + 8, cy - 42, cx + cw + 22, cy - 28], fill=(59, 130, 246, 255))
    
    # Floating 24K gold foil particles
    random.seed(999)
    for _ in range(80):
        fx = random.randint(600, w)
        fy = random.randint(20, h - 20)
        fr = random.randint(2, 6)
        draw.ellipse([fx - fr, fy - fr, fx + fr, fy + fr], fill=(250, 204, 21, random.randint(60, 200)))
        
    return im.convert('RGB')

def generate_zen_badge():
    w, h = 1200, 750
    # Natural bamboo sage deep forest
    im = make_gradient(w, h, (6, 33, 26), (15, 60, 48))
    draw = ImageDraw.Draw(im, 'RGBA')
    
    cx, cy = 880, 360
    # Japanese Zen Enso Circle (Calligraphic ink circle)
    enso_r = 180
    for thick in range(12, 34):
        draw.arc([cx - enso_r - thick, cy - enso_r - thick, cx + enso_r + thick, cy + enso_r + thick],
                 start=15, end=330, fill=(52, 211, 153, 35), width=2)
    # Core enso stroke
    draw.arc([cx - enso_r, cy - enso_r, cx + enso_r, cy + enso_r], start=20, end=330, fill=(52, 211, 153, 210), width=16)
    
    # Sacred Geometry Lotus Petals in Center
    for pet in range(8):
        ang = pet * math.pi / 4
        px = cx + 55 * math.cos(ang)
        py = cy + 55 * math.sin(ang)
        draw.ellipse([px - 22, py - 22, px + 22, py + 22], outline=(167, 243, 208, 140), width=2)
    draw.ellipse([cx - 24, cy - 24, cx + 24, cy + 24], fill=(52, 211, 153, 160), outline=(255, 255, 255, 200), width=2)
    
    # Organic bamboo lines & ripples
    for rip_r in range(230, 480, 50):
        draw.ellipse([cx - rip_r, cy - rip_r, cx + rip_r, cy + rip_r], outline=(52, 211, 153, 30), width=1)
        
    return im.convert('RGB')

if __name__ == '__main__':
    targets = [
        ('frontend/assets/finance-calendar.jpg', generate_calendar_banner),
        ('frontend/assets/badge-banner.jpg', generate_badge_banner),
        ('frontend/assets/badge-spider.jpg', generate_spider_badge),
        ('frontend/assets/badge-bloodborne.jpg', generate_bloodborne_badge),
        ('frontend/assets/badge-money.jpg', generate_money_badge),
        ('frontend/assets/badge-cute.jpg', generate_cute_badge),
        ('frontend/assets/badge-cyberpunk.jpg', generate_cyberpunk_badge),
        ('frontend/assets/badge-neural.jpg', generate_neural_badge),
        ('frontend/assets/badge-batman.jpg', generate_batman_badge),
        ('frontend/assets/badge-synthwave.jpg', generate_synthwave_badge),
        ('frontend/assets/badge-royal.jpg', generate_royal_badge),
        ('frontend/assets/badge-zen.jpg', generate_zen_badge),

        ('frontend-dummy/assets/finance-calendar.jpg', generate_calendar_banner),
        ('frontend-dummy/assets/badge-banner.jpg', generate_badge_banner),
        ('frontend-dummy/assets/badge-spider.jpg', generate_spider_badge),
        ('frontend-dummy/assets/badge-bloodborne.jpg', generate_bloodborne_badge),
        ('frontend-dummy/assets/badge-money.jpg', generate_money_badge),
        ('frontend-dummy/assets/badge-cute.jpg', generate_cute_badge),
        ('frontend-dummy/assets/badge-cyberpunk.jpg', generate_cyberpunk_badge),
        ('frontend-dummy/assets/badge-neural.jpg', generate_neural_badge),
        ('frontend-dummy/assets/badge-batman.jpg', generate_batman_badge),
        ('frontend-dummy/assets/badge-synthwave.jpg', generate_synthwave_badge),
        ('frontend-dummy/assets/badge-royal.jpg', generate_royal_badge),
        ('frontend-dummy/assets/badge-zen.jpg', generate_zen_badge),
    ]
    for path, gen_func in targets:
        print(f'Generating {path}...')
        img = gen_func()
        img.save(path, quality=92)
    print('All assets generated successfully!')
