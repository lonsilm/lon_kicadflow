# Lon KiCadFlow

面向 AI 协作的 KiCad 工程工作流技能，调用名为 **`$lon-kicadflow`**。

覆盖从创建工程、原理图与库，到 PCB 规则、布局审查、制造导出和跨机器交接的常见任务。默认使用文件、KiCad CLI 与官方 API，不依赖 computer-use 或固定安装盘符。

**原理图默认要求详细中文逐器件注释。** 几乎每个实际器件都需在图内讲清具体功能、真实网络、关键参数和正常/默认状态；重复器件可明确分组，但必须逐位号可追溯，不以“滤波”“保护”等笼统词语代替解释。

**复杂工程默认采用分层模块化原理图。** 根页表达系统能量流和控制闭环，子页按输入保护、功率级、控制核心、采样保护、调试通信和测试验收等功能划分；每页写明“输入→处理→输出→验证”，并从根页完成页间接口、网表和 ERC 验收。

## 安装

```sh
git clone https://github.com/lonsilm/lon_kicadflow.git
```

将仓库中的 **`lon-kicadflow/` 文件夹**复制到 Codex 的技能目录：

- 默认：`~/.codex/skills/lon-kicadflow/`
- Windows：`%USERPROFILE%\.codex\skills\lon-kicadflow\`
- 自定义 `CODEX_HOME`：该目录下的 `skills/lon-kicadflow/`

入口应为 `.../skills/lon-kicadflow/SKILL.md`。刷新技能列表或重启客户端后即可调用。其它支持 SKILL.md 的 AI 客户端可按各自机制安装。

详细步骤见 [安装与迁移](lon-kicadflow/INSTALL.md)。

## 调用示例

```text
$lon-kicadflow 从零创建一个四层控制板工程，先确认供电和接口，再绘制原理图。

$lon-kicadflow 只审查当前PCB的电源、地回流和启动下载，输出HTML，不修改PCB。

$lon-kicadflow 查本机KiCad切换过孔尺寸的快捷键，只回答操作方法。

$lon-kicadflow 全面完善原理图中文注释，逐器件解释具体用途、连接和默认状态；不改电气设计，附注释覆盖清单。

$lon-kicadflow 将一张平面电源原理图重构为根页和 6 个功能子页，每页写输入、处理、输出和验证方法，核对页间接口与根网表。

$lon-kicadflow 从当前保存PCB导出Gerber和钻孔，打包制造ZIP，不修改PCB。
```

## 内容

- [技能入口与任务路由](lon-kicadflow/SKILL.md)
- [环境探测、CLI、Python与IPC](lon-kicadflow/references/environment-and-ipc.md)
- [创建工程与原理图](lon-kicadflow/references/projects-and-schematics.md)
- [分层模块化原理图：页划分、接口与验证](lon-kicadflow/references/hierarchical-schematics.md)
- [逐器件详细中文注释：写法、示例与覆盖验收](lon-kicadflow/references/schematic-annotations.md)
- [符号、封装、测试结构与3D模型](lon-kicadflow/references/libraries-and-3d.md)
- [实际PCB创建与编辑方法](lon-kicadflow/references/pcb-editing.md)
- [规则、布局与布线](lon-kicadflow/references/rules-and-layout.md)
- [供电、启动、去耦与模拟域审查](lon-kicadflow/references/electrical-review.md)
- [ERC/DRC、几何、连通性与验收](lon-kicadflow/references/validation-and-review.md)
- [Gerber、钻孔、装配资料与下单](lon-kicadflow/references/manufacturing.md)
- [本机快捷键查询](lon-kicadflow/references/hotkeys.md)
- [排错、备份与交接](lon-kicadflow/references/troubleshooting-and-handoff.md)

## 辅助脚本

Python 3.10+；主辅助器仅依赖标准库：

```sh
python lon-kicadflow/scripts/kicad_ops.py --help
python lon-kicadflow/scripts/kicad_ops.py probe
python lon-kicadflow/scripts/test_helpers.py
```

`kicad_ops.py` 包含环境探测、源文件哈希、板层和元件库存、网表差异、快捷键查询、网表/ERC/DRC导出、新建空工程和制造打包。可选 `capture_pcb.py` 使用匹配版本的 pcbnew 读取原生几何和连接图。

## 验证与边界

在 Windows、KiCad 10.0.6、Python 3.12 环境实测了新建工程、六项辅助器测试、原生几何读取、ERC/DRC以及六层Gerber和钻孔打包；同时验证了压缩包解压后运行。Linux、macOS及其它KiCad版本需先探测本机能力。

技能遵守用户任务与工程内的 `AGENTS.md`：只读审查不保存PCB；“只改原理图”“只加元件”“只改模型”分别验证。它不是通用自动布线器、完整原理图同步器或电磁仿真工具，制造文件导出成功也不代表电路功能已经验证。

本仓库仅包含可复用技能、文档和脚本。
