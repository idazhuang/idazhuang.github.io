# 补充 01 · W1-D1 晚上段 ·「装 MMRotate + 跑通第一张 DOTA demo」保姆级实操
## 原手册这一格只给了方向，这一页给你完整的命令、版本、权重地址和报错解药

> **这一页替代什么**：替代原 W1-D1「晚上段 · 装 MMRotate 工具链 + 跑通第一张 DOTA demo」的第 ②③④⑤ 块。原文让你"先去 GitHub README 看它钦定的版本号"——那恰恰是新手最做不到的一步。这一页把版本号写死、把权重地址给全、把报错列成表。
>
> **今晚的及格线（写在最前面）**：终端里出现 `result.jpg`，打开它能看到一张俯视图上套着一圈**斜着的彩色框**。做到这一步今晚就结束，不要顺手去训练。
>
> **时间预算**：顺利 40 分钟；踩两个坑 2 小时；完全打不通 —— 走第 6 节的保底路线，30 分钟内照样出图。**卡住不是你笨，是这套框架有历史包袱**，第 1 节会讲清楚为什么。

---

## 1. 先垫概念：为什么「代码下下来根本跑不通」

新手默认"clone 下来 → python 一跑 → 出结果"。深度学习框架不是这样的。你缺的是三样东西，它们**分别存放、分别下载**：

| 你以为只需要 | 实际需要三样 | 它是什么 | 从哪来 | 有多大 |
|---|---|---|---|---|
| 代码 | **① 代码** | 模型怎么搭、怎么前向、怎么画框的 Python 实现 | `git clone` 仓库 | 几十 MB |
| | **② config 配置文件** | 一个 `.py`，写死了"用哪个骨干网、输入多大、有几类、框怎么编码"。**代码是通用的，config 才决定你跑的是哪个模型** | 仓库里的 `configs/` 目录，或单独下载 | 几 KB |
| | **③ checkpoint 权重** | 一个 `.pth`，别人在 DOTA 上训练几十小时得到的几千万个参数。**没有它，模型是个随机初始化的空壳，输出全是噪声** | 官方下载站，**必须单独下** | 100–300 MB |

**这就是你卡住的根本原因**：仓库里只有 ①②，`.pth` 因为太大**不会**跟着 `git clone` 下来。原手册那句"跑自带 demo"跳过了整个 ③。

三者的关系，记住这一句：

> **代码是引擎，config 是图纸，checkpoint 是已经调校好的参数。三样凑齐，`demo/image_demo.py` 才能出图。**

再补两个今晚会反复见到的词：

- **MM 全家桶的依赖链**：`mmcv-full`（底层 CUDA 算子，旋转框的 IoU、NMS 都在这）→ `mmdet`（通用检测框架）→ `mmrotate`（旋转框检测）。地基 → 楼房 → 精装修。
- **"代际"**：这套生态有两代，**不能混用**。
  - **0.x 代**：`mmcv-full 1.x` + `mmdet 2.x` + `mmrotate 0.x`
  - **1.x 代**：`mmengine` + `mmcv 2.x` + `mmdet 3.x` + `mmrotate 1.x`
  
  跨代必崩，报错是 `AssertionError: MMCV==2.x.x is used but incompatible`。**今晚 80% 的报错来源于此。**

**为什么推荐走 0.x 代**：MMRotate 的主分支（main）到今天仍是 **0.3.4**，1.x 停在 `1.0.0rc1` 预览版。0.x 的模型权重最全、网上踩坑记录最多、你 W2 要复现的 Oriented R-CNN baseline 也在这一代。**用老的那个，不是保守，是选文档和 issue 最多的那条路。**

---

## 2. 手把手带做（第 0 步）：开工前的 5 分钟体检

**别急着装。先搞清楚你的机器是什么配置**，因为后面每条命令里的版本号都由它决定。

```bash
# ① 有没有 N 卡、驱动是什么、显存多大
nvidia-smi

# ② Python 在哪、什么版本
python --version

# ③ conda 在不在
conda --version
```

**怎么读 `nvidia-smi` 的输出**（这是新手第一个大误区）：

```text
+-----------------------------------------------------------------------------+
| NVIDIA-SMI 535.104.05   Driver Version: 535.104.05   CUDA Version: 12.2      |
|-------------------------------+----------------------+----------------------+
| GPU  Name        Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
|   0  NVIDIA GeForce RTX 3090  | 00000000:01:00.0 Off |                  N/A |
|  0%   35C    P8    25W / 350W |      0MiB / 24576MiB |      0%      Default |
+-------------------------------+----------------------+----------------------+
```

