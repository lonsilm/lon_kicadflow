# 安装、迁移和调用

本文件用于用户要求的跨电脑携带，不是当前TC377工程的操作记录。skill不包含PCB/手册/固件/第三方模型，也不内置该工程电压和脚号。

## 安装到Codex

将完整 `lon-kicadflow/` 文件夹复制到目标机器的skill目录：

- 通常为 `~/.codex/skills/lon-kicadflow/`。
- Windows通常为 `%USERPROFILE%\.codex\skills\lon-kicadflow\`。
- 若设置了 `CODEX_HOME`，使用该目录下的 `skills/lon-kicadflow/`。

确保入口直接是 `.../skills/lon-kicadflow/SKILL.md`，不要多套一层同名文件夹。已经存在同名技能时先比较/备份，不无提示覆盖个人修改。按客户端支持方式刷新技能列表或重启客户端；当前会话未自动发现时可先让AI读取该文件绝对路径。

其它AI客户端若支持SKILL.md目录，可按其机制安装；否则让AI先读入口并按路由读取references。工具可用性由客户端决定，不能仅复制skill就获得KiCad安装或IPC权限。

## 运行依赖

- Python 3.10+：辅助脚本仅标准库，不强制第三方pip包。
- KiCad CLI：按目标版本安装；建项辅助器要求KiCad≥8。
- 精确PCB几何：可选匹配版本的pcbnew；实时PCB：可选官方kipy与支持的API服务器。
- 可选几何/HTML/PDF工具仅在对应任务需要时使用；skill本身不强制安装。

无需原电脑的B盘/D盘路径。用 `probe` 探测；便携安装可指定CLI：

```text
python <本技能目录>/scripts/kicad_ops.py probe --cli <本机CLI绝对路径>
```

## 调用示例

```text
$lon-kicadflow 从零创建一个四层STM32传感器板工程，先梳理供电和接口，再绘制原理图。

$lon-kicadflow 只审查这个PCB，不要修改文件；优先检查电源回路、地回流和启动下载，输出HTML。

$lon-kicadflow 只在原理图新增去耦，原有电容不动，也不要同步PCB；先给网络和选料依据。

$lon-kicadflow 根据这个精确连接器型号制作本地封装和3D模型，核实脚号和机械尺寸。

$lon-kicadflow 查本机KiCad的过孔尺寸切换快捷键，只回答操作方法。

$lon-kicadflow 从当前保存的PCB导出全部Gerber和钻孔，打包嘉立创ZIP，不改PCB。

$lon-kicadflow 迁移这个工程到另一台电脑，查绝对库路径和缺失模型，保留现有布线。
```

默认允许正常自动发现，不要求每次必须手动调用。显式 `$lon-kicadflow` 最便于选择它。对于每次任务，工程自身的AGENTS和用户最新约束仍需读取；本skill不撤销PCB只读，也不把某工程的只读规则套到所有新项目。

## 脚本与能力边界

`kicad_ops.py --help`列出环境探测、哈希、库存、网表比较、快捷键查询、检查、导出和建项。脚本不能自动完成任意原理图布局、交互路由或3D碰撞分析；AI需结合参考文档、源文件和可用官方接口执行并验证。没有未经说明的全自动布线/功能保证。

新建项目是空白骨架，无板框导致初始DRC报板框缺失正常；不是完整电路。制造导出按已保存铜填充，未经重铺铜；由用户或获授权的设计步骤维护正确保存状态。

此包主要在Windows/KiCad10/Python3.12实测；脚本不硬编码平台盘符，提供跨平台探测，但未在所有Linux/macOS/KiCad版本实机验收，迁移后先运行probe和小工程检查。
