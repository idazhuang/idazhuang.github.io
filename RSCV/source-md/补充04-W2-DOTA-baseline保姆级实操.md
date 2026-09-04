# 补充 04 · W2 ·「DOTA 数据 → 切图 → config → 训练 → 评测」保姆级实操
## 原 W2 给了命令，但四道闸门每一道都缺了会卡死你的那一步

> **这一页替代什么**：替代 W2 的 **D8 晚上段**（准备 config）、**D9 中午段**（切图）、**D9 晚上段**（启动训练）、**D11 中午段**（跑评估）四格的动手部分。原文有代码块，比 W1-D1 强，但四处关键缺口会让你在周三之前全部卡死：
>
> | 原文说 | 实际缺了什么 | 后果 |
> |---|---|---|
> | "把 DOTA 下下来"（W1-D5） | **没给下载地址、没给目录结构要求** | 下完摆错位置，切图脚本直接报错 |
> | "参数照官方文档"跑切图 | **没说必须先编辑那个 json 里的路径** | 脚本找不到数据，或切出 0 张图 |
> | "用你 D8 改好的 config" | **从没给出这个文件该写什么** | 不知道从哪下笔 |
> | "改 batch_size 适配 4090" | **没说学习率要不要跟着改** | 改错方向 → loss 直接 nan |
> | "跑评估脚本，记录 mAP" | **没给命令，也没说 DOTA test 集没有标注** | 在 test 上评测得到全 0，以为模型废了 |
>
> **本周及格线**：`work_dirs/` 里有一个训练完的 `.pth`，`tools/test.py --eval mAP` 打印出一个 60–75 之间的 mAP 数字。**不要求达到论文的 75.69**，单卡 + 单尺度能到 68–73 就是正常的。

---

## 1. 先垫概念：这一周你要跨四道闸

复现任何一个检测 baseline，永远是这四步，顺序不能乱：

```text
① 数据就位  →  ② 数据变成框架要的形状  →  ③ config 写对  →  ④ 训练 → ⑤ 评测
   (下载解压)      (DOTA 特有：切图)          (继承+改路径+改lr)
```

**每一道闸的失败长相不同**，先记住，出问题时能立刻定位：

| 闸 | 失败长相 |
|---|---|
| ① 数据 | `FileNotFoundError` / 找不到 `labelTxt` |
| ② 切图 | 切出 0 张图，或切完框的位置不对 |
| ③ config | `KeyError` / 训练能起但 loss 是 nan / 类别数不对 |
| ④ 训练 | OOM 爆显存 / loss 不降 / 慢到离谱 |
| ⑤ 评测 | mAP = 0.000（**九成是在没标注的 test 集上评的**） |

---

## 2. 闸一：DOTA 数据集（W1-D5 就该开始下，原文没给地址）

### 2.1 去哪下

**官网**：`https://captain-whu.github.io/DOTA/dataset.html`

页面上 DOTA-v1.0 分成 **train / val / test** 三块，每块都给了 Google Drive 和百度网盘两个入口。**国内用百度网盘那一列。**

**★ 先下 val，不要等 train。** val 只有约 450 张原图（1–2 GB），**足够你把整条流程跑通**。train 有 1400+ 张、十几 GB，让它在后台慢慢下。

> **这是原手册没教、但能救你两天的策略**：**用小数据先打通流程，再换大数据。** 你后面两年每次接触新数据集都该这么干。

### 2.2 解压成什么目录结构（★ 切图脚本硬性要求）

下下来是若干个分卷压缩包。解压后**必须**摆成这个样子，一个字母都不能差：

```text
data/DOTA/
├── train/
│   ├── images/          ← 全部 .png 原图
│   └── labelTxt/        ← 同名 .txt 标注，注意大小写：labelTxt
├── val/
│   ├── images/
│   └── labelTxt/
└── test/
    └── images/          ← 只有图，没有 labelTxt（见 §6，这点很重要）
```

**验证目录摆对了没有**：