> ⚠️ **右上角那个 `CUDA Version: 12.2` 不是"你装了 CUDA 12.2"**，它是"**你的驱动最高能支持到 CUDA 12.2**"。你完全可以在这台机器上装 CUDA 11.8 版本的 PyTorch。**驱动版本 ≥ 你要用的 CUDA 版本就行。**
>
> 新手最常见的自我劝退是："我这里显示 12.2，可 mmcv 只支持到 11.8，是不是没救了？"——没这回事，往下走。

**体检判定表**：

| 体检结果 | 判定 | 今晚怎么走 |
|---|---|---|
| 有 N 卡，驱动 ≥ 520 | ✅ 最顺 | 路线 A，CUDA 11.8 |
| 有 N 卡，驱动 450–520 | ✅ 可以 | 路线 A，把 cu118 换成 cu111/cu113（见 4.2） |
| 有 N 卡，但是 RTX 40/50 系新卡 | ⚠️ 注意 | 路线 A，但可能遇到 `no kernel image` 报错，见第 5 节第 8 条 |
| 没有 N 卡（核显 / A 卡 / Mac） | ⚠️ 能出图 | 路线 A 全程可做，只是 demo 加 `--device cpu`，慢几秒而已 |
| Windows 原生 | ⚠️ 麻烦 | **强烈建议先装 WSL2 + Ubuntu**，在 Linux 里做。今晚在 Windows 硬扛大概率是浪费一晚上 |

**⑥ 这一步你学会了什么**：你学会了区分**驱动版本**和 **CUDA 运行时版本**——这个区分你后面两年每换一台机器都要用一次。

---

## 3. 三条路线，先选一条

| | 路线 A（推荐） | 路线 B | 路线 C（保底） |
|---|---|---|---|
| 装什么 | MMRotate **0.3.4** 代 | MMRotate **1.0.0rc1** 代 | **Ultralytics YOLO-OBB** |
| 难度 | 中 | 高 | **极低** |
| 耗时 | 40 分钟 – 2 小时 | 1–3 小时 | **10 分钟** |
| 预训练权重 | 齐全 | 部分 | 齐全，自动下载 |
| W2 baseline 能用吗 | ✅ 就是它 | ⚠️ config 名字全变了 | ❌ 只能当对照组 |
| 什么时候选 | **默认走这条** | 你就是想用新版 | **A 打不通 / 今晚只剩一小时** |

> **决策规则**：先走 A。**A 卡满 2 小时就切 C**，今晚必须有一张出图。C 出图之后，A 挪到明天 D2 的晚上段收尾——原手册已经允许"环境溢出 1–2 天"，这在计划内。

---

## 4. 路线 A 全流程（逐条命令 + 期望输出）

### 4.1 建一个干净的环境

```bash
conda create -n mmrot python=3.9 -y
conda activate mmrot
```

> **为什么是 3.9**：`mmcv-full 1.7.2` 的预编译包覆盖 Python 3.7–3.10。**3.9 是命中率最高的**。
> **⛔ 不要用 Python 3.11/3.12** —— 没有预编译包，pip 会转去本地编译，几十分钟后大概率失败。
> **为什么不复用中午段建的 `rs` 环境**：可以复用，但 MMRotate 会把 `numpy`、`yapf` 往低版本按。**单开一个 `mmrot` 更干净**，把 `rs` 留给你自己写脚本用。这也是"一个项目一间无菌实验室"的实践。

### 4.2 装 PyTorch（版本要和后面的 mmcv 对齐）

```bash
pip install torch==2.0.1 torchvision==0.15.2 --index-url https://download.pytorch.org/whl/cu118
```

**验证（这一步不过不许往下走）**：

```bash
python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"
```

**期望输出**：

```text
2.0.1+cu118 11.8 True
```

- 最后是 `True` → 继续。
- 最后是 `False` 但你有 N 卡 → 多半是装成了 CPU 版。`pip uninstall torch torchvision -y` 后重来，注意 `--index-url` 不能丢。
- 没有 N 卡 → `False` 是正常的，继续走，后面 demo 加 `--device cpu`。

**驱动老一点的对照表**（把上面命令里的 `cu118` 和版本号替换掉）：

