"""metrics.py —— 亲手实现 F1 / IoU / mIoU，看清指标在算什么。"""
import numpy as np

def confusion(pred, gt, num_classes, ignore_index=None):
    pred, gt = np.asarray(pred).ravel(), np.asarray(gt).ravel()
    if ignore_index is not None:
        m = gt != ignore_index
        pred, gt = pred[m], gt[m]
    k = (gt >= 0) & (gt < num_classes)
    return np.bincount(num_classes * gt[k].astype(int) + pred[k],
                       minlength=num_classes**2).reshape(num_classes, num_classes)

def binary_prf(pred, gt, positive=1):
    tp = int(((pred == positive) & (gt == positive)).sum())
    fp = int(((pred == positive) & (gt != positive)).sum())
    fn = int(((pred != positive) & (gt == positive)).sum())
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    iou = tp / (tp + fp + fn) if tp + fp + fn else 0.0
    return dict(P=p, R=r, F1=f1, IoU=iou, TP=tp, FP=fp, FN=fn)

def miou(cm):
    inter = np.diag(cm).astype(float)
    union = cm.sum(1) + cm.sum(0) - np.diag(cm)
    iou = np.divide(inter, union, out=np.full_like(inter, np.nan), where=union > 0)
    return iou, float(np.nanmean(iou))

if __name__ == '__main__':
    rng = np.random.default_rng(0)
    # ---- 场景1：极不平衡的变化检测，验证"准确率会骗人" ----
    gt = np.zeros(10000, int); gt[:200] = 1            # 2% 是变化
    lazy = np.zeros(10000, int)                        # 全猜"没变"的废物模型
    print('【全猜没变的废物模型】')
    print('  准确率 =', (lazy == gt).mean())
    print('  ', binary_prf(lazy, gt))
    real = gt.copy()
    flip_fn = rng.choice(np.where(gt == 1)[0], 40, replace=False); real[flip_fn] = 0   # 漏检40
    flip_fp = rng.choice(np.where(gt == 0)[0], 30, replace=False); real[flip_fp] = 1   # 误检30
    print('【一个真的在干活的模型】')
    print('  准确率 =', (real == gt).mean())
    print('  ', {k: (round(v,4) if isinstance(v,float) else v) for k,v in binary_prf(real, gt).items()})

    # ---- 场景2：F1 只在变化类算 vs 两类平均，差多少 ----
    r = binary_prf(real, gt, positive=1); r0 = binary_prf(1-real, 1-gt, positive=1)
    print('\n【F1 的两种算法】')
    print(f'  只算变化类 F1 = {r["F1"]:.4f}   ← 变化检测论文报的是这个')
    print(f'  两类平均  F1 = {(r["F1"]+r0["F1"])/2:.4f}   ← 算错会虚高一大截')

    # ---- 场景3：mIoU 与 ignore_index ----
    g = rng.integers(0, 8, (64, 64)); p = g.copy()
    mask = rng.random(g.shape) < 0.25                   # 25% 的像素预测错
    p[mask] = rng.integers(0, 8, int(mask.sum()))
    g[:8, :] = 0                                        # LoveDA: 0 = ignore（无标注区）
    cm_all = confusion(p, g, 8)
    cm_ign = confusion(p, g, 8, ignore_index=0)
    print('\n【mIoU 与 ignore】')
    print(f'  不排除 ignore 类: mIoU = {miou(cm_all)[1]:.4f}')
    print(f'  排除 ignore 类  : mIoU = {miou(cm_ign)[1]:.4f}   ← LoveDA 官方口径')