```bash
cd data/DOTA
ls train/images | wc -l      # 期望：1411 左右
ls train/labelTxt | wc -l    # 期望：和上面同一个数
ls val/images | wc -l        # 期望：458 左右
ls test/images | wc -l       # 期望：937 左右
head -3 train/labelTxt/$(ls train/labelTxt | head -1)
```

最后一条应打印出类似：

```text
imagesource:GoogleEarth
gsd:0.146343590398
2753.0 2408.0 2861.0 2385.0 2888.0 2468.0 2805.0 2493.0 plane 0
```

**读懂这一行**（W1-D6 写解析脚本时正是解析它）：**8 个数 = 旋转框的四个角点 (x1,y1,x2,y2,x3,y3,x4,y4)**，然后是**类别名**，最后一个 `0/1` 是 **difficult 标志**（1 = 难样本，评测时通常忽略）。前两行是元信息，`gsd` 就是《名词逐个讲透》里说的地面采样距离。

### 2.3 磁盘预算（原文完全没提，很多人切到一半磁盘满）

| 项 | 大小 |
|---|---|
| DOTA-v1.0 原始（train+val+test） | 约 20 GB |
| 切图后（1024×1024, gap 200, 单尺度） | **约 30–40 GB** |
| 训练产生的 checkpoint（12 epoch，每 epoch 存一个） | 约 12 × 160 MB ≈ 2 GB |
| **建议预留** | **100 GB** |

**省空间的两招**：① config 里设 `checkpoint_config = dict(interval=4, max_keep_ckpts=2)`，别每个 epoch 都存；② 切图只切 train+val，test 等真要提交榜单时再切。

---

## 3. 闸二：切图（原文给了命令，但漏了"必须先改 json"）

### 3.1 为什么必须改 json

原文那条命令：

```bash
python tools/data/dota/split/img_split.py --base-json tools/data/dota/split/split_configs/ss_trainval.json
```

**这条命令本身没错，但直接跑一定失败**——因为那个 json 里写的是作者机器上的路径。你必须先打开它改成你的。原文注释里有一句"改 json 里的路径指向你的 DOTA"，但**没说改哪几个字段、改成什么样**。

### 3.2 具体改什么

```bash
cat tools/data/dota/split/split_configs/ss_trainval.json
```

改成下面这样（**只有 `img_dirs` / `ann_dirs` / `save_dir` 三处要动，其余保持原样**）：

```json
{
  "nproc": 8,
  "img_dirs": [
    "data/DOTA/train/images/",
    "data/DOTA/val/images/"
  ],
  "ann_dirs": [
    "data/DOTA/train/labelTxt/",
    "data/DOTA/val/labelTxt/"
  ],
  "sizes": [1024],
  "gaps": [200],
  "rates": [1.0],
  "img_rate_thr": 0.6,
  "iof_thr": 0.7,
  "no_padding": false,
  "padding_value": [104, 116, 124],
  "save_dir": "data/split_ss_dota/trainval/",
  "save_ext": ".png"
}
```

**每个字段在干什么**（原文一个都没解释）：

| 字段 | 含义 | 动不动 |
|---|---|---|
| `img_dirs` / `ann_dirs` | 输入图和标注目录，**必须一一对应、末尾带斜杠** | ★改 |
| `save_dir` | 切完存哪 | ★改 |
| `sizes` | patch 边长，1024 | 别动 |
| `gaps` | 相邻 patch 的重叠像素 = 原文说的 overlap | 别动 |
| `rates` | 缩放倍率。`[1.0]` = 单尺度；多尺度是 `[0.5,1.0,1.5]`，**图会多 3 倍，先别用** | 别动 |
| `img_rate_thr` | patch 里有效像素占比低于它就丢弃（边角空白块） | 别动 |
| `iof_thr` | 目标被切掉多少就不再算这个 patch 的标注 | 别动 |
| `nproc` | 并行进程数，按你的 CPU 核数调 | 可调 |