| 你的驱动 | 用这组 |
|---|---|
| ≥ 520 | `torch==2.0.1 torchvision==0.15.2` + `cu118` |
| 470–520 | `torch==1.13.1 torchvision==0.14.1` + `cu117` |
| 450–470 | `torch==1.10.1 torchvision==0.11.2` + `cu113` |

### 4.3 ★ 先按住三个"地雷依赖"（原手册完全没提，今晚最大的坑）

MMRotate 0.x 写于 2022 年。它之后，Python 生态有三个包发生了**破坏性升级**，会让你在明明版本"对"的情况下报出莫名其妙的错。**先按住它们，比事后排查省一小时**：

```bash
pip install "numpy<2" "yapf==0.40.1" "setuptools<70"
```

| 包 | 不按住会怎样 | 原因 |
|---|---|---|
| `numpy` | 导入时 ABI 报错，或 `module 'numpy' has no attribute 'float'` | numpy 2.0 是破坏性大版本，mmcv 1.x / mmdet 2.x 都是 numpy 1.x 时代的产物 |
| `yapf` | `TypeError: FormatCode() got an unexpected keyword argument 'verify'` | yapf 0.40.2（2023-09-22 发布）删掉了 `verify` 参数，而 mmcv 的 `Config.pretty_text` 还在传它 |
| `setuptools` | 装 mmrotate 时 `error: each element of 'ext_modules' ...` 之类的构建错误 | 新版 setuptools 移除了老的构建接口 |

> **⑥ 这一步你学会了什么**：**"依赖地狱"不只发生在直接依赖之间，更常发生在"依赖的依赖"悄悄升级时**。以后复现任何两年前的代码，第一反应就是把 numpy / setuptools / 格式化工具按回当年的版本。

### 4.4 装 mmcv-full（★ 今晚最关键的一条命令）

```bash
pip install mmcv-full==1.7.2 -f https://download.openmmlab.com/mmcv/dist/cu118/torch2.0/index.html
```

**这条命令为什么长成这样**：

- `mmcv-full` ≠ `mmcv`。0.x 代要的是 **`mmcv-full`**（带编译好的 CUDA 算子）。装成 `mmcv` 或 `mmcv-lite` 会报 `No module named 'mmcv._ext'`。
- `-f` 后面那个地址是 OpenMMLab 的**预编译包索引**。URL 的构造规则是：
  ```text
  https://download.openmmlab.com/mmcv/dist/{cu版本}/{torch版本}/index.html
  ```
  你把 4.2 里的 CUDA 和 torch 填进去即可（`cu118` / `torch2.0`）。
- **不带 `-f` 的后果**：pip 找不到预编译包 → 下载源码包 → 在你机器上现场编译 CUDA 算子 → 二三十分钟后大概率因为缺 nvcc 或 GCC 版本不对而失败。**这是新手在这一步崩掉的头号原因。**

**★ 怎么判断这条命令有没有走对**：盯 pip 的输出。

```text
✅ 对了：Downloading https://download.openmmlab.com/.../mmcv_full-1.7.2-cp39-cp39-manylinux1_x86_64.whl (60.2 MB)
❌ 错了：Downloading mmcv-full-1.7.2.tar.gz (...)   ← 出现 .tar.gz 就是要现场编译，立刻 Ctrl+C
```

看到 `.tar.gz` 就 Ctrl+C，回头检查：Python 是不是 3.11+？`-f` 的 URL 里 cu/torch 版本填对了吗？（若 `torch2.0` 无效，试 `torch2.0.0`。）

**验证**：

```bash
python -c "import mmcv; from mmcv.ops import nms_rotated; print(mmcv.__version__, 'ops ok')"
```

**期望输出**：`1.7.2 ops ok`。能 `import mmcv.ops` 才算真装成了，只 `import mmcv` 不算。

### 4.5 装 mmdet（必须是 2.x）

```bash
pip install mmdet==2.28.2
```

**验证**：

```bash
python -c "import mmdet; print(mmdet.__version__)"    # 期望：2.28.2
```

> ⛔ `pip install mmdet` 不写版本号会装到 **3.x**，与 mmrotate 0.x 不兼容，直接白干。

### 4.6 装 mmrotate

```bash
cd ~            # 或你放代码的地方
git clone https://github.com/open-mmlab/mmrotate.git
cd mmrotate
pip install -v -e .
```

