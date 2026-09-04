"""seed_tools.py —— 固定随机性 + 多 seed 结果的显著性判断。"""
import os, random, numpy as np

def set_seed(seed: int, deterministic: bool = True):
    """把所有随机源固定住。缺任何一行都会导致复现不了。"""
    random.seed(seed); np.random.seed(seed)
    os.environ['PYTHONHASHSEED'] = str(seed)
    try:
        import torch
        torch.manual_seed(seed); torch.cuda.manual_seed_all(seed)
        if deterministic:
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.benchmark = False   # ★ 关掉才可复现，但会慢一些
    except ImportError:
        pass

def summarize(vals):
    v = np.asarray(vals, float)
    return dict(mean=v.mean(), std=v.std(ddof=1) if len(v) > 1 else 0.0, n=len(v))

def compare(base, ours, seed_paired=True):
    """判断 ours 相对 base 的提升是否可信。返回结论字典。"""
    b, o = np.asarray(base, float), np.asarray(ours, float)
    sb, so = summarize(b), summarize(o)
    delta = so['mean'] - sb['mean']
    pooled = np.sqrt((sb['std']**2 + so['std']**2) / 2) if len(b) > 1 else 0.0
    cohen_d = delta / pooled if pooled > 0 else float('inf')
    out = dict(base=f"{sb['mean']:.2f}±{sb['std']:.2f}", ours=f"{so['mean']:.2f}±{so['std']:.2f}",
               delta=round(delta, 3), cohen_d=round(cohen_d, 2) if pooled > 0 else None)
    if seed_paired and len(b) == len(o):
        d = o - b
        out['每个seed都赢'] = bool((d > 0).all())
        out['配对差均值'] = f"{d.mean():.2f}±{d.std(ddof=1):.2f}" if len(d) > 1 else f"{d.mean():.2f}"
    # ---- 判定规则 ----
    if len(b) < 3 or len(o) < 3:
        out['结论'] = '❌ seed 不足（<3），不能下任何结论'
        return out
    noise = max(sb['std'], so['std'])
    # ★ 配对判定优先：同 seed 逐对相减，能消掉 seed 本身带来的共同波动
    if seed_paired and len(b) == len(o):
        d = o - b
        if d.mean() <= 0:
            out['结论'] = '无提升'
        elif (d > 0).all() and d.mean() > 2 * d.std(ddof=1):
            out['结论'] = '✅ 配对判定：每个 seed 都赢且差值稳定 —— 可信'
        elif (d > 0).all():
            out['结论'] = '⚠ 每个 seed 都赢，但差值本身波动大 —— 加 seed 再看'
        else:
            out['结论'] = '★ 有的 seed 输了 —— 不可信'
        return out
    # 无配对时退化为边际比较（更保守）
    if delta <= 0:            out['结论'] = '无提升'
    elif delta < noise:       out['结论'] = '★ 提升小于噪声，不可信'
    elif delta < 2 * noise:   out['结论'] = '⚠ 弱信号'
    else:                     out['结论'] = '✅ 提升明显大于噪声'
    return out

if __name__ == '__main__':
    print('【情形1】看着涨了 0.4，但方差大 —— 典型的自欺欺人')
    for k, v in compare([73.1, 72.4, 73.6], [73.5, 72.9, 73.9]).items(): print(f'   {k}: {v}')
    print('\n【情形2】提升不大但极稳定，每个 seed 都赢')
    for k, v in compare([73.1, 72.4, 73.6], [73.9, 73.2, 74.4]).items(): print(f'   {k}: {v}')
    print('\n【情形3】真正明显的提升')
    for k, v in compare([73.1, 72.4, 73.6], [75.8, 75.2, 76.1]).items(): print(f'   {k}: {v}')
    print('\n【情形4】只跑1个seed就下结论（新手最常犯）')
    for k, v in compare([73.1], [74.0]).items(): print(f'   {k}: {v}')