**再准备一份只切 test 的**（test 没有标注，`ann_dirs` 要留空）：

```bash
cat tools/data/dota/split/split_configs/ss_test.json   # 同理改 img_dirs 和 save_dir，ann_dirs 保持 []
```

### 3.3 跑起来 + 期望输出

```bash
cd ~/mmrotate
python tools/data/dota/split/img_split.py \
    --base-json tools/data/dota/split/split_configs/ss_trainval.json
```

**你应该看到**：进度条跑完，最后打印处理了多少张。然后：

```bash
ls data/split_ss_dota/trainval/images | wc -l     # 期望：约 21000–22000 张
ls data/split_ss_dota/trainval/annfiles | wc -l   # 期望：和上面同一个数
```

> **注意输出目录里标注文件夹叫 `annfiles`，不是 `labelTxt`。** 这是切图脚本的输出约定，后面写 config 时要用对名字。**这是新手在闸三卡住的常见原因。**

### 3.4 抽查一张（务必做，别跳）

用 W1-D6 写的 `vis_dota.py`，随便挑一张切块可视化，**确认框还套在目标上**。切图脚本会重算坐标，如果目录摆错、或者你用了错误的 `ann_dirs`，切出来的框会整体错位——**这时候框是错的但脚本不报错**，你会一路训练到周四才发现。

### 3.5 常踩的坑

| 坑 | 症状 | 解 |
|---|---|---|
| 路径末尾漏斜杠 | 找不到文件 | `img_dirs` 每项末尾都要 `/` |
| `labelTxt` 大小写写错 | 切出图但没有标注 | 严格照 §2.2 的大小写 |
| 把 test 也放进 `ss_trainval.json` | 报错找不到 test 的 labelTxt | test 单独用 `ss_test.json` |
| 磁盘满，切到一半停 | 进程被杀 | `df -h` 看剩余空间，见 §2.3 |
| 用了多尺度 `rates` | 切出 6 万多张、磁盘爆 | 第一次复现坚持 `[1.0]` |

---

## 4. 闸三：config（原文说"D8 改好的"，但从没给出内容）

### 4.1 先懂 MM 框架的 config 继承

MM 系框架的 config 是**层层继承**的。`configs/oriented_rcnn/oriented_rcnn_r50_fpn_1x_dota_le90.py` 开头是：

```python
_base_ = ['../_base_/datasets/dotav1.py',
          '../_base_/schedules/schedule_1x.py',
          '../_base_/default_runtime.py']
```

意思是"我继承这三个基础配置，然后只写我要改的部分"。**你要做的不是去改官方 config，而是新建一个继承它的自己的 config。**

> **纪律**：**永远不要直接编辑 `configs/` 下的官方文件。** 改了之后你就再也说不清自己的实验和官方基线差在哪，也没法 `git pull` 更新。**新建一个自己的文件，继承它。** 这条纪律你后面两年每次实验都要用。

### 4.2 你的第一个 config（完整内容，可直接用）

新建 `configs/my/my_orcnn_r50.py`：