- `-e` = editable（可编辑安装）：**装的是一个指向这个目录的软链接**。你以后改 `mmrotate/` 里的代码，立刻生效，不用重装。W2 之后你会天天改它，所以现在就用 `-e`。
- `-v` = verbose，出错时能看到更多信息。

**验证**：

```bash
python -c "import mmrotate; print(mmrotate.__version__)"   # 期望：0.3.4
```

### 4.7 三代版本对账（跑 demo 前的最后一道关）

```bash
python -c "import mmcv, mmdet, mmrotate; print('mmcv',mmcv.__version__,'| mmdet',mmdet.__version__,'| mmrotate',mmrotate.__version__)"
```

**期望输出**：`mmcv 1.7.2 | mmdet 2.28.2 | mmrotate 0.3.4`

对照官方兼容表（来源：MMRotate 仓库 `docs/en/faq.md`）：

| MMRotate | 需要 MMCV | 需要 MMDetection |
|---|---|---|
| **0.3.4 / main** | `mmcv-full>=1.5.3, <1.8.0` | `mmdet>=2.25.1, <3.0.0` |
| 0.3.3 / 0.3.2 | `mmcv-full>=1.5.3, <1.7.0` | `mmdet>=2.25.1, <3.0.0` |
| 0.3.1 / 0.3.0 | `mmcv-full>=1.4.5, <1.6.0` | `mmdet>=2.22.0, <3.0.0` |

> **半年后这张表过期了怎么办**（原手册想让你做、但没教你怎么做的那一步）：
> 打开 `https://github.com/open-mmlab/mmrotate` → 点 `docs/` → `en/` → `faq.md` → 页面开头第一张表就是它。**不用读英文正文，只看那张表的第一行（main 行）。**

### 4.8 ★★ 拿 config 和权重（原手册整段漏掉的一步）

**方式一：一条命令搞定（推荐）**

```bash
mim download mmrotate --config oriented_rcnn_r50_fpn_1x_dota_le90 --dest .
```

（如果提示 `mim: command not found`，先 `pip install -U openmim`。）

跑完当前目录会多出**两个**文件：

```text
oriented_rcnn_r50_fpn_1x_dota_le90.py      ← config，几 KB
oriented_rcnn_r50_fpn_1x_dota_le90-6d2b2ce0.pth   ← 权重，约 158 MB
```

**方式二：手动下（mim 抽风时用）**

config 其实仓库里就有，不用下：`configs/oriented_rcnn/oriented_rcnn_r50_fpn_1x_dota_le90.py`

权重必须下，完整地址是：

```bash
wget -c https://download.openmmlab.com/mmrotate/v0.1.0/oriented_rcnn/oriented_rcnn_r50_fpn_1x_dota_le90/oriented_rcnn_r50_fpn_1x_dota_le90-6d2b2ce0.pth
```

- `-c` = 断点续传。国内下这个站容易断，断了重跑同一条命令即可接着下。
- **文件大小应为 165,749,436 字节（约 158 MB）**。下完用 `ls -l` 核对——**如果只有几 KB，那是下到了一个 HTML 错误页，不是权重**。这个坑非常常见。

**怎么自己找别的模型的权重**（授人以渔）：

> 进 `https://github.com/open-mmlab/mmrotate` → `configs/` → 选一个方法目录（如 `oriented_rcnn/`）→ 打开里面的 `README.md` → 表格里每一行末尾都有 **model** 链接，那就是 `.pth` 地址；同一行的 config 列就是配套的 `.py`。**config 和权重必须成对使用，张冠李戴会报 `size mismatch`。**

### 4.9 跑 demo

确认你在 `mmrotate` 目录下，然后：

```bash
python demo/image_demo.py \
  demo/demo.jpg \
  configs/oriented_rcnn/oriented_rcnn_r50_fpn_1x_dota_le90.py \
  oriented_rcnn_r50_fpn_1x_dota_le90-6d2b2ce0.pth \
  --out-file result.jpg
```

四个位置参数的含义，对照第 1 节的三样东西：

| 位置 | 是什么 | 对应 |
|---|---|---|
| `demo/demo.jpg` | 输入图（仓库自带，不用下） | 数据 |
| `configs/.../oriented_rcnn_r50_fpn_1x_dota_le90.py` | 图纸 | ② config |
| `oriented_rcnn_..._le90-6d2b2ce0.pth` | 调校好的参数 | ③ checkpoint |
| `--out-file result.jpg` | 输出画到哪 | — |

