"""to_dota.py —— 把 SAR 船舶数据集的标注转成 DOTA 格式（MMRotate 能吃的格式）。
支持两种来源：COCO JSON（HRSID 等）/ VOC XML（SSDD 等）。
"""
import os, json, argparse
import numpy as np
import xml.etree.ElementTree as ET

def hbb_to_poly(x, y, w, h):
    """水平框 (x,y,w,h) -> 四点，顺时针。"""
    return [x, y, x + w, y, x + w, y + h, x, y + h]

def seg_to_poly(seg):
    """COCO 分割多边形 -> 最小外接旋转框的四点（这才用上了旋转框的价值）。"""
    import cv2
    pts = np.array(seg, dtype=np.float32).reshape(-1, 2)
    box = cv2.boxPoints(cv2.minAreaRect(pts))
    return box.reshape(-1).tolist()

def write_dota(out_dir, stem, objs):
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, stem + '.txt'), 'w', encoding='utf-8') as f:
        f.write('imagesource:converted\ngsd:null\n')
        for poly, cls, diff in objs:
            f.write(' '.join(f'{v:.1f}' for v in poly) + f' {cls} {diff}\n')

def from_coco(json_path, out_dir, use_seg=True):
    d = json.load(open(json_path, encoding='utf-8'))
    cats = {c['id']: c['name'].replace(' ', '-') for c in d['categories']}
    imgs = {i['id']: i['file_name'] for i in d['images']}
    per = {}
    for a in d['annotations']:
        if use_seg and a.get('segmentation'):
            seg = a['segmentation'][0] if isinstance(a['segmentation'], list) else None
            poly = seg_to_poly(seg) if seg and len(seg) >= 8 else hbb_to_poly(*a['bbox'])
        else:
            poly = hbb_to_poly(*a['bbox'])
        per.setdefault(a['image_id'], []).append(
            (poly, cats.get(a['category_id'], 'ship'), a.get('iscrowd', 0)))
    for iid, fn in imgs.items():
        write_dota(out_dir, os.path.splitext(fn)[0], per.get(iid, []))
    return len(imgs), sum(len(v) for v in per.values())

def from_voc(xml_dir, out_dir):
    n_img = n_obj = 0
    for fn in sorted(os.listdir(xml_dir)):
        if not fn.endswith('.xml'): continue
        root = ET.parse(os.path.join(xml_dir, fn)).getroot()
        objs = []
        for o in root.findall('object'):
            name = (o.findtext('name') or 'ship').replace(' ', '-')
            diff = int(o.findtext('difficult') or 0)
            rb = o.find('rotated_bndbox')          # 部分 SSDD 版本带旋转框
            if rb is not None:
                poly = [float(rb.findtext(k)) for k in
                        ('x1','y1','x2','y2','x3','y3','x4','y4')]
            else:
                b = o.find('bndbox')
                x1, y1 = float(b.findtext('xmin')), float(b.findtext('ymin'))
                x2, y2 = float(b.findtext('xmax')), float(b.findtext('ymax'))
                poly = [x1,y1, x2,y1, x2,y2, x1,y2]
            objs.append((poly, name, diff)); n_obj += 1
        write_dota(out_dir, os.path.splitext(fn)[0], objs); n_img += 1
    return n_img, n_obj

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--coco'); ap.add_argument('--voc'); ap.add_argument('--out', required=True)
    a = ap.parse_args()
    if a.coco: print('转换完成: %d 张图 / %d 个目标' % from_coco(a.coco, a.out))
    elif a.voc: print('转换完成: %d 张图 / %d 个目标' % from_voc(a.voc, a.out))
