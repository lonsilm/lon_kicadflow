# 环境、版本、CLI与官方IPC

## 环境探测

先取得工程路径、OS、CLI版本、文件格式版本、Python与资源目录。多版本并存时，编辑器、CLI、库和Python扩展应匹配。不为迁就工具升级工程。

```text
python <SKILL>/scripts/kicad_ops.py probe
python <SKILL>/scripts/kicad_ops.py probe --cli <自定义路径>/kicad-cli.exe --out <新的probe.json>
kicad-cli version
kicad-cli sch export netlist --help
kicad-cli sch erc --help
kicad-cli pcb drc --help
kicad-cli pcb export gerbers --help
kicad-cli pcb export drill --help
```

版本帮助优先于别的版本示例。网表格式名通常为 `kicadxml`，默认可能为S表达式；使用XML比较时显式指定。

| 资源 | Windows候选 | Linux/macOS候选 |
|---|---|---|
| CLI | 安装目录 `bin/kicad-cli.exe` | PATH；macOS应用包内 |
| 配置 | `%APPDATA%/kicad/<版本>/` | `$XDG_CONFIG_HOME/kicad/<版本>/` 或 `~/.config/kicad/`；macOS `~/Library/Preferences/kicad/` |
| 库 | 安装目录 `share/kicad/` | `/usr/share/kicad/`；macOS应用包或共享资源目录 |
| 项目库表 | 工程 `sym-lib-table`、`fp-lib-table` | 同左 |

这些仅为候选，便携包/Flatpak/分发版可能不同。读取实际 `KICAD_CONFIG_HOME`、`KICAD*_SYMBOL_DIR`、`KICAD*_FOOTPRINT_DIR`、`KICAD*_3DMODEL_DIR` 和 `kicad_common.json`，不要直接替换版本号假定目录存在。

`kicad_ops.py`只依赖Python标准库。缺工具时先利用文件完成能做的事；不要为一个模块导入失败重装用户Python或批量改PATH。

## 工具选择

| 任务 | 优先工具 | 边界 |
|---|---|---|
| 网表、ERC/DRC、制造输出 | CLI | 读取磁盘，不知道未保存状态 |
| 项目规则 | `.kicad_pro` JSON / `.kicad_dru` | 依据本机schema；编辑器可能覆盖离线修改 |
| 原理图、库 | 结构化S表达式编辑＋原生验证 | 不用简单正则重写嵌套结构 |
| 打开的PCB状态 | 官方kipy IPC | 公开能力随版本变化 |
| 保存PCB精确几何 | 匹配版本pcbnew只读载入 | 不SaveBoard/Save/Fill |
| 快捷键 | 当前user.hotkeys＋版本文档 | 不需要控制窗口 |

旧HQ插件、第三方服务或MCP可能没安装在另一台电脑。先发现工具；不自造协议或私发protobuf绕过接口。

## Python与绑定

`import pcbnew`失败先查解释器、位数和KiCad版本。Windows可探测CLI旁 `python.exe`；Linux常用系统绑定；macOS按发行包查找。

```python
import sys, importlib.util
print(sys.executable)
print(importlib.util.find_spec('pcbnew'))
print(importlib.util.find_spec('kipy'))
```

不混用不同版本的DLL目录或把不兼容二进制装进默认Python。纯文件检查无需pcbnew。

## 官方IPC只读采集

启用API服务器属于配置变更，不因想检查文件就默认修改。有可用连接时：

```python
from kipy import KiCad
kicad = KiCad(timeout_ms=20000)
kicad.check_version()
board = kicad.get_board()
```

通过已安装公开类、`inspect.signature()`、docstring和官方API文档确认能力，不假设所有版本都有原理图编辑、写网类、路由或保存接口。

项目中实际遇到的采集问题：

1. 批量 `get_pads()/get_footprints()`可能缓存旧位置；公开 `get_items_by_id`可按批重读，核对ID、中心与精确多边形。接口不存在就报告局限，不伪造刷新。
2. padstack可能返回背面焊盘的前层模板形状；按真实层集合过滤，不能只看 `copper_shapes.layer`。
3. 某些几何API返回板级绝对坐标，**不要再次镜像/旋转/叠加偏移**。本地坐标和绝对坐标明确标识，用非对称焊盘验证。
4. 多次IPC调用不是原子快照。记录开始/结束；用户同时移动对象时重采，不能用混合状态判断精确间距。
5. 不用“先修改再撤销”测试写接口完成只读任务；序列化丢失padstack/单位等问题在隔离副本验证，不直接试存用户板。

## 原生只读解析

示意，先检查本机签名：

```python
from pathlib import Path
import hashlib, pcbnew
path = Path('board.kicad_pcb')
before = hashlib.sha256(path.read_bytes()).hexdigest()
board = pcbnew.LoadBoard(str(path))
for footprint in board.GetFootprints():
    print(footprint.GetReference(), footprint.GetFPIDAsString())
    for pad in footprint.Pads():
        print(pad.GetNumber(), pad.GetNetname(), pad.GetPosition())
assert hashlib.sha256(path.read_bytes()).hexdigest() == before
# 不保存、升级或重铺铜。
```

内部长度常为nm（1mm=1,000,000nm），但先查具体接口；文件层ID不等于物理层序，不跨版本硬编码。

## 数据来源和竞争

- CLI仅声明检查保存文件；IPC说明当时内存状态，不保证已保存。
- 锁可能有效或残留。只读照常；有写冲突证据再协调，不每次要求关闭工程。
- 哈希变化先查用户编辑/工具写入，作废过期派生结果；**不恢复自己的旧快照覆盖用户工作**。
- 报告写新目录，含来源、时间、哈希、版本和局限；独立副本与当前板分开标识。

官方入口：`https://docs.kicad.org/`、`https://dev-docs.kicad.org/`、`https://docs.kicad.org/kicad-python-main/`。选择本机版本；离线时依据本地帮助和包，不编造已联网查证。
