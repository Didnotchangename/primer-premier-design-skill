# Primer Premier 5 Primer Design Skill / 引物设计技能

[中文](#中文) · [English](#english)

## 中文

供 Local Agent 使用的中文技能，围绕真实 Primer Premier 5（PP5）组织 PCR 引物设计、ORF 分析、特异性检查和 Excel 报告交付。

默认使用 cDNA 模板，先完成一条真实序列的样例，确认格式和筛选方式后再批量处理。完整规范见 [SKILL.md](SKILL.md)。

## 工作流程

1. 核对输入序列，使用可靠 CDS 注释或 NCBI ORFfinder 确定目标 ORF。
2. 在隔离的 CrossOver bottle 中运行真实 PP5，保留参数回读和原生候选记录。
3. 复核 F/R 序列、原始坐标、产物长度、ORF 覆盖和完整模板上的 False Priming。
4. 对首选、备选逐对提交 Primer-BLAST，记录物种、数据库、请求和结果状态。
5. 按技能规范交付每对两行、先 F 后 R 的 Excel，并附真实 PP5 截图和用户评价栏。

**脚本入口完成计算流程和证据记录；带截图的 Excel 仍需由执行技能的代理按交付规范另行制作、检查。**

## 默认筛选条件

| 项目 | 默认值 |
| --- | --- |
| PCR 模板 | cDNA |
| 产物长度 | 200–750 bp |
| 引物长度 | 优选 18–25 nt |
| GC 含量 | 40–60% |
| Tm | 56–65°C，优选约 60°C |
| 配对温差 | ≤2°C |
| False Priming | F/R 均须为 None，并在完整输入模板上复核 |
| 候选数量 | 每条序列 1 对首选，条件允许时最多 2 对备用 |

扩增子必须与目标 ORF 重叠，优先提高覆盖率。结构提示和实际 ΔG 应保留供逐对评价；不擅自用统一 ΔG 阈值放行或淘汰。当前脚本的自动推荐采用保守筛选，结构待复评候选的展示和用户评价按 SKILL.md 执行。任务明确指定的参数优先于默认值，改变本地搜索参数后须重新回读验收。

## 依赖与安装

本地自动化针对 **macOS + CrossOver + Primer Premier 5**。需要自行准备可用的 PP5 CrossOver 归档（`.cxarchive`）；本仓库不包含 PP5 或 CrossOver 软件。

- macOS 上的 Python 3，用于运行主入口。
- 已安装的 CrossOver，以及与执行器匹配的 PP5 归档。执行器检查 PP5 程序 SHA256，具体版本约束见 [本地运行说明](references/local-runtime.md)。
- 可访问 NCBI 的网络。完整流程会将模板序列和引物提交到 NCBI，仅在序列允许上传时使用。
- `runtime/python-win32/` 内附 Windows Python 3.8.10 32 位嵌入式运行环境，供 bottle 内的 Win32 控制使用。

将整个仓库安装到 Codex 的技能目录，保留目录结构：

```sh
mkdir -p ~/.codex/skills
git clone https://github.com/Didnotchangename/primer-premier-design.git \
  ~/.codex/skills/primer-premier-design
```

在新的 Codex 会话中调用 `primer-premier-design`，提供 FASTA、目标物种和本机 PP5 归档位置。技能要求先检查本会话实际具备的操作能力；软件存在不代表自动化已通过验证。

## 命令行入口

以下以人类 TNF 参考转录本作参数示例。**必须替换为实际输入、物种、已核实的转录本和本机路径**；没有可靠转录本 accession 时省略 `--reference`。

```sh
python3 ~/.codex/skills/primer-premier-design/scripts/pp5_complete.py \
  --fasta /absolute/path/input.fasta \
  --organism 'Homo sapiens (taxid:9606)' \
  --reference NM_000594.4 \
  --archive '/absolute/path/Primer Premier 5.cxarchive' \
  --workdir /absolute/path/work/pp5 \
  --output /absolute/path/outputs/result
```

完整入口默认只处理 FASTA 第一条记录。样例确认后，批量任务需逐条使用独立输出目录执行并核对全部 ID。不要同时让多个执行器使用同一个工作目录。

输出包含 `progress.json`、ORF 原始结果、PP5 参数与候选证据，以及逐对特异性请求、状态和报告。恢复运行应沿用对应目录，先检查已有进度，避免重复提交网络任务。参数、状态含义和恢复边界见 [NCBI 接口与完整流程](references/ncbi-services.md)。

## 文件说明

| 文件 | 用途 |
| --- | --- |
| [SKILL.md](SKILL.md) | 完整工作规范、筛选边界和交付要求 |
| [scripts/pp5_complete.py](scripts/pp5_complete.py) | ORF → PP5 → 覆盖复核 → Primer-BLAST 完整计算入口 |
| [scripts/pp5_design.py](scripts/pp5_design.py) | macOS 本地 PP5 执行器 |
| [scripts/pp5_driver.py](scripts/pp5_driver.py) | bottle 内 Win32 控制与原生数据提取 |
| [scripts/ncbi_services.py](scripts/ncbi_services.py) | NCBI 网页接口适配与结果解析 |
| [references/excel-delivery.md](references/excel-delivery.md) | 38 列 Excel、合并、图片和公式验收规范 |
| [references/automation-progress.md](references/automation-progress.md) | 通用自动化约束、故障处理和验收要求 |
| [references/result-mapping-evidence.json](references/result-mapping-evidence.json) | PP5 原生字段映射证据 |
| [runtime/python-win32/LICENSE.txt](runtime/python-win32/LICENSE.txt) | 随附 Python 运行环境的许可说明 |

## 使用边界

当前执行器依赖特定 PP5 版本及本地环境，历史运行记录不能保证其他机器直接可用。命令中的 `/absolute/path/` 是占位路径，需按本机配置替换。真实输入、批次清单、候选、截图、任务状态和研究结果应留在本地任务目录，不写入可分发技能。

ORFfinder 与 Primer-BLAST 的网页适配可能随 NCBI 网站变化。待返回、未检查、失败和通过必须分别记录；Primer-BLAST 的结论限于实际检查的物种、数据库和参数，默认不额外做基因组 BLAST。所有结果均为计算预测，需实验验证。

本仓库尚未为原创技能内容指定开源许可证；公开可见不等于授予任意使用或再分发许可。第三方运行环境遵循其随附许可。


## English

A local Agent skill for PCR primer design using the real **Primer Premier 5 (PP5)** application. It connects ORF analysis, native PP5 candidate generation, specificity checks, and Excel delivery requirements. See [SKILL.md](SKILL.md) for the full instructions.

The default PCR template is cDNA. Process one real sequence as a sample, confirm the report format and screening approach, then proceed with batch work.

### Workflow

1. Validate the input and select a target ORF using reliable CDS annotations or NCBI ORFfinder.
2. Run PP5 in a dedicated CrossOver bottle, retaining parameter readbacks and native candidate evidence.
3. Independently verify primer sequences, original-template coordinates, amplicon length, ORF coverage, and False Priming on the full input template.
4. Check each primary and backup pair separately with Primer-BLAST, retaining the organism, database, request, and result status.
5. Prepare the Excel report with two rows per pair, forward before reverse, real PP5 screenshots, and user evaluation fields.

**The scripts produce computational results and evidence. The agent running the skill must separately build and verify the Excel report and its screenshots according to the delivery specification.**

### Default criteria

| Item | Default |
| --- | --- |
| PCR template | cDNA |
| Amplicon length | 200–750 bp |
| Primer length | Preferably 18–25 nt |
| GC content | 40–60% |
| Tm | 56–65°C, preferably around 60°C |
| Pair Tm difference | ≤2°C |
| False Priming | None for both primers, verified on the full input template |
| Pairs per sequence | One primary pair and up to two backups, when suitable |

Amplicons must overlap the target ORF; higher coverage is preferred. Preserve native structure warnings and actual ΔG values for individual review rather than applying an invented universal threshold. The current automatic selection is conservative; report candidates requiring structure review and user decisions as specified in SKILL.md. Explicit task requirements override defaults. Changes to native search parameters require readback and renewed validation.

### Requirements and installation

Local automation targets **macOS + CrossOver + Primer Premier 5**. Supply your own working PP5 CrossOver archive (`.cxarchive`). PP5 and CrossOver are not included.

- Python 3 on macOS for the main entry point.
- CrossOver and a PP5 archive matching the executable SHA256 enforced by the driver. See [local runtime details](references/local-runtime.md).
- Network access to NCBI. The full workflow submits template sequences and primers to NCBI; use it only when external submission is authorized.
- The bundled Windows Python 3.8.10 32-bit embeddable runtime in `runtime/python-win32/` is used for Win32 control inside the bottle.

Install the entire repository in your Codex skills directory, preserving its structure:

```sh
mkdir -p ~/.codex/skills
git clone https://github.com/Didnotchangename/primer-premier-design.git \
  ~/.codex/skills/primer-premier-design
```

In a new Codex session, invoke `primer-premier-design` and provide the FASTA input, target organism, and local PP5 archive path. The agent must first verify that the current session can operate the software; an installed application alone does not establish working automation.

### Command-line entry point

This example uses human TNF solely to illustrate the arguments. **Replace the input, organism, verified transcript accession, and local paths for your task.** Omit `--reference` when no reliable transcript accession is available.

```sh
python3 ~/.codex/skills/primer-premier-design/scripts/pp5_complete.py \
  --fasta /absolute/path/input.fasta \
  --organism 'Homo sapiens (taxid:9606)' \
  --reference NM_000594.4 \
  --archive '/absolute/path/Primer Premier 5.cxarchive' \
  --workdir /absolute/path/work/pp5 \
  --output /absolute/path/outputs/result
```

The full entry point processes only the first FASTA record. After sample approval, run batch records separately with distinct output directories and reconcile every input ID. Do not run multiple drivers against the same working directory concurrently.

Outputs include `progress.json`, original ORF results, PP5 parameter and candidate evidence, and per-pair specificity requests, statuses, and reports. Inspect existing progress before resuming with the corresponding directories to avoid duplicate submissions. See [NCBI services and workflow](references/ncbi-services.md) for parameter, status, and recovery details.

### Repository contents

| Path | Purpose |
| --- | --- |
| [SKILL.md](SKILL.md) | Full workflow, screening rules, and delivery requirements |
| [scripts/pp5_complete.py](scripts/pp5_complete.py) | ORF → PP5 → coverage verification → Primer-BLAST entry point |
| [scripts/pp5_design.py](scripts/pp5_design.py) | macOS PP5 runner |
| [scripts/pp5_driver.py](scripts/pp5_driver.py) | Win32 control and native data extraction inside the bottle |
| [scripts/ncbi_services.py](scripts/ncbi_services.py) | NCBI web adapters and result parsing |
| [references/excel-delivery.md](references/excel-delivery.md) | 38-column Excel layout, merging, screenshots, and formula verification |
| [references/automation-progress.md](references/automation-progress.md) | Reusable automation constraints, troubleshooting, and validation requirements |
| [references/result-mapping-evidence.json](references/result-mapping-evidence.json) | Evidence for native PP5 field mappings |
| [runtime/python-win32/LICENSE.txt](runtime/python-win32/LICENSE.txt) | Bundled Python runtime license notices |

### Limitations

The driver depends on a specific PP5 build and local environment. Historical validation does not guarantee that it will run unchanged on another machine. The `/absolute/path/` values in commands are placeholders to replace for your machine. Keep real inputs, batch lists, candidates, screenshots, job states, and research results in local task directories rather than in distributable skill resources.

ORFfinder and Primer-BLAST web adapters may require updates when NCBI changes its website. Keep pending, unchecked, failed, and passed states distinct. Specificity conclusions apply only to the actual organism, database, and parameters checked; genome BLAST is not added by default. All results are computational predictions and require experimental validation.

No open-source license has been assigned to the original skill content. Public visibility does not itself grant unrestricted use or redistribution rights. Third-party runtime components remain subject to their accompanying licenses.
