# PP5 自动化技术约束与验收

本文件保留可复用的接口、故障处理和验收要求，不记录个人研究对象、批次结果或工作目录。文件名为兼容现有引用而保留。历史本地验证不等于新机器或新输入已通过验收。

## 完整流程与推荐边界

- 完整入口为 `scripts/pp5_complete.py`：ORF 分析 → 完整输入模板上的 PP5 原生设计 → 坐标与 ORF 覆盖复核 → 逐对 Primer-BLAST。`pp5_design.py` 只完成本地阶段。
- 局部 ORF 窗口的 False Priming 检查不能代表完整模板。扩增子必须与目标 ORF 重叠；ORF 覆盖为零的候选不推荐。
- False Priming 集合必须已初始化，F/R 计数必须已知且均为零，才可进入自动推荐；未知、空指针和非零计数均不放行。计数零仅适用于该轮实际输入模板，不代替全转录组特异性检查。
- 当前脚本的自动推荐同时要求 Hairpin、Self Dimer 和 Cross Dimer 原生计数为零。按 SKILL.md 展示待用户评价的结构候选时，保留实际 ΔG、3′标记、完整结构、False Priming 和特异性状态，不将人工选用写成计算或实验通过。
- 参数默认 cDNA、GC 40–60%、Tm 56–65°C、配对温差 ≤2°C、产物 200–750 bp、引物优选 18–25 nt。原生长度参数为 nominal±tolerance；三轮为 20±2、24±1、22±4，第三轮是内部超集，最终按交付长度过滤。每轮最多读取 100 对，不能声称穷举最优。
- 追加长度搜索须回读验证，且不能违背任务的硬范围。既往本地环境中名义长度 26 曾出现参数回读清零，原因未确认；不得忽略回读失败。无结果搜索若超时，记录超时，不能写成已证明无候选。
- 完整入口默认只取第一条 FASTA。样例确认后的批量任务需逐条独立记录和核对；不要用旧批次统计代替新输入验收。

## 独立副本与进程生命周期

- 仅从用户提供的 PP5 CrossOver 归档恢复专用 bottle，不覆盖或操作用户原安装。隔离副本需有 `codex-isolated-test.marker`；使用前检查 PP5 程序 SHA256。
- 相同工作目录用文件锁避免并行启动；启动前 inventory 必须拒绝已存在的隔离 PP5 实例。
- PP5 的 `pref.tbl` 会保存 PID；Wine 重启后的 PID 复用可能导致 Only one copy 提示。仅在执行器自己的隔离副本中，每条启动前恢复归档的原始 `pref.tbl`，不能清理用户真实数据或改程序绕过实例保护。
- CrossOver 会让 GUI 共享控制台管道句柄。控制程序若使用 capture_output/communicate 等待 EOF，可能假性卡住；Win32 助手继承控制台，stdin=DEVNULL，原生 JSON 以助手正常退出后写完的文件为准。
- 保持启动 PP5 的 Mac 控制进程存活，直到读取和截图完成；finally 中调用已验证的 close。父进程过早结束可能留下无法由新 Win32 助手枚举的孤立 Mac 外观窗口。
- 若需处理孤立窗口，结合 lsof 工作目录和隔离标记确认所属 PID，仅关闭本次独立副本；绝不按进程名称全局关闭软件。

## 控件、搜索完成与模态窗口

- 多选文件 ListBox 使用 LB_SETSEL，并以 LB_GETSEL 回读确认；LB_SETCURSEL 不足以完成多选导入。
- XVT 窗口可能先于控件和 PWR 对象出现。等待实际菜单、控件、vtable 和全部参数回读一致，再操作。
- 使用 SendMessageTimeout 避免无限同步等待；完整枚举本进程的模态窗口。未知弹窗停止，不盲目继续。
- SearchProgress+0xf4 WORD 用于原生完成判断。状态字符串可能经多层指针或位于映像数据段；有界跟踪，按自身 NUL 终止，不扫描相邻字符串误判完成。
- 搜索可能提示 `More than 30000 possible primers. Optimal primer search will be exceedingly time consuming.`。只有在参数已核对的 run 阶段才允许这个确切警告，并点击唯一启用的 `&Search`；其它模态仍停止。保留 `native_search_warnings`，不能把警告或中断当成无候选。
- 连续同因失败按 SKILL.md 保存进度并停止该项。恢复时只处理缺失步骤，先核对软件、模板和已有状态，不能初始化覆盖已完成记录。

## 版本绑定的原生接口

PP5 EXE SHA256 为 `024eea91d0e65f068784f93760fa27eb7d4ab69f642404c26049ad0d3112e4c8`，不符拒绝。下面地址和偏移只适用于此版本。写入限于隔离副本的配置表和当前 DNA 文档的 8 字节产物范围，操作前核对隔离标记、对象布局和完整模板；不改机器码。字段证据见 [result-mapping-evidence.json](result-mapping-evidence.json)。