**没有 GPU 就加一句**：

```bash
  --device cpu
```

**想看更多框（默认阈值 0.3）**：

```bash
  --score-thr 0.1
```

### 4.10 ③ 合格样例

- 终端**没有红色 Traceback**，安静地结束（中间可能有几行 UserWarning，**警告不是错误，忽略**）。
- 当前目录出现 `result.jpg`。
- 打开它：一张俯视的停车场/街区图，上面套着一圈**斜着的彩色框**，框住车辆等目标。

**看到这张图 = 今晚赢了。** 立刻做两件事：

1. 截图存进 `RS-CV/20-代码实验/W1D1-环境SOP/` （上午段建的知识库派上用场了）。
2. 顺手换一张你自己的图试试（任何俯拍图都行）：
   ```bash
   python demo/image_demo.py 你的图.jpg configs/oriented_rcnn/oriented_rcnn_r50_fpn_1x_dota_le90.py oriented_rcnn_r50_fpn_1x_dota_le90-6d2b2ce0.pth --out-file my_result.jpg
   ```
   **换图不换 config/权重** —— 这一下你就真懂三者的分工了。

### 4.11 一键脚本（存下来，换机器时直接跑）

```bash
#!/usr/bin/env bash
# install_mmrotate.sh —— MMRotate 0.3.4 一键环境（示例配置：CUDA 11.8 / torch 2.0.1 / Python 3.9）
set -e

conda create -n mmrot python=3.9 -y
source activate mmrot

pip install torch==2.0.1 torchvision==0.15.2 --index-url https://download.pytorch.org/whl/cu118
python -c "import torch; assert torch.__version__.startswith('2.0.1'); print('torch ok', torch.cuda.is_available())"

pip install "numpy<2" "yapf==0.40.1" "setuptools<70"
pip install mmcv-full==1.7.2 -f https://download.openmmlab.com/mmcv/dist/cu118/torch2.0/index.html
python -c "from mmcv.ops import nms_rotated; print('mmcv ops ok')"

pip install mmdet==2.28.2
pip install -U openmim

git clone https://github.com/open-mmlab/mmrotate.git
cd mmrotate
pip install -v -e .

mim download mmrotate --config oriented_rcnn_r50_fpn_1x_dota_le90 --dest .

python demo/image_demo.py demo/demo.jpg \
  configs/oriented_rcnn/oriented_rcnn_r50_fpn_1x_dota_le90.py \
  oriented_rcnn_r50_fpn_1x_dota_le90-6d2b2ce0.pth \
  --out-file result.jpg

echo "全部完成，看 $(pwd)/result.jpg"
```

用法：`chmod +x install_mmrotate.sh && ./install_mmrotate.sh`

---

## 5. ④⑤ 报错急救手册

### 5.0 先学会读报错（这个技能比这张表值钱）

1. **从下往上读。** Traceback 最后一行 `XxxError: 具体信息` 才是真正的错，上面几十行是调用路径。
2. **提取"可搜索的那一句"。** 把最后一行里**你自己的路径、文件名、数字**删掉，只留通用部分。
   - 原始：`FileNotFoundError: [Errno 2] No such file: '/home/zhang/mmrotate/oriented_rcnn_xxx.pth'`
   - 拿去搜：`mmrotate FileNotFoundError checkpoint No such file`
3. **搜索的地方按顺序**：① 本页第 5.1 节表格 → ② `https://github.com/open-mmlab/mmrotate/issues` 右上 Search（**记得把过滤器从 `is:open` 删掉，很多答案在已关闭的 issue 里**）→ ③ Google 加英文报错原文 → ④ CSDN / 知乎搜中文报错。
4. **一个错查 20 分钟没解决就止损**，记进 SOP 的"待解决"，走保底路线。

### 5.1 症状 → 原因 → 解药

