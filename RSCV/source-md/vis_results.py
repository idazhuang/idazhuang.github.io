"""vis_results.py —— 画 预测框(绿) vs GT框(红)，算旋转框 IoU，标出 对/错/漏。"""
import cv2, numpy as np

def obb_to_corners(box):
    """(cx,cy,w,h,angle_deg) -> (4,2) 角点。"""
    cx, cy, w, h, ang = box[:5]
    return cv2.boxPoints(((float(cx), float(cy)), (float(w), float(h)), float(ang)))

def obb_iou(a, b):
    r1 = ((float(a[0]), float(a[1])), (float(a[2]), float(a[3])), float(a[4]))
    r2 = ((float(b[0]), float(b[1])), (float(b[2]), float(b[3])), float(b[4]))
    ret, region = cv2.rotatedRectangleIntersection(r1, r2)
    if ret == 0 or region is None:
        return 0.0
    inter = cv2.contourArea(cv2.convexHull(region))
    union = a[2]*a[3] + b[2]*b[3] - inter
    return float(inter/union) if union > 0 else 0.0

def match(preds, gts, iou_thr=0.5):
    """按分数降序贪心匹配。返回 (TP索引, FP索引, 漏检GT索引, 每个TP的IoU)。"""
    order = sorted(range(len(preds)), key=lambda i: -preds[i][5]) if preds and len(preds[0]) > 5 \
            else list(range(len(preds)))
    used, tp, fp, ious = set(), [], [], {}
    for pi in order:
        best, best_iou = -1, iou_thr
        for gi, g in enumerate(gts):
            if gi in used:
                continue
            v = obb_iou(preds[pi], g)
            if v >= best_iou:
                best, best_iou = gi, v
        if best >= 0:
            used.add(best); tp.append(pi); ious[pi] = best_iou
        else:
            fp.append(pi)
    fn = [gi for gi in range(len(gts)) if gi not in used]
    return tp, fp, fn, ious

def draw(img, preds, gts, iou_thr=0.5):
    tp, fp, fn, ious = match(preds, gts, iou_thr)
    for gi in range(len(gts)):                      # GT 红；漏检的画粗一点
        cv2.polylines(img, [obb_to_corners(gts[gi]).astype(np.int32)], True,
                      (0, 0, 255), 4 if gi in fn else 2)
    for pi in tp:                                   # 检对 绿
        c = obb_to_corners(preds[pi]).astype(np.int32)
        cv2.polylines(img, [c], True, (0, 255, 0), 2)
        cv2.putText(img, f'{ious[pi]:.2f}', tuple(c[0]),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1, cv2.LINE_AA)
    for pi in fp:                                   # 误检 黄
        cv2.polylines(img, [obb_to_corners(preds[pi]).astype(np.int32)], True, (0, 255, 255), 2)
    return img, dict(TP=len(tp), FP=len(fp), FN=len(fn))

if __name__ == '__main__':
    img = np.full((400, 600, 3), 40, np.uint8)
    gts   = [(150,150,80,40,20), (400,150,60,60,0), (300,300,70,30,-45)]
    preds = [(155,152,78,42,22,0.95), (420,160,60,60,5,0.88), (520,320,50,50,0,0.60)]
    img, stat = draw(img, preds, gts)
    cv2.imwrite('vis_results.jpg', img)
    print(stat)
    for p, g in zip(preds[:2], gts[:2]):
        print(f'  IoU={obb_iou(p,g):.3f}')