- MENU 120 导入，546 Primer Design，541 Search，542 Search Results；Search Criteria/Progress 用 Return 进入下一状态。不能把自绘按钮的内部 ID 当作 WM_COMMAND。
- Search Criteria 窗口 PWR+0xf0 为参数副本；doc+0x8c。mode+0xc；nominal+0x18；tolerance+0x1c；Tm+0x30/+0x34；GC+0x38/+0x3c。
- `srchcrit.tbl` 长度 130，头 888800008250；mode 文件偏移 0xe，nominal 0x16，tolerance 0x1a，Tm 0x42/0x46，GC 0x4a/0x4e。doc+0x68/+0x6c 为产物范围。
- SearchResults vtable 0x54a388；window+0x100 为 grid，vtable 0x54a5f8；grid+0xec 为 doc，vtable 0x548bb8。
- doc+0x48 为完整模板指针，+0x4c 为长度；doc+0x70 为 pair 集合，集合+4 为 count，+0xc 为指针数组。
- pair+4 为 F，+8 为 R，+0x10 为原生配对 Rating，+0x14 为 Cross Dimer 集合。primer+8 为模板左端 0-based 位置，+0xc 为序列指针，指针前 4 字节为长度，+0x24 为 GC，+0x2c 为 Tm。R 已为订购方向 5′→3′。
- primer+0x18 为 Hairpin，+0x1c 为 Self Dimer，+0x20 为 False Priming 集合；集合+4 为条数。必须结合已初始化状态和真实界面验收，不能将空指针当零。
- 原生结构节点 +4 为 float ΔG（kcal/mol），+0x28 为 3′标记，+0x14/+0x18 为两行结构文本，+0x1c 为连线文本。保留完整文本及原始值；`@` 是内部连线标记，不自行解释为错配。
- Criteria 构造器 0x411640，参数回读 0x415100；Results 构造器 0x4d67e0，pair 行回调 0x4db3e0；单引物结构显示 0x474680，相关报告 0x478640；Cross Dimer 报告 0x47d120，结构显示 0x47c010。
- 输出为原始输入上的 1-based inclusive 坐标，start=F.pos+1，end=R.pos+R.length。独立核对 F 与模板、R 与反向互补、GC、长度和产物；负链还需映射回原始输入，不能仅相信界面显示。

## 逐对真实 PP5 截图

- 每对交付引物均需真实 PP5 完整结果子窗口截图。先核对该行 F/R 序列，再拍摄实际候选；首选、备用和待复评候选均须附图。
- Search Results 的 ScrollBar 使用 SB_CTL 回读范围；向父窗口发送 WM_VSCROLL/SB_THUMBPOSITION，顶部行取 min(目标 0-based 行, 当前最大值)。历史显示配置的范围为 0..95，行点击点为客户区 x65、y141+30×(目标行−顶部行)，仅供现场校准参考，不能跨显示配置盲用。
- 选择实际最稳定结构后截图。历史配置的按钮客户区参考：R Dimer (170,375)、Cross Dimer (300,346)、F Hairpin (105,346)；必须现场核对控件和状态。
- 用 GetWindowRect 读取子窗口边界；通过 CG 窗口列表及 lsof 工作目录确认隔离副本 PID，再以 `screencapture -x -o -l` 捕获父窗口，按坐标差裁出完整子窗口，保留全部警告。历史子窗口为 641×422 像素，不能作为固定尺寸。
- Wine GetWindowDC 跨进程 BitBlt 在既往本地环境中失败，不假称已有可用截图路径。
- 图旁列明候选 ID 和 F/R。逐张核对身份、坐标、产物长度、Tm、False Priming、最稳定结构和 ΔG；OCR 漏读时目视核对，不将缺失当通过。
- 按候选身份核对导出 XLSX 内嵌 PNG 的数量和字节哈希；保全已有单元格、公式、评价和截图对应关系。列布局和公式验收以 [excel-delivery.md](excel-delivery.md) 为准，不能照搬历史列位置。

## 验收范围与数据保密

新环境首次使用需实际验证导入、参数回读、搜索完成、原生结果、全模板 False Priming、坐标复核、截图和正常关闭。软件安装存在、PP5 评分或某次历史运行成功，均不能代替本次完整验收。

未获取的盐、Mg、dNTP、引物浓度和热力学阈值应明确标未知。原生结构计数只反映实际计算条件的提示；未注释模板的真实 ORF、实验性能和全数据库特异性不能由计数代替。当前原生结果由只读结构化提取取得，不冒充软件数据库另存或打印。

真实输入、批次清单、候选、截图、NCBI 请求/任务状态和研究结果保存在本地任务目录，不写入可分发的技能资源。发布包只保留通用方法、接口约束和不含私人研究信息的技术说明。
