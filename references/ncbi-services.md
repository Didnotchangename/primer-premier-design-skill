# NCBI接口与完整流程

## 三种接口不要混淆

- **BLAST Common URL API** 是官方公开接口：[文档](https://blast.ncbi.nlm.nih.gov/doc/blast-help/urlapi.html)。`Blast.cgi` 用 `CMD=Put` 提交、RID查询、`CMD=Get`取结果。它做序列相似性搜索，不能仅凭两条引物各有命中就宣称配对特异性。需要考虑方向、间距、3′错配和F/F、R/R潜在扩增。不能把BLAST接口说成Primer-BLAST API。
- **Primer-BLAST** 本次用其网页表单 `primertool.cgi` 提交既有PP5引物，并按返回的完整`ctg_time + job_key` URL取状态。未发现官方同等级公开API文档；这是版本可能改变的网页适配器。只检查PP5已给定的F/R，不让远端重新设计替换。解析真实结果的`PRIMER_RESULTS_INFO`，核对实际表格引物序列和产物长度；不能扫描隐藏的通用警告文本来判断通过。限定当前物种RefSeq mRNA，配对分别报告。
- **ORFfinder** 官网页面调用 `projects/orffinder/ORFfinderBE.cgi`，已实测返回JSON及六框ORF坐标/蛋白/边界标记。它是网站内部CGI，未发现同等级稳定公开API文档。官方提供[Linux命令行程序](https://ftp.ncbi.nlm.nih.gov/genomes/TOOLS/ORFfinder/)及[参数说明](https://ftp.ncbi.nlm.nih.gov/genomes/TOOLS/ORFfinder/USAGE.txt)。网页`startcdn=1`表示ATG-only；CLI对应`-s 0`，不要混用。网页`minlen=25`表示最少25aa/75nt；CLI`-ml 75`直接用nt。

当前入口在macOS调用远端CGI并保留官方后端原始JSON；未验证Linux ORFfinder本地二进制。响应速度取决于远端服务和排队状态，不保证完成时间。

## 默认入口

`scripts/pp5_complete.py` 为完整流程入口；`pp5_design.py`仅是底层PP5设计器，不等于完整生物学流程。

```sh
python3 ~/.codex/skills/primer-premier-design/scripts/pp5_complete.py \
  --fasta /absolute/path/input.fasta \
  --organism 'Homo sapiens (taxid:9606)' \
  --reference NM_000594.4 \
  --archive '/absolute/path/Primer Premier 5.cxarchive' \
  --workdir /absolute/path/work/pp5 \
  --output /absolute/path/outputs/result
```

**命令中的物种和转录本只是TNF测试例子，绝不能套用到新序列。** 物种缺失时先问清，同时可继续ORF及本地设计。`--reference`仅用于已核实的目标转录本；无可靠accession时省略，提交原始序列，若NCBI要求选择目标，标为需确认，不自动允许所有命中。

入口只取FASTA第一条，符合先样例再批量要求。批准批量后按记录循环调用，每条独立目录并核对全部ID，不能遗漏输入后续记录。支持`--genetic-code`及`--orf-id`；若目标ORF已获注释确认，按其坐标和方向采用，不盲从最长ORF。默认最长ORF是初选依据，预测身份及边界标记必须保留。

执行顺序：NCBI ORFfinder及可靠CDS注释 → 在完整原始输入模板进行原生PP5三轮 → F/R坐标、结构及False Priming原生集合计数复核 → 只保留与目标ORF有交集且F/R False Priming计数均0的候选，优先ORF覆盖率 → 首选及每对备选分别做Primer-BLAST → 完成状态与原始报告。负链完整模板反向互补后，产物坐标映射回原始输入。不能用局部ORF窗口的False Priming计数代替完整模板检查，也不能用Primer-BLAST通过替代该项。

ORF较短时产物上限为`min(750,窗口长度)`，仍满足原始200–750bp约束。不要把750写入702nt的PP5模板，否则原生参数校验会弹窗。

输出`progress.json`、ORF原始JSON、native参数回读和候选、每对独立请求/状态URL/HTML及结论。网络轮询30秒一次，默认最多等待600秒；运行中或待确认不算通过。再次运行相同命令使用同目录恢复已完成的本地阶段及同一网络任务，不重新提交。`computational_checks_complete`只表示本次计算检查完成，不代表实验验证，也不保证全数据库/基因组/所有物种特异。

## 独立复核要求

- 软件演示序列或公开参考转录本仅用于技术验证，不能据此宣称用户的新输入已完成设计或特异性检查。
- 即使参考转录本相似，也需比较实际输入的碱基、CDS坐标及ORF边界；不能把演示序列直接等同于参考转录本。
- 按原始输入坐标计算扩增子与目标ORF的交集；零覆盖候选不推荐，部分覆盖不能写成完整CDS克隆。
- PP5 Tm与NCBI Tm分别保留实际数值和模型说明，不能相互覆盖；5′/3′partial等边界标记不能省略。
- Primer-BLAST结论只适用于本次物种、数据库、参数和实际检查的配对。不为凑数量添加不满足条件的备用。
- 输入序列、逐对请求、状态URL、原始HTML和研究结果留在本地任务目录，不作为可分发技能的示例或验证日志。