| # | 报错原文（关键部分） | 真正原因 | 解药 |
|---|---|---|---|
| 1 | `AssertionError: MMCV==2.x.x is used but incompatible. Please install mmcv>=1.x, <1.x` | 装了 1.x 代的 mmcv，mmrotate 是 0.x 代 | `pip uninstall mmcv mmcv-full -y`，重做 4.4 |
| 2 | `ModuleNotFoundError: No module named 'mmcv._ext'` 或 `No module named 'mmcv.ops'` | 装成了 `mmcv` / `mmcv-lite`（无 CUDA 算子），或源码编译失败 | 卸干净后**必须**装 `mmcv-full`，且带 `-f` 索引 |
| 3 | pip 在下载 `mmcv-full-1.7.2.tar.gz` 而不是 `.whl` | `-f` 索引里没有匹配你 torch/Python 的预编译包 | Ctrl+C。检查 Python 是否 3.11+；核对 `-f` URL 里的 cu/torch；把 `torch2.0` 试成 `torch2.0.0` |
| 4 | `TypeError: FormatCode() got an unexpected keyword argument 'verify'` | yapf ≥ 0.40.2 删了 `verify` 参数 | `pip install yapf==0.40.1` |
| 5 | `AttributeError: module 'numpy' has no attribute 'float'` / numpy ABI 报错 | numpy 2.x | `pip install "numpy<2"` |
| 6 | `KeyError: 'OrientedRCNN is not in the models registry'` | 没装 mmrotate，或用 API 时忘了 `import mmrotate` | 确认 4.6 成功；Python 里**必须**有 `import mmrotate` 这一行来触发注册 |
| 7 | `FileNotFoundError: ... .pth` | **权重根本没下**（原手册漏掉的那步）或路径写错 | 回到 4.8。`ls -l *.pth` 确认存在且约 158 MB |
| 8 | `RuntimeError: CUDA error: no kernel image is available for execution on the device` | 预编译的 mmcv 不含你显卡的架构（常见于 RTX 40/50 系配老 CUDA） | 换更高 CUDA 的组合（cu118 起）；或最后手段本地编译：`TORCH_CUDA_ARCH_LIST="8.9" pip install mmcv-full==1.7.2`（8.9 是 40 系；50 系用 9.0） |
| 9 | `ImportError: ... undefined symbol: _ZN3c10...` | mmcv 编译时的 torch 版本 ≠ 当前 torch | 两者对齐重装；**先卸 mmcv-full 再换 torch**，顺序反了还会错 |
| 10 | `AssertionError: MMDetection 3.x is incompatible` | mmdet 装成 3.x | `pip install mmdet==2.28.2` |
| 11 | `ImportError: libGL.so.1: cannot open shared object file` | 无桌面的服务器缺 OpenCV 的图形库 | `pip install opencv-python-headless`；有 root 则 `apt install -y libgl1 libglib2.0-0` |
| 12 | 下载 `.pth` 极慢 / 中断 / 下完只有几 KB | 网络问题；几 KB 的是错误页不是权重 | `wget -c` 续传；或用浏览器直接打开那个 URL 下载后拷进目录 |
| 13 | `Microsoft Visual C++ 14.0 or greater is required` | Windows 原生缺编译器 | **别装 VS 了，去装 WSL2 + Ubuntu**，在里面重做，省几小时 |
| 14 | `size mismatch for ... : copying a param with shape ...` | config 和权重不配套（张冠李戴） | 回 4.8，从同一个 README 表格的**同一行**取 config 和 model |
| 15 | 大量 `UserWarning` / `DeprecationWarning`，但没有 Traceback | 不是错误 | **忽略。** 老框架配新 Python 必然一堆警告，只要 `result.jpg` 出来了就是成功 |

---

## 6. 路线 C：保底方案（10 分钟出旋转框结果图）

**什么时候用**：路线 A 卡满 2 小时，或今晚只剩一小时。

Ultralytics 的 YOLO-OBB 系列自带在 **DOTAv1 上预训练的旋转框模型**，权重首次运行**自动下载**，没有 mmcv 那套编译依赖。

```bash
conda create -n obb python=3.10 -y
conda activate obb
pip install ultralytics

# 用任意一张俯拍图（航拍/卫星截图都行），权重会自动下载
yolo obb predict model=yolo11n-obb.pt source=你的图.jpg save=True
```

结果默认存在 `runs/obb/predict/` 下。打开就能看到斜框。

**必须说清楚的三件事，别自己骗自己**：

1. **这不算作弊**。今晚的目标是"亲眼看到旋转框检测的输出、理解 config+权重+推理这条链路"，路线 C 同样达成。
2. **但它替代不了路线 A**。W2 要复现的 Oriented R-CNN、后面所有和论文对齐的实验，学术界都以 MMRotate 为准。**路线 A 必须补上**，只是可以挪到明后天。
3. **Ultralytics 是 AGPL-3.0 协议**。自己学习、写论文没问题；将来若涉及闭源商用要另外买授权。现在知道有这回事就行。

