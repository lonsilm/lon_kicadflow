---
name: lon-kicadflow
description: 使用文件、KiCad CLI与官方API完成KiCad建项、原理图设计与详细中文逐器件注释、符号封装和3D模型、布线规则、PCB电气及布局审查、Gerber制造导出和快捷键查询。适用于AI协作绘制或检查KiCad工程及跨电脑迁移，按实际版本探测工具，不依赖固定安装路径。
---

# KiCad工程全流程

以实际工程文件、当前工具能力和器件原厂资料为依据完成用户当前任务。使用中文沟通；先给结论、再给必要证据。详细流程按下表读取，不必为一次快捷键查询加载所有参考文档。

## 首先确定任务与边界

1. 读取适用的 `AGENTS.md` 和最近有效约束。确定工程根目录、根原理图、PCB，以及当前任务是查询、审查、源文件修改还是板上修改。旧交接文档里的“当前”“已完成”只作线索，重新核对源文件。
2. **本用户偏好：不使用computer-use。** 优先文件、CLI、官方IPC；查询快捷键无需控制界面。工具缺少接口时，先尝试离线源文件、项目库、只读解析等合理方案；说明实质限制，不声称完成了仅由用户操作才能完成的步骤。
3. 遵守工程写入限制。**“只修改原理图”“只改模型”“只添加电容”“PCB只读”是不同范围。** 不自动F8、不恢复历史PCB、不把一次例外当长期授权。新项目已授权的正常设计工作可以在范围内继续，不重复索要批准。
4. 只读任务立即继续，不因锁文件就要求关闭编辑器。写入前若有证据显示内存可能覆盖磁盘修改，协调保存/重载；不删除锁、强杀进程或用保存后恢复规避只读限制。等待时继续不依赖保存状态的分析。
5. 记录版本、根文件哈希和来源（磁盘/实时IPC/派生副本）。报告区分“设计源已改”“PCB已同步”“仅做建议”。

## 详细中文原理图注释（默认要求）

**绘制、增加器件或完善原理图时，必须先读 [逐器件中文注释规范](references/schematic-annotations.md)，将可见注释作为原理图成果的一部分。**

- 注释的解释性内容全部使用中文。位号、真实网名、引脚名、型号、数值和单位保留准确标识，并用中文解释含义；不为中文化改动电气身份。
- 新绘制或全面完善的图，目标为全部实际器件均有可唯一对应的说明。几乎每个器件都要讲清具体功能、连接到哪里、为什么需要、关键参数/正常或默认状态；适用时写明装配、调试和失效影响。禁止仅写“电阻”“滤波”“保护”“按手册”等含糊短语。
- 相同用途的重复器件可有明确位号清单的分组注释，仍需逐器件可追溯；不同电源域、输入/输出侧、默认状态或用途不能混写。芯片须解释所用功能块与关键电源、复位、时钟和接口，不能只写“主控芯片”。
- 说明必须在原理图内可见，不能只留在隐藏属性、BOM、报告或聊天里。保持文字可读且不遮挡连线；附逐位号覆盖清单并人工核对内容准确性，不以“附近有文字”判定合格。
- 已有工程的局部任务在授权范围内补齐相关器件注释，列出其余缺漏；查询或只读审查不擅自改整张图。未知功能/选值依据明确标注待核实，不能编造。

## 按任务读取

| 当前任务 | 参考文档 |
|---|---|
| 换电脑、找CLI/Python/库、IPC连接或坐标异常 | [环境与工具](references/environment-and-ipc.md) |
| 从零建项、分层原理图、加减元件、网表/BOM | [建项与原理图](references/projects-and-schematics.md) |
| 根页/子页、模块划分、页间接口和学习型验证顺序 | [分层模块化原理图](references/hierarchical-schematics.md) |
| 绘图时的必读规范：详细中文逐器件说明、默认状态与覆盖验收 | [逐器件中文注释](references/schematic-annotations.md) |
| 符号/封装、自制测试点、安装孔、跳线、连接器、3D | [库、封装和模型](references/libraries-and-3d.md) |
| 线宽过孔、板厂工艺、PCB布局/布线、BTB重排 | [规则与布局](references/rules-and-layout.md) |
| 实际建板、放封装、创建铜线/过孔、同步与保存范围 | [PCB编辑方法](references/pcb-editing.md) |
| 电源、启动下载、模拟域、去耦、器件适配 | [电气审查](references/electrical-review.md) |
| ERC/DRC、网表与PCB一致性、参考地、审查报告 | [检查与验收](references/validation-and-review.md) |
| Gerber/钻孔/钢网/BOM/坐标、打板交付 | [制造与交付](references/manufacturing.md) |
| 快捷键、切换过孔、菜单位置、版本差异 | [快捷键查询](references/hotkeys.md) |
| 故障恢复、备份、清理、跨AI交接 | [排错和交接](references/troubleshooting-and-handoff.md) |
| 迁移和安装本技能、调用示例 | [安装与迁移](INSTALL.md) |

## 脚本入口

脚本位于本skill的 `scripts/`，**不在用户工程根目录**。将 `<SKILL>` 替换为本skill实际目录；将 `python` 换成探测到的Python 3.10+。路径有空格时使用参数数组或正确的shell引号。