```python
# configs/my/my_orcnn_r50.py
# 继承官方 Oriented R-CNN 基线，只改：数据路径 + batch + 存盘策略
_base_ = ['../oriented_rcnn/oriented_rcnn_r50_fpn_1x_dota_le90.py']

# ---------- 1) 指向你切好的数据 ----------
data_root = 'data/split_ss_dota/'
angle_version = 'le90'

data = dict(
    samples_per_gpu=2,      # 单卡每批 2 张，4090 24G 够用；显存不足改 1（★然后必须改 lr，见下）
    workers_per_gpu=2,      # 数据加载线程；CPU 弱或内存小就调到 1
    train=dict(
        ann_file=data_root + 'trainval/annfiles/',   # 注意是 annfiles，切图脚本的输出名
        img_prefix=data_root + 'trainval/images/'),
    val=dict(
        ann_file=data_root + 'trainval/annfiles/',
        img_prefix=data_root + 'trainval/images/'),
    test=dict(
        ann_file=data_root + 'trainval/annfiles/',   # ★ 先指向 trainval，理由见 §6
        img_prefix=data_root + 'trainval/images/'))

# ---------- 2) 学习率（★ 原手册完全没提这一节）----------
# MMRotate 的 DOTA config 默认就是"单卡 × 每卡 2 张"，lr=0.005 与之配套。
# 所以你在 4090 上用 samples_per_gpu=2 时：lr 不用改。
# 只有当你因为显存把 batch 改成 1 时，才要按线性缩放规则减半：
# optimizer = dict(lr=0.0025)

# ---------- 3) 省磁盘 ----------
checkpoint_config = dict(interval=4, max_keep_ckpts=2)   # 每 4 epoch 存一次，最多留 2 个
evaluation = dict(interval=4, metric='mAP')              # 每 4 epoch 在 val 上评一次
```

### 4.3 ★ 学习率与 batch：一个和直觉相反的点

原文说"改 batch_size 适配 4090"，**但没说学习率要不要跟着改**。这是本周最容易把训练搞崩的地方，而且很多人搞反了方向。

**线性缩放规则（Linear Scaling Rule）**：`总 batch` 变成原来的 k 倍，`lr` 也要变成 k 倍。

**关键事实**：MMDetection 的 COCO config 默认是 **8 卡 × 2 张 = 总 batch 16**，所以单卡跑必须把 lr 除以 8。**但 MMRotate 的 DOTA config 不是**——它默认就是**单卡 × 2 张 = 总 batch 2**，`lr=0.005` 就是为这个配的。

| 你的设置 | 总 batch | lr 该设多少 |
|---|---|---|
| 单卡，`samples_per_gpu=2` | 2 | **0.005（不用改，就是默认值）** |
| 单卡，`samples_per_gpu=1`（显存不够） | 1 | **0.0025** |
| 单卡，`samples_per_gpu=4`（显存宽裕） | 4 | 0.01 |

> **所以在 4090 上跑 batch 2，你什么都不用改。** 但你必须**知道为什么不用改**——因为下周你换个 MMDetection 的 COCO config，同样的操作就必须把 lr 除以 8，否则第一个 epoch 就 nan。
>
> **判断任何 config 默认几卡的方法**：看文件名。MM 系约定文件名里的 `_8x2_` 表示 8 卡每卡 2 张；**没写数字的，去看它 `_base_` 里的 schedule 文件，或看仓库 README 里那一行的 "batch size" 列**。

### 4.4 验证 config 真的生效了

**别直接开训。** 先把最终展开的配置打出来看一眼：

```bash
python tools/misc/print_config.py configs/my/my_orcnn_r50.py | grep -E "ann_file|img_prefix|samples_per_gpu|lr=|num_classes"
```

**你应该看到**：`ann_file` 和 `img_prefix` 都指向你 `data/split_ss_dota/` 下的路径、`samples_per_gpu=2`、`lr=0.005`、`num_classes=15`。

**有一个不对就先别训**——一次训练几小时，路径错了等于白烧半天电。

---

## 5. 闸四：训练

### 5.1 先 dry-run，别直接挂 12 个 epoch

```bash
# 只跑 1 个 epoch，且每 50 iter 打一次日志，看看能不能正常跑起来
python tools/train.py configs/my/my_orcnn_r50.py \
    --work-dir work_dirs/dryrun \
    --cfg-options runner.max_epochs=1 log_config.interval=50
```

**盯前 200 个 iter 的 loss**，这是判断训练健不健康的窗口：

```text
Epoch [1][50/10800]  lr: 1.978e-03, loss_rpn_cls: 0.4321, loss_rpn_bbox: 0.1234,
                     loss_cls: 0.8765, acc: 87.5, loss_bbox: 0.5432, loss: 1.9752
```