**⑥ 这一步你学会了什么**：**任何一个技术目标都该准备 Plan B**。研究里最贵的不是走错路，是在一条路上耗到失去信心。

---

## 7. 今晚的《环境搭建 SOP》怎么写（≥800 字，直接套这个骨架）

原手册说"SOP 不是流水账，是遇到 X 报错 → 用 Y 解决的可复用手册"。但没给模板。用下面这个，填完自然超过 800 字：

```markdown
# 环境搭建 SOP · v1（W1-D1）

## 0. 我的机器
- 系统 / 显卡 / 驱动版本 / nvidia-smi 显示的 CUDA：
- Python：3.9   conda 环境名：mmrot

## 1. 最终成功的版本组合（★下次直接照抄这一段）
| 组件 | 版本 | 装法 |
|---|---|---|
| torch / torchvision | 2.0.1 / 0.15.2 | pip + --index-url cu118 |
| numpy / yapf / setuptools | <2 / 0.40.1 / <70 | 先按住再装 mm 系列 |
| mmcv-full | 1.7.2 | pip + -f 预编译索引 |
| mmdet | 2.28.2 | pip |
| mmrotate | 0.3.4 | git clone + pip install -v -e . |

## 2. 完整命令流水（可直接复制重放）
（把 4.11 的脚本贴进来，改成你实际用的版本号）

## 3. 我今晚踩的坑（★最值钱的一段，每条按下面格式写）
### 坑 1：<报错最后一行原文>
- 出现在哪一步：
- 我一开始以为是：
- 实际原因：
- 解决命令：
- 花了多久：
- 下次怎么避免：

### 坑 2：…

## 4. 验证四连（换机器后按这个顺序自查）
1. torch.cuda.is_available() → True
2. from mmcv.ops import nms_rotated → 不报错
3. import mmdet, mmrotate → 版本号对得上兼容表
4. demo 出图 → result.jpg 有斜框

## 5. 遗留问题 / 待办
-

## 6. 关键文件在哪
- 代码：~/mmrotate
- 权重：~/mmrotate/*.pth（158 MB，已加进 .gitignore）
- 结果图：~/mmrotate/result.jpg
```

> **一个小纪律**：`.pth` 权重、数据集**永远不要提交进 git**。现在就在 `mmrotate/.gitignore` 里确认有 `*.pth`。这个习惯在 M3-W11 正式学 git 时会再讲一次，但今天就该有。

---

## 8. ⑥ 今晚你同时学会了什么 + 验收清单

**你以为你在装软件，其实你练的是这四件事**：

1. **分清"代码 / 配置 / 权重"三件套** —— 这是所有深度学习项目复现的通用结构，换成任何框架都成立。
2. **版本代际的概念** —— 以后看到任何项目的 README 写着"本代码基于 X 1.5、Y 2.3"，你会先对表再动手，而不是无脑装最新。
3. **预编译包 vs 源码编译** —— 知道 pip 输出里 `.whl` 和 `.tar.gz` 的区别意味着什么，这一条能帮你省下无数个小时。
4. **报错的检索方法** —— 从下往上读、去掉个人路径、去 issue 搜原文（含已关闭的）。

**今晚验收清单**（三个都打勾才算结束）：

- [ ] `python -c "import torch;print(torch.cuda.is_available())"` → `True`（没 N 卡则跳过）
- [ ] `result.jpg` 存在，图上有斜框（路线 A 或 C 都算）
- [ ] 《环境搭建 SOP》写完，其中"我今晚踩的坑"至少有 1 条

> **技能卡｜复现任何一份深度学习代码的六步**
> ① 看 README 的版本要求（代际）→ ② 建独立环境 → ③ 装对 CUDA 的 torch 并验证 → ④ 按住老旧依赖（numpy/setuptools 等）→ ⑤ 装框架，优先预编译包 → ⑥ **单独下载 config 和权重**，跑 demo 验证。
> 这六步你后面两年会用几十次。今晚是第一次。

**明天怎么接**：D2 早上读论文（Zhu 2017），和今晚的环境无关，正常进行。如果今晚走的是路线 C，把路线 A 排进 D2 或 D3 的晚上段——**别让它拖过 W1**，因为 W2-D8 的 Oriented R-CNN baseline 要用它。
