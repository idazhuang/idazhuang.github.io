"""vis_dota.py —— 读 DOTA 标注，画旋转框，存图。"""
import os, argparse
import cv2
import numpy as np

CLASSES = ['plane','baseball-diamond','bridge','ground-track-field','small-vehicle',
           'large-vehicle','ship','tennis-court','basketball-court','storage-tank',
           'soccer-ball-field','roundabout','harbor','swimming-pool','helicopter']
np.random.seed(42)
COLORS = {c: tuple(int(v) for v in np.random.randint(60, 255, 3)) for c in CLASSES}

def parse_dota_label(txt_path):
    objs = []
    with open(txt_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith(('imagesource', 'gsd')):
                continue
            p = line.split()
            if len(p) < 9:
                continue
            pts = np.array([float(x) for x in p[:8]], dtype=np.float32).reshape(4, 2)
            objs.append(dict(points=pts, cls=p[8], difficult=int(p[9]) if len(p) > 9 else 0))
    return objs

def draw(img, objs, thickness=2, show_difficult=True):
    for o in objs:
        if o['difficult'] and not show_difficult:
            continue
        color = COLORS.get(o['cls'], (0, 255, 0))
        pts = o['points'].astype(np.int32).reshape(-1, 1, 2)
        cv2.polylines(img, [pts], isClosed=True, color=color, thickness=thickness)
        x, y = o['points'][0].astype(int)
        cv2.putText(img, o['cls'], (x, max(y - 5, 12)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)
    return img

def poly_to_xywha(pts):
    (cx, cy), (w, h), ang = cv2.minAreaRect(pts.astype(np.float32))
    return cx, cy, w, h, ang

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--img'); ap.add_argument('--label'); ap.add_argument('--out', default='vis.jpg')
    a = ap.parse_args()
    img = cv2.imread(a.img)
    objs = parse_dota_label(a.label)
    print(f'读到 {len(objs)} 个目标')
    cv2.imwrite(a.out, draw(img, objs))