| 现象 | 判断 | 动作 |
|---|---|---|
| total loss 从 ~2 稳步往下走 | ✅ 健康 | Ctrl+C，去跑正式的 |
| loss 出现 `nan` | ❌ lr 太高 | 按 §4.3 把 lr 减半 |
| loss 卡在某个值不动 | ⚠️ 多半是数据/标注错了 | 回 §3.4 抽查可视化 |
| `acc` 一直 100 但 loss 不降 | ⚠️ 标注全空 | `ann_file` 路径写错，回 §4.4 |
| 一个 iter 好几秒 | ⚠️ 没吃满 GPU | `nvidia-smi` 看利用率；调 `workers_per_gpu` |

### 5.2 正式训练

```bash
tmux new -s train
# 在 tmux 里：
python tools/train.py configs/my/my_orcnn_r50.py --work-dir work_dirs/orcnn_r50
# Ctrl+B 然后按 D 脱离；回来看：tmux attach -t train
```

**同时把这三样记进 `20-代码实验/实验日志.md`**（原文强调了，照做）：完整命令、`work_dir` 路径、启动时间。

**时间预期**：单张 4090、约 2.1 万张切块、12 epoch，**大约 8–14 小时**。周二晚挂上，周三早上看结果，正好对上原手册的节奏。

### 5.3 OOM 的处理顺序（按这个顺序试，别乱改）

1. `samples_per_gpu=2` → `1`，**同时把 lr 改成 0.0025**（§4.3）
2. config 里加 `fp16 = dict(loss_scale='dynamic')`（混合精度，省一半显存、还更快）
3. backbone 里加 `with_cp=True`（用时间换显存）
4. 还不行 → `nvidia-smi` 看是不是有别的进程占着显存，先杀掉

---

## 6. 闸五：评测（★ 原文只有一句"跑评估脚本"，而这里有个大陷阱）

### 6.1 ★★ DOTA 的 test 集没有公开标注

**这是新手在 W2 最常见的崩溃点**：在 test 集上跑评测，得到 `mAP: 0.0000`，以为训练全白费了。

**真相**：DOTA 是有排行榜的基准数据集，**test 集的标注被官方扣着**，你下下来的 `test/` 目录里**只有 images 没有 labelTxt**。想知道 test 上的分数，只能把预测结果按格式打包，提交到官方评测服务器。

**所以第一次复现的正确做法**：**在 val 上评测。** 上面 §4.2 的 config 里 `test=` 指向 trainval 就是为这个准备的。

> **更严谨的做法**（第二次做实验时改）：切图时把 train 和 val 分开切成两个目录，用 train 训、用 val 评。**第一次复现先把流程跑通，允许 train/val 混在一起——但你要知道这时候的 mAP 是偏高的，不能写进论文。** 这个区分现在就要建立，否则你 M5 做主实验时会出大问题。

### 6.2 评测命令

```bash
python tools/test.py \
    configs/my/my_orcnn_r50.py \
    work_dirs/orcnn_r50/latest.pth \
    --eval mAP
```

**期望输出**：一张 15 类的 per-class AP 表，最后一行是 mAP。

```text
+--------------------+------+-------+--------+-------+
| class              | gts  | dets  | recall | ap    |
+--------------------+------+-------+--------+-------+
| plane              | 4449 | 10832 | 0.945  | 0.892 |
| baseball-diamond   |  358 |  2841 | 0.849  | 0.771 |
| ...                |      |       |        |       |
+--------------------+------+-------+--------+-------+
| mAP                |      |       |        | 0.7?? |
+--------------------+------+-------+--------+-------+
```

**这张表就是 D11 晚上段要你分析的 per-class AP。** 重点看哪几类特别低——通常是 `small-vehicle`（太小）、`bridge`（细长、跨块被切断）、`roundabout`（形状特殊）。**这些低分类别就是你未来找 Gap 的第一批线索**，把它们记进 `10-论文笔记/待做idea.md`。

### 6.3 你的数字应该是多少

