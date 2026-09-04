"""paper_figs.py —— 出版级图表的统一设置 + 两个常用图。"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

def set_paper_style(col='single'):
    """col='single' 单栏(约3.5in宽) / 'double' 双栏通栏(约7.16in)。
    ★ 关键：字号按"图缩到论文里之后仍能看清"来定，不是按屏幕上好看来定。"""
    plt.rcParams.update({
        'figure.figsize': (3.5, 2.6) if col == 'single' else (7.16, 3.0),
        'figure.dpi': 150,
        'savefig.dpi': 600,            # 位图导出时用；矢量图无所谓
        'font.size': 8,                # ★ 论文里图注常是 8pt，图内字号不应小于它
        'axes.labelsize': 8, 'axes.titlesize': 9,
        'xtick.labelsize': 7, 'ytick.labelsize': 7, 'legend.fontsize': 7,
        'axes.linewidth': 0.8, 'lines.linewidth': 1.2, 'lines.markersize': 3.5,
        'axes.grid': True, 'grid.alpha': 0.3, 'grid.linewidth': 0.5,
        'savefig.bbox': 'tight', 'savefig.pad_inches': 0.02,
        'pdf.fonttype': 42, 'ps.fonttype': 42,   # ★ 字体嵌入为 TrueType，避免出版社报错
    })

# 色盲友好配色（Okabe-Ito），避免纯红绿对比
CB = ['#0072B2', '#D55E00', '#009E73', '#CC79A7', '#E69F00', '#56B4E9']

def ablation_bar(names, means, stds, out='fig_ablation.pdf', ylabel='mAP (%)'):
    set_paper_style('single')
    fig, ax = plt.subplots()
    x = np.arange(len(names))
    ax.bar(x, means, yerr=stds, capsize=2.5, color=CB[:len(names)],
           edgecolor='black', linewidth=0.6)
    ax.set_xticks(x); ax.set_xticklabels(names, rotation=20, ha='right')
    ax.set_ylabel(ylabel)
    lo = min(np.array(means) - np.array(stds)); hi = max(np.array(means) + np.array(stds))
    ax.set_ylim(lo - (hi - lo) * 0.5, hi + (hi - lo) * 0.3)   # ★ 不从0开始要在图注声明
    for xi, m in zip(x, means):
        ax.text(xi, m + max(stds) * 1.3, f'{m:.1f}', ha='center', fontsize=6.5)
    fig.savefig(out); plt.close(fig)
    return out

def seed_curve(steps, series, out='fig_curve.pdf', ylabel='mAP (%)'):
    set_paper_style('single')
    fig, ax = plt.subplots()
    for i, (name, runs) in enumerate(series.items()):
        arr = np.asarray(runs, float)          # (n_seed, n_step)
        m, s = arr.mean(0), arr.std(0, ddof=1)
        ax.plot(steps, m, label=name, color=CB[i])
        ax.fill_between(steps, m - s, m + s, color=CB[i], alpha=0.18, linewidth=0)
    ax.set_xlabel('Epoch'); ax.set_ylabel(ylabel); ax.legend(frameon=False)
    fig.savefig(out); plt.close(fig)
    return out

if __name__ == '__main__':
    rng = np.random.default_rng(0)
    print(ablation_bar(['Baseline','+A','+B','+A+B (Ours)'],
                       [73.0, 74.1, 73.8, 75.7], [0.6, 0.5, 0.6, 0.4]))
    steps = np.arange(1, 13)
    base = [73 - 12/np.sqrt(s) + rng.normal(0,.3,12) for s in range(1,4)]
    ours = [76 - 12/np.sqrt(s) + rng.normal(0,.3,12) for s in range(1,4)]
    print(seed_curve(steps, {'Baseline': base, 'Ours': ours}))
    import os
    for f in ['fig_ablation.pdf','fig_curve.pdf']:
        print(f, os.path.getsize(f), 'bytes')
