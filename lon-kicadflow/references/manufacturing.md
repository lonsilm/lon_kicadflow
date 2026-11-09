# Gerber、钻孔、装配资料与下单

## 输入与范围

从用户指定的**当前保存PCB**导出，不从旧备份或旧报告生成。确认根文件时间/哈希、实际铜层数、板厚、板框和导出原点。若用户正在改但未保存，说明导出范围；不自动保存、同步原理图或修板。

读取板内层表，按F.Cu→In1.Cu→…→B.Cu排列，不根据工程名、历史“四层”文字或固定层ID猜。板厚字段并不保证板厂实际叠层；需要阻抗控制时单独选择并核实制造叠层。

制造导出不是电气验收；已有最新审查且源未变时不为了导出再跑一整套审查。用户已选择试板时继续完成打包。

## 使用辅助脚本

```text
python <SKILL>/scripts/kicad_ops.py export-fab <当前PCB> --cli <CLI> --output <不存在的制造目录> --include-paste
```

脚本：

- 从源文件探测全部铜层。
- 导出铜、正反阻焊、正反丝印、板框；`--include-paste`才附正反锡膏层。
- 默认X2层功能属性，使用原点一致的绝对坐标；不镜像底层。
- 若本机支持，丝印减去阻焊开窗，避免不必要压焊盘。
- 导出Excellon mm、显式小数、PTH与NPTH分开；空钻孔文件不装入ZIP（生成目录里保留）。
- 不 `--check-zones`、不重铺铜、不改源文件；核对Gerber铜层功能/层序、单位和结束标记、钻孔头、ZIP CRC与源PCB哈希。
- 输出ZIP、完整原始文件和 `EXPORT_VALIDATION.json`；拒绝覆盖旧目录。

脚本不是完整Gerber几何/DFM查看器，未验证板框闭合、所有孔与铜的精确叠加、过期铜填充、阻抗或订单费用。需要这些检查时按相应流程补，而不是把脚本成功当作完整审核。

## 手工CLI等价操作

先看本机帮助；下例铜层数按实际替换：

```text
kicad-cli pcb export gerbers --output <新目录>/Gerber --layers F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,F.SilkS,B.SilkS,Edge.Cuts --subtract-soldermask <PCB>
kicad-cli pcb export drill --output <新目录>/Gerber --format excellon --drill-origin absolute --excellon-units mm --excellon-zeros-format decimal --excellon-separate-th <PCB>
```

使用辅助原点时Gerber `--use-drill-file-origin` 与钻孔 `--drill-origin plot` 成对使用；不能Gerber绝对原点、钻孔辅助原点。底层不手工镜像；钻孔 `--excellon-mirror-y` 通常不应开启。

注意危险/范围变化参数：

- DRC `--save-board`、`--refill-zones`，Gerber `--check-zones` 会改变或重新计算几何状态，不在普通只读导出中使用。
- `--board-plot-params`可能引入旧的绘图选项/层集合，不验证就照用可能漏层。
- `--common-layers Edge.Cuts`把板框叠加到每层，通常不需要；单独输出板框即可。
- 输出只包括制造所需层，通常不打包Dwgs、Fab、Courtyard、页框标题作为铜图。

## 文件映射和验收

常用Protel扩展名（具体以X2功能属性为准）：

| 文件 | 含义 |
|---|---|
| `.gtl` / `.gbl` | 顶/底铜 |
| `.g1`、`.g2`… | 内层铜，顺序核X2 `Copper,Ln` |
| `.gts` / `.gbs` | 顶/底阻焊 |
| `.gto` / `.gbo` | 顶/底丝印 |
| `.gtp` / `.gbp` | 顶/底锡膏，钢网用途 |
| `.gm1`等 | 板框，以 `Profile` 属性确认 |
| `PTH.drl` / `NPTH.drl` | 金属化/非金属化钻孔 |
| `.gbrjob` | Gerber作业元数据，不是额外铜层 |

确认至少：所有铜层、正反阻焊、所需丝印、唯一正确板框、有孔则有相应钻孔。文件非零不代表有有效几何；空NPTH和无背面丝印可以合理为空。核Gerber `MOMM/MOIN`、`M02`结束，钻孔 `M48/M30`、工具表、坐标；槽和盲埋孔需额外检查相应钻孔对/铣槽指令。

制造ZIP只放必要文件，平铺稳定名称，不混入不同版本、不打包整个工程、旧ZIP、报告图片或设计源码。ZIP CRC和manifest的文件哈希对齐。若捕获到源文件变化，导出作废并重新基于最新保存源生成，不恢复旧板。

有可用Gerber原生查看/解析工具时，复核板框尺寸、孔和铜定位、各层存在、文字镜像和阻焊开窗。不能仅以渲染画面漂亮证明电气正确。不使用computer-use去操作查看器；可用CLI/文件工具，或交付由用户在下单预览中核对。

## BOM、坐标与钢网

裸板下单通常只需Gerber+钻孔；SMT贴装另需BOM、坐标和工艺要求，不能把未核料的BOM直接称为可下单。

- 坐标使用实际PCB实例、确定原点、单位和正反面；旋转约定与贴片厂不同，连接器/二极管/IC1脚尤其核实。
- BOM与PCB位号双向对照，DNP/测试铜点/螺钉孔/手工锡桥分清，精确MPN/供应编号不臆造。
- 钢网只用正确Paste开口，不用Mask代替；裸露焊盘分窗、过孔吸锡和特殊封装按装配要求。
- 导出命令按 `pcb export pos --help`、`sch export bom --help` 的本机能力确认。原理图BOM和PCB装配实例可能不同，给出差异。

## 下单参数

告诉用户实际层数、板厚、板框尺寸（来自可靠轮廓/作业元数据）、必要工艺选择和精确ZIP路径。铜厚、表面处理、阻焊色、阻抗、孔处理等未知项明确待选，不擅自当成已确定。

板内自定义叠层不等于板厂标准叠层；Gerber传了六层，订单不能选四层。PCB开孔/铜到板边与1oz规则不适用于所有订单。

导出授权不等于提交订单、付款或向外发送设计；没有用户相应请求就交付可上传包即可。当前任务是直接导出时不添加不必要的批准步骤。