```text
python <SKILL>/scripts/kicad_ops.py --help
python <SKILL>/scripts/kicad_ops.py probe --cli <kicad-cli路径>
python <SKILL>/scripts/kicad_ops.py snapshot <工程目录> --out <新的before.json>
python <SKILL>/scripts/kicad_ops.py inspect-board <board.kicad_pcb> --out <新的board.json>
python <SKILL>/scripts/kicad_ops.py check <工程目录> --cli <CLI> --output <新的检查目录> --parity
python <SKILL>/scripts/kicad_ops.py netdiff <before.net> <after.net> --out <新的delta.json>
python <SKILL>/scripts/kicad_ops.py compare <before.json> --out <新的source_delta.json>
python <SKILL>/scripts/kicad_ops.py hotkeys viaSize --file <当前版本user.hotkeys>
python <SKILL>/scripts/kicad_ops.py export-fab <board.kicad_pcb> --cli <CLI> --output <新的制造目录> --include-paste
python <SKILL>/scripts/kicad_ops.py new-project <不存在的新目录> --layers 4 --cli <CLI>
<匹配KiCad的Python> <SKILL>/scripts/capture_pcb.py <PCB> --output <新的geometry.json> --connectivity
```

- `probe`先查显式 `--cli`、`KICAD_CLI` 和PATH，再查常见安装目录。便携版位置可显式传入；不扫描整个磁盘。
- 现有工程只读；脚本不调用保存、升级或重铺铜。`new-project`仅创建新目录，使用KiCad 8最小源格式，由已安装KiCad≥8解析验证。
- `check`导出根网表/ERC/DRC；根页不唯一时指定 `--schematic`、`--board`。`--parity`要求根原理图与PCB同目录同名。报告有违规与执行失败是两件事。
- `netdiff`、`compare`：返回码0表示无差异，2表示有差异，1表示失败。其它命令0仅表示执行成功，**不表示电路或DRC通过**。
- 报告与输出目录拒绝覆盖；重跑用新目录。不从截图重建本可从源文件取得的数据。
- `snapshot`是源文件哈希清单，**不是备份**；不涵盖固件、数据手册和所有3D资产。完整迁移须另行收集依赖。
- `capture_pcb.py`为可选原生几何/填铜/连通性采集，依赖匹配的pcbnew；不保存、不重铺铜。不能代替DRC、回流分析或阻抗验证。

## 共用执行流程

### 查询或审查

只读取得当前事实→按问题读取原厂资料/版本帮助→给具体对象、网络、位置和优先级→说明局限。不要为一个快捷键或一个供电问题重新全板审查。

### 修改设计源

取得当前基线/备份→明确变化集合→修改授权文件并补齐对应中文注释→原生解析/根网表/ERC→逐端点、器件属性及注释覆盖比较→验证保护对象→交付。只改原理图时不自动同步PCB；用户已改变焊盘时优先核对真实封装，不用旧BOM改回去。

### 新建或重构模块化原理图

复杂控制板和电源板先按 [分层模块化原理图](references/hierarchical-schematics.md) 划分根页与子页。根页表达系统能量流和控制闭环；子页分别承载输入保护、功率级、控制核心、采样保护、调试通信和测试验收等功能。每个子页必须可见地写出“输入→处理→输出→验证”，并用稳定网名、层次端口和明确电源域表达页间接口。根网表、ERC、BOM和导出视图从根页验收，不能用独立子页通过替代整项通过。

### 修改PCB

仅在当前任务和工程规则允许时执行。先保存可恢复基线并保护既有铜线；按真实脚号网络与几何验证。修改后校验网络、间距、孔、连通性和源/板一致性，不能把库变更当作板上已更新。

### 制造导出

读取保存PCB→实际铜层与板框→同一原点导出Gerber和钻孔→核对层序/文件结束标记/ZIP→前后哈希→提供ZIP和下单参数。不在导出时悄悄修板或重铺铜。

## 必须保留的判断原则

- **默认、预设、板级最小值、对象实际值和有效规则不同。** 设置5mil不会把旧线变成5mil，也不代表过孔间必能穿线。
- **DRC无错误不等于可工作；运行成功不等于DRC零违规。** 供电稳定、栅极驱动、启动、回流和散热需电气证据。
- **网表而非BOM证明连接。** 比较 `(位号,脚号)→网络`，不比较会重排的网络编号；NC、GND、悬空不能互换。
- **有限寻路失败不能证明物理不可布通。** 披露清铜、门户、网格和预算；保留原铜与允许重布的方案不能直接比排名。
- **标称电容不等于有效容量。** 精确MPN、偏压、温度、容差、回路位置共同决定作用。用户说“加”就不替换原件。
- **模拟电源滤波不等于必须切割地平面。** 连续参考地和受控回流通常优先；不同供电电压的性能条件查具体手册。
- **3D外观不是焊盘编号依据。** 模型、库封装、板上实例分别校验；不为匹配模型镜像脚号。
- 不将本项目的工艺门槛、MCU电压、BGA几何、安装路径或快捷键写死成所有新工程的参数。

## 交付

完成成果后简洁说明改了什么、怎么验证和影响使用的剩余限制。审查优先自包含HTML（用户偏好），附机器可读证据，不只给图片。可做则继续；确有写入禁令时指出精确来源、范围和待授权动作，不凭推测引入批准流程。