官方 model zoo 上 `oriented_rcnn_r50_fpn_1x_dota_le90` 的 **mAP = 75.69**，但那是**在官方 test 服务器上、按官方切图协议**得到的。

| 你的情况 | 合理区间 |
|---|---|
| 单卡、单尺度、在 val 上评 | **68–75** |
| 差得很远（< 50） | 回 §3.4 查切图标注是否错位 |
| 高得离谱（> 85） | 多半是 train/val 数据泄漏（§6.1），正常，第一次可以接受 |

> **原手册说"复现报告"要写，这里补一句写法**：报告里**必须写清你的评测协议**——在哪个 split 上评的、单尺度还是多尺度、用的哪种 mAP 算法（见《名词逐个讲透》§5.3）。**不写清协议的数字等于没有数字**，这是学术规范，现在就要养成。

### 6.4 想跑 test 提交榜单（可选，第一次可跳过）

```bash
python tools/test.py configs/my/my_orcnn_r50.py work_dirs/orcnn_r50/latest.pth \
    --format-only --eval-options submission_dir=work_dirs/submission
```

这会把切块上的预测**合并回原图坐标**并打包成官方要求的格式。打包好的文件提交到 DOTA 官网的评测服务器。**这一步等你 M2 真要对榜时再做。**

---

## 7. W2 专属报错急救表

| 报错 / 症状 | 原因 | 解 |
|---|---|---|
| 切图跑完 0 张图 | json 里路径错，或末尾漏 `/` | 回 §3.2 |
| `FileNotFoundError: .../labelTxt` | 目录名大小写错，或把 test 放进了 trainval 的 json | 回 §2.2 / §3.5 |
| 训练启动即 `KeyError: 'ann_file'` | config 里 `data=dict(...)` 结构写错 | 用 §4.2 的完整版覆盖 |
| loss 第一个 epoch 就 `nan` | lr 相对 batch 太大 | §4.3，lr 减半 |
| `CUDA out of memory` | batch 太大 | §5.3 按顺序试 |
| `mAP: 0.0000` | **在没标注的 test 上评** | §6.1，改评 val |
| mAP 只有个位数 | 切图后框错位 / `ann_file` 指错目录 | §3.4 可视化抽查 |
| 训练极慢，GPU 利用率忽高忽低 | 数据加载是瓶颈 | 调 `workers_per_gpu`；数据放 SSD 不要放机械盘/网盘 |
| `latest.pth` 不存在 | 训练还没存过盘，或 `max_keep_ckpts` 把它删了 | `ls work_dirs/orcnn_r50/` 看实际文件名 |

---

## 8. 本周验收清单

- [ ] `data/DOTA/` 目录结构符合 §2.2，`head` 能打印出标注行
- [ ] `data/split_ss_dota/trainval/` 下有约 2 万张切块 + 同数量 annfiles
- [ ] 抽查一张切块，可视化后框仍套在目标上
- [ ] `configs/my/my_orcnn_r50.py` 存在，`print_config.py` 检查全部正确
- [ ] dry-run 前 200 iter loss 稳步下降，无 nan
- [ ] `work_dirs/orcnn_r50/` 里有训练完的 `.pth`
- [ ] `--eval mAP` 打印出 per-class 表，mAP 在 68–75
- [ ] 《DOTA baseline 复现报告》写完，**其中写清了评测协议**
- [ ] per-class 里最低的 3 类已记进 `待做idea.md`

> **技能卡｜复现任何检测 baseline 的五道闸**
> ① 数据就位（先用小 split 打通）→ ② 转成框架要的形状 → ③ **新建继承式 config，绝不改官方文件** → ④ dry-run 看前 200 iter，再挂正式训练 → ⑤ 评测**先确认这个 split 有没有标注**，并记录评测协议。
> 这五道闸你在 W3（SAR baseline）、W5（分割/变化检测）、M5（主实验）会一模一样地再走一遍。**W2 是唯一一次有人牵着你走，后面要自己走。**
