# 快捷键、菜单与上下文查询

## 只问快捷键时的最短流程

识别KiCad版本、原理图/PCB/3D/库编辑器，以及空闲/正布线/选中对象状态→读取当前版本的 `user.hotkeys` →按内部action ID检索→直接给按键、动作和适用状态。不要为回答“怎么切换过孔”导出全板DRC或控制窗口。

```text
python <SKILL>/scripts/kicad_ops.py probe
python <SKILL>/scripts/kicad_ops.py hotkeys viaSize
python <SKILL>/scripts/kicad_ops.py hotkeys trackWidth routeSingle show3DViewer
python <SKILL>/scripts/kicad_ops.py hotkeys updatePcbFromSchematic --file <当前版本>/user.hotkeys
```

查询词不区分大小写，多个词取OR。辅助脚本把所有匹配文件一起列出，**不能把旧版本配置误认为当前激活版本**；多版本时显式指定文件。

## 配置格式

现代 `user.hotkeys` 常为TSV：`actionID<TAB>主键<TAB>备用键`，如：

```text
pcbnew.EditorControl.viaSizeDec    <当前绑定>
pcbnew.EditorControl.viaSizeInc    <当前绑定>
common.Control.updatePcbFromSchematic    <当前绑定>
common.Control.show3DViewer    <当前绑定>
```

上面为说明，实际列使用制表符，不是空格。action ID可能随版本变化；搜索关键词比只按中文菜单名可靠。空白表示此文件未给定或未分配，不能猜默认生效键；文件也不一定包含所有默认动作。

若本机文件缺失/没有条目：查对应版本官方手册、安装源action定义或用户提供的快捷键导出。只找到常见默认时标注“默认值，未核本机自定义”。不要编造“已核实”。

## 常见动作的查询词

| 用户问法 | action/搜索词 | 必须补充的上下文 |
|---|---|---|
| 开始走线 | routeSingle、router | PCB且有有效起点 |
| 差分走线 | differential、diffPair | 先正确识别差分对/命名与规则 |
| 放过孔/换层 | via、layer | 正在布线时的动作与空闲不同 |
| 上/下一档过孔 | viaSizeDec、viaSizeInc | 预设列表 vs 网类尺寸 |
| 上/下一档线宽 | trackWidthDec、trackWidthInc | 当前预设、自动宽度、网类 |
| 修改尺寸/属性 | properties、edit | 悬停/选中/过滤器 |
| 移动/拖动 | move、drag | 是否保持导线连接，PCB不同工具行为 |
| 翻面/旋转 | flip、rotate | 层/镜像与旋转不同 |
| 更新PCB | updatePcbFromSchematic | 会改PCB，查询不代表允许执行 |
| 铺铜 | fill、zone | 会更新几何；只读任务不执行 |
| 高亮网 | highlightNet | 仅显示，不更改网类或连接 |
| 3D视图 | show3DViewer | 模型缺失与显示隐藏分开 |
| 局部坐标清零 | localCoord、resetLocal | 不等于移动制造原点 |

常见默认如E属性、R旋转、X开始单线、V布线中过孔、Alt+3打开3D等，只作查找线索；**本机配置优先，不能把常见默认当已验证答案**。更新PCB常见F8，但某用户已改为Alt+I，说明不应硬编码。

## 过孔预设的特别说明

同一项目案例中，`\` 曾绑定上一档过孔，`'` 绑定下一档；这是当时用户配置，不是所有机器默认。不要把反斜杠与英文单引号说反。

切换预设通常影响接下来放的过孔；空闲选中已有过孔时某些动作可能调整已有对象。说明用户当前在哪个状态，不自动修改所有孔。

“默认信号0.4/0.3”与“有四档可切换”通过网类和预设设置完成，快捷键只是切换入口。列表里的0/0可代表使用网类尺寸，不是真零尺寸孔；网类尺寸与手选预设优先关系需本版本验证。

## 修改快捷键

用户只问怎么操作时只回答，不改配置。明确要求绑定时，备份当前文件、检查目标action与同上下文冲突、局部写入；不要覆盖整份快捷键。

配置是否能热重载取决于版本，编辑器可能覆盖磁盘更改；有证据才协调关闭/重载。最后报告哪个action绑定成什么、是否已经由当前进程加载。用键名和动作双重描述，避免输入法/键盘布局歧义。

菜单位置按当前版本文档或本地资源查证，使用动作名称优先，语言不同不强行给错误的中文菜单路径。
