<div align="center">

<img src="assets/banner.png" alt="Primer Premier 5 Primer Design Skill" width="100%">

# Primer Premier 5 · Primer Design Skill

**一条 FASTA 进去，38 列引物报告出来。**
ORF 分析 → PP5 原生候选 → 全模板 False Priming 复核 → Primer-BLAST 分层特异性 → 带截图的 Excel

<p>
<a href="https://github.com/Didnotchangename/primer-premier-design-skill/stargazers"><img src="https://img.shields.io/github/stars/Didnotchangename/primer-premier-design-skill?style=flat-square&color=5EEAD4" alt="Stars"></a>
<a href="https://github.com/Didnotchangename/primer-premier-design-skill/releases"><img src="https://img.shields.io/github/v/release/Didnotchangename/primer-premier-design-skill?style=flat-square&color=A78BFA" alt="Release"></a>
<a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-7DD3FC?style=flat-square" alt="License"></a>
<img src="https://img.shields.io/badge/platform-macOS%20%2B%20CrossOver-94A3B8?style=flat-square" alt="Platform">
<img src="https://img.shields.io/badge/agent-Codex%20%7C%20Claude%20Code%20%7C%20Cursor-94A3B8?style=flat-square" alt="Agent">
</p>

**简体中文** · [English](#english)

</div>

---

> **TL;DR** — 这不是又一个 Primer3 封装。它驱动**真实的 Primer Premier 5 桌面程序**（通过 CrossOver/Win32 消息接口），保留软件原生候选、原生 ΔG、原生结构警告和界面截图，然后逐对做 Primer-BLAST。给的是能直接进实验记录本的东西，不是一堆坐标。

<!-- 把上面替换成 10 秒演示 GIF。这是整个仓库最值钱的一张图。 -->
<!-- <div align="center"><img src="assets/demo.gif" width="90%"></div> -->

## 为什么需要它

实验室里设计引物的真实流程通常是：人在 PP5 里点半天 → 手动抄 F/R 序列 → 一个一个去 NCBI 贴 Primer-BLAST → 截图 → 拼 Excel。几十条序列就是几个通宵，而且**抄错一位碱基就白做**。

这个技能把这条路自动化了，但**没有偷工减料**：

| 普通脚本的做法 | 这个技能的做法 |
| --- | --- |
| 自己实现 Tm/GC 公式，结果和软件对不上 | 调用真实 PP5，保留原生评分、原生 ΔG、原生结构警告 |
| 只在 ORF 窗口里查 False Priming | 在**完整输入模板**上重新复核并记录模板长度 + SHA |
| 一对引物的 BLAST 结论套给备用对 | 首选、备选**逐对**独立提交，逐对记录物种/数据库/状态 |
| 只给序列坐标 | 每对都附**真实 PP5 结果窗口截图**并嵌入 Excel |
| 拿不到的参数就填 0 或"通过" | 未获取 = 未获取，未检查 = 未检查，绝不伪造 |

## 工作流

```mermaid
flowchart LR
    A([FASTA / Excel 输入]) --> B[输入核对<br/>方向 · 长度 · 模糊碱基]
    B --> C[ORF 分析<br/>NCBI ORFfinder 六框]
    C --> D[真实 PP5 设计<br/>CrossOver bottle + Win32<br/>三轮原生搜索]
    D --> E[独立复核<br/>F/R 反向互补 · 坐标 ·<br/>ORF 覆盖率 · 全模板 FP]
    E --> F[Primer-BLAST<br/>逐对 · 分物种分库]
    F --> G([38 列 Excel<br/>两行/对 · 先 F 后 R<br/>含截图与评价栏])

    style D fill:#123044,stroke:#3FB98A,color:#5EEAD4
    style G fill:#1B2E4A,stroke:#7DD3FC,color:#F8FAFC
```

## 输出长什么样

<!-- ⚠️ 待补：把真实产物截图放进来。这是转化率第二高的位置。 -->
<!-- <div align="center"><img src="assets/output-excel.png" width="88%"></div>
<p align="center"><sub>38 列主表 · 每对两行（先 F 后 R）· 共用字段纵向合并 · 内嵌 PP5 截图</sub></p> -->

主表包含：候选 ID、F/R 序列、原始坐标、产物长度、ORF 覆盖率（bp 与 %）、长度/GC/Tm/配对温差、**PP5 原生评分**、发夹/自二聚体/交叉二聚体、**实际 ΔG**、3′ 端标记、False Priming 全模板复核状态、Primer-BLAST 状态与链接、**用户评价**与备注栏。附方法页记录软件版本、计算条件、检索日期与全部未完成项。

## 快速开始

需要 **macOS + CrossOver + 你自己的 Primer Premier 5 归档（`.cxarchive`）**。本仓库不包含 PP5 或 CrossOver。详见 [本地运行说明](references/local-runtime.md)。

```sh
# 1. 装到 agent 的技能目录
git clone https://github.com/Didnotchangename/primer-premier-design-skill.git \
  ~/.codex/skills/primer-premier-design

# 2. 先跑一条真实序列（强烈建议先单条验证）
python3 ~/.codex/skills/primer-premier-design/scripts/pp5_complete.py \
  --fasta /abs/path/input.fasta \
  --organism 'Homo sapiens (taxid:9606)' \
  --reference NM_000594.4 \
  --archive '/abs/path/Primer Premier 5.cxarchive' \
  --workdir  /abs/path/work/pp5 \
  --output   /abs/path/outputs/result
```

```sh
# 3. 确认格式和筛选方式后，在新会话里让 agent 接手
> 用 primer-premier-design 处理 /abs/path/batch.fasta，物种是 ...
```

> 上面的序列只是参数示例（人 TNF）。**必须换成你自己的输入、物种和已核实的转录本号**；没有可靠 accession 就省掉 `--reference`。

## 默认筛选条件

这套默认值是关键——它们不是拍脑袋定的，是使用者逐条确认过的实验习惯。

| 项目 | 默认值 |
| --- | --- |
| PCR 模板 | cDNA（要 gDNA 须重新评估内含子与基因组产物长度） |
| 产物长度 | 200–750 bp，必须与目标 ORF 重叠 |
| 引物长度 | 优选 18–25 nt |
| GC 含量 | 40–60% |
| Tm | 56–65 °C，优选 ≈60 °C |
| 配对温差 | ≤ 2 °C |
| False Priming | F/R **均须为 None**，且在完整输入模板上复核 |
| 结构 | 弱 Dimer / Cross Dimer 允许复评，列实际 ΔG 由人判断 |
| 候选数量 | 每条序列 1 对首选 + 最多 2 对备用，不为凑数放宽 |

任务里明确指定的参数**优先于**默认值；改过本地搜索参数必须回读验收。

## 目录

| 路径 | 用途 |
| --- | --- |
| [SKILL.md](SKILL.md) | 完整工作规范、筛选边界与交付契约 |
| [scripts/pp5_complete.py](scripts/pp5_complete.py) | ORF → PP5 → 覆盖复核 → Primer-BLAST 入口 |
| [scripts/pp5_design.py](scripts/pp5_design.py) | macOS 本地 PP5 执行器 |
| [scripts/pp5_driver.py](scripts/pp5_driver.py) | bottle 内 Win32 控制与原生数据提取 |
| [scripts/ncbi_services.py](scripts/ncbi_services.py) | NCBI 适配器与结果解析 |
| [references/excel-delivery.md](references/excel-delivery.md) | 38 列布局、合并、截图与公式验收 |
| [references/automation-progress.md](references/automation-progress.md) | 自动化约束、故障处理与验收 |
| [references/local-runtime.md](references/local-runtime.md) | 运行环境与版本约束 |
| [references/result-mapping-evidence.json](references/result-mapping-evidence.json) | PP5 原生字段映射证据 |
| [runtime/python-win32/](runtime/python-win32/) | 随附 Windows Python 3.8.10 32 位嵌入式运行时（bottle 内 Win32 控制用，遵循 PSF 许可） |
| [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md) | 第三方组件许可说明（PP5 / CrossOver / PSF Python / NCBI） |

## 已知边界

诚实地说清楚，比事后被踩坑骂一遍好：

- 执行器绑定**特定 PP5 版本**（校验程序 SHA256），历史验证不保证在别的机器直接可用。
- ORFfinder / Primer-BLAST 的网页适配会随 NCBI 改版失效，需要更新。
- 自动推荐采用**保守**门槛（F/R False Priming 原生计数均 0）。结构待复评的候选会被标出来交给人判断，不做自动放行。
- 特异性结论**只**对实际检查过的物种、数据库和参数成立；默认不额外做基因组 BLAST。
- 所有结果都是计算预测，**需要实验验证**。

## Roadmap

- [ ] `--no-pp5` 无软件模式（Primer3 后端），让没装 PP5 的人也能跑通全流程
- [ ] 批量任务并发调度与断点续跑
- [ ] 产物截图自动拼接对比图
- [ ] Web UI（扔 FASTA 进去看结果）
- [ ] 英文版 SKILL.md

有想要的先说一声，issue 里开口就行。

## 许可

原创内容采用 **MIT**。第三方组件（随附的 Windows Python 运行时、PP5、CrossOver、NCBI 服务）遵循各自许可，**PP5 与 CrossOver 不随本仓库分发**。详见 [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md)。

## 致谢

如果你也在用 PP5 做引物设计，欢迎说说你的默认参数和踩过的坑——这些比代码更难得。

---

<div align="center"><sub>如果这个技能帮你省了一个通宵，点个 ⭐ 让下一个做引物的人也能找到它。</sub></div>

<br>

<a id="english"></a>

# English

A local agent skill that drives the **real Primer Premier 5 (PP5)** desktop application through CrossOver to design PCR primers — then verifies every pair independently and delivers a traceable Excel report.

**Not another Primer3 wrapper.** PP5's native candidates, native ΔG, native structure warnings, and real UI screenshots are preserved. Each pair is submitted to Primer-BLAST separately. Missing values stay missing — nothing is fabricated.

### Install

```sh
git clone https://github.com/Didnotchangename/primer-premier-design-skill.git \
  ~/.codex/skills/primer-premier-design
```

Requires **macOS + CrossOver + your own PP5 `.cxarchive`** (not bundled). See [local runtime](references/local-runtime.md). Works with any agent that reads `SKILL.md` (Codex, Claude Code, Cursor, …).

### Pipeline

`FASTA` → input validation → ORF (NCBI ORFfinder) → native PP5 design in an isolated bottle → independent re-verification (reverse complement, coordinates, ORF coverage, full-template False Priming) → per-pair Primer-BLAST → 38-column Excel with embedded screenshots.

### Default criteria

cDNA template · amplicon 200–750 bp overlapping the target ORF · primer 18–25 nt · GC 40–60% · Tm 56–65 °C (≈60 °C preferred) · pair ΔTm ≤ 2 °C · False Priming **None** for both primers on the full template · 1 primary + up to 2 backup pairs. Explicit task requirements override these.

### License

Original content is **MIT**. Bundled third-party components keep their own licenses; see [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md). PP5 and CrossOver are not distributed here.

> Contribution notes and detailed behavior live in [SKILL.md](SKILL.md). The skill's internal specification is currently written in Chinese.
