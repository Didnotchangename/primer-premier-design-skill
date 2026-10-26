# 本机底层PP5执行器

本文件仅描述本地设计阶段。完整默认任务请先读[ncbi-services.md](ncbi-services.md)并运行pp5_complete.py，不能将下述底层命令的成功当作ORF和特异性已完成。

需由用户提供可用的归档，例如 `/absolute/path/Primer Premier 5.cxarchive`。
CrossOver `/Applications/CrossOver.app/Contents/SharedSupport/CrossOver/bin`。
原安装位于 `~/Library/Application Support/CrossOver/Bottles/Primer Premier 5`，执行器不使用、不覆盖它。

## 执行

```sh
python3 ~/.codex/skills/primer-premier-design/scripts/pp5_design.py \
  --fasta /absolute/path/input.fasta \
  --archive '/absolute/path/Primer Premier 5.cxarchive' \
  --workdir /absolute/path/work/pp5-run \
  --output /absolute/path/outputs/pp5-result
```

默认仅第一条。样例确认后加 `--all`，序列条数不限，顺序运行，每条独立启动和关闭本执行器的 PP5 实例。workdir可复用，但只能使用带隔离标记的专用 bottle；不得同时启动两个运行器使用同一workdir。输出目录每次新建以免覆盖旧审计数据。异常停止后先检查该独立副本是否仍运行；不要以重复启动来处理弹窗。

运行器自动从归档恢复专用 bottle，导入真实模板，设置参数，再从原生对象回读、搜索和只读提取结果。只改隔离副本的 srchcrit.tbl 和当前 DNA 文档的8字节产物上下限；不改 EXE、DLL 或算法。每条保留 request、readback、native、validated 和关闭记录；汇总 progress.json 和 selected.csv。Excel按 SKILL.md 契约生成，不能把CSV改扩展名伪装XLSX。

依赖 Windows Python3.8.10 win32 embeddable 已随 skill 存于 runtime/python-win32；不依赖当前聊天work路径。它只用于 Win32 ctypes，不运行第三方引物算法。主程序SHA256固定为 `024eea91d0e65f068784f93760fa27eb7d4ab69f642404c26049ad0d3112e4c8`，版本不符即拒绝。参考 automation-progress.md 的验收记录与边界。

CrossOver 中 GUI 与控制程序共享控制台句柄，不能对控制程序用 capture_output/communicate 等待管道EOF，否则GUI可能持有管道导致假性卡住；控制程序继承当前控制台，结果以控制程序成功退出后写完的JSON文件为依据。自绘窗口等待控件与有效vtable后才访问，模态弹窗报错退出，不能盲目继续菜单命令。
