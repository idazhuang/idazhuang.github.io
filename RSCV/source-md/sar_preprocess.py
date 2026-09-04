"""sar_preprocess.py —— SAR 原始数据 -> 可看可训的 8bit 图。"""
import numpy as np, cv2

def to_amplitude(arr):
    """复数 -> 幅度；已是实数则取绝对值。"""
    return np.abs(arr).astype(np.float32)

def amp_to_db(amp, eps=1e-6):
    """幅度 -> dB。幅度用 20log10，强度(幅度平方)用 10log10。"""
    return 20.0 * np.log10(np.maximum(amp, eps))

def stretch(db, lo_pct=1.0, hi_pct=99.0):
    """分位裁剪 + 归一化到 0-255。"""
    lo, hi = np.percentile(db, [lo_pct, hi_pct])
    if hi - lo < 1e-6: hi = lo + 1e-6
    return np.clip((db - lo) / (hi - lo), 0, 1)

def sar_to_png(arr, out_path, lo_pct=1.0, hi_pct=99.0):
    vis = (stretch(amp_to_db(to_amplitude(arr)), lo_pct, hi_pct) * 255).astype(np.uint8)
    cv2.imwrite(out_path, vis)
    return vis

if __name__ == '__main__':
    rng = np.random.default_rng(0)
    H = W = 256
    truth = np.full((H, W), 0.02)        # 暗：海面
    truth[60:200, 60:120] = 1.0          # 亮：船体 (50倍)
    truth[80:180, 150:220] = 0.2         # 中：海岸
    # 单视 SAR：复高斯 -> 幅度服从 Rayleigh
    z = rng.normal(0, np.sqrt(truth/2)) + 1j*rng.normal(0, np.sqrt(truth/2))
    amp = np.abs(z)
    print(f"原始幅度 动态范围: min={amp.min():.5f} max={amp.max():.4f} 比值={amp.max()/max(amp.min(),1e-9):.0f}x")
    # 对照：不做 log 直接线性归一化
    lin = ((amp - amp.min())/(amp.max()-amp.min())*255).astype(np.uint8)
    log = (stretch(amp_to_db(amp))*255).astype(np.uint8)
    cv2.imwrite('sar_linear.png', lin); cv2.imwrite('sar_log.png', log)
    print(f"线性显示: 均值={lin.mean():.1f}  低于10灰阶的像素占比={100*(lin<10).mean():.1f}%")
    print(f"log显示 : 均值={log.mean():.1f}  低于10灰阶的像素占比={100*(log<10).mean():.1f}%")
