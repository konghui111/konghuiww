# konghuiww 项目索引

> 鸣潮 (Wuthering Waves) 游戏自动化项目，基于 ok-script 框架 (Python 3.12)
> 最后更新: 2026-08-29

## 目录

- [1. 项目概览](#1-项目概览)
- [2. 目录结构](#2-目录结构)
- [3. 角色系统](#3-角色系统)
- [4. 任务系统](#4-任务系统)
- [5. GUI 组件](#5-gui-组件)
- [6. 资产文件](#6-资产文件)
- [7. 配置](#7-配置)
- [8. 关键架构](#8-关键架构)
- [9. 参考项目](#9-参考项目)
- [10. 决策与变更历史](#10-决策与变更历史)

---

## 1. 项目概览

- **应用名**: 鸣潮凹分助手
- **入口**: `main.py` → `ok.OK(config).start()`
- **框架**: ok-script (ok 包)，提供截图/OCR/模板匹配/输入模拟
- **打包**: `pyappify.yml` 定义 Windows 打包和 GitHub 更新源
- **参考项目**: ok-wuthering-waves (`E:\ok-wuthering-waves-master\`)，详见 [9. 参考项目](#9-参考项目)
- **已注册角色** (18): qianxiao, yangyang, suisui, feixue, Linnai, Aemeath, Mornye, qingxiao, denia, jianxin, xigelika, verina, shorekeeper, qiuyuan, jinxi, rebecca, Galbrena, Lupa
- **未注册模板**: character.py

---

## 2. 目录结构

```
e:\konghuiww\konghuiww\
├── main.py                    # 入口 (release 模式, 精简 GUI)
├── main_debug.py              # 入口 (debug 模式, 完整 GUI)
├── bench_template_match.py    # 基准工具: 模板匹配耗时
├── bench_full_pipeline.py     # 基准工具: 完整流程耗时
├── API.md                     # ok-script 框架 API 文档
├── PROJECT_INDEX.md           # 本文件
├── pyappify.yml               # PyAppify 打包配置 (name: konghuiww)
├── deploy.txt                 # 发布到更新仓库的文件列表
├── src/
│   ├── config.py              # 应用配置 (窗口捕获, OCR, 热键, 任务注册)
│   ├── globals.py             # Globals 类: on_show_main_window 钩子精简 GUI
│   ├── character/             # 角色战斗脚本 + 共享工具 (按属性分文件夹)
│   │   ├── __init__.py        # 枚举, 注册表, 共享函数, 角色库 (18 角色)
│   │   ├── fg_time_collector.py  # fg_time 自动收集器
│   │   ├── spectro/           # 衍射 (4): jinxi, Linnai, shorekeeper, verina
│   │   ├── electric/          # 导电 (1): rebecca
│   │   ├── fire/              # 热熔 (5): Aemeath, Mornye, denia, Galbrena, Lupa
│   │   ├── ice/               # 冰属性 (2): feixue, suisui
│   │   ├── wind/              # 气动 (4): qingxiao, jianxin, xigelika, qiuyuan
│   │   ├── havoc/             # 湮灭 (2): qianxiao, yangyang
│   │   └── character.py       # 模板角色 (未注册)
│   ├── axis/                  # 轴 JSON 文件 (从 src/character/ 独立出来)
│   │   └── *.json             # 各队伍轴配置
│   ├── tasks/
│   │   ├── CombatBaseTask.py     # 战斗基类 (热键/角色检测/协奏/内存回收, 共享逻辑)
│   │   ├── AxisCombatTask.py     # 打轴战斗任务 (继承 CombatBaseTask, 轴命令/执行/fg_time)
│   │   ├── AutoCombatTask.py     # 自动战斗任务 (继承 CombatBaseTask, 骨架待开发, 默认 F8)
│   │   ├── AxisEditorTask.py     # 轴编辑工具任务 (新建轴/编辑轴/编辑角色)
│   │   ├── CharacterAutoTask.py  # 旧版战斗任务 (已拆分, 保留备份)
│   │   ├── AxisEditor.py         # 轴编辑器 GUI + 数据结构
│   │   ├── CharacterEditor.py    # 角色属性编辑器 GUI (网格布局, 每行6角色)
│   │   ├── MyBaseTask.py         # 自定义基类
│   │   ├── MyOneTimeTask.py      # 示例一次性任务
│   │   ├── MyTriggerTask.py      # 示例触发器任务
│   │   └── ColorPercentageTask.py # 找色工具任务
│   └── ui/
│       ├── CombatTab.py       # 自定义战斗配置 Tab (main 模式唯一可见页面)
│       └── MyTab.py           # 自定义标签页示例
├── assets/
│   ├── coco_annotations.json  # COCO 标注 (特征类别, 基于 2560x1440)
│   └── images/                # 源截图 (0.png~19.png)
├── configs/                   # 运行时配置 (git-ignored)
├── .agents/skills/            # Qwen Code skill 定义
│   └── ok-character-codegen/  # 从文字轴描述生成角色代码的 skill
└── references/
    └── ok-script-resolution.md  # ok-script 分辨率自适应参考文档
```

---

## 3. 角色系统

### 3.1 角色属性

| 文件 | 角色名 | 定位 | 属性 | 优先级 | 共鸣链 | 已注册动作 |
|------|--------|------|------|--------|--------|-----------|
| feixue.py | feixue | MAIN_DPS | ICE | NORMAL | 0 | main, skill_coordination |
| qianxiao.py | qianxiao | SUB_DPS | HAVOC | NORMAL | 0 | ea3, a4, z, qre, super_z2a3, super_a4, skill_coordination |
| suisui.py | suisui | HEALER | ICE | NORMAL | 0 | aaaa, normal_a23, super_a12, a4e, ea4qr, skill_coordination, skill_coordination_z |
| yangyang.py | yangyang | MAIN_DPS | HAVOC | NORMAL | 0 | aaaa, c_a1, c_a12, w_e_c_a2, c_a3e, c_a34, c_e, c_z, y_a12, y_a34, y_z1, y_e, qr, y_z, main, skill_coordination (DUAL_SKILL=True) |
| Linnai.py | Linnai | SUB_DPS | SPECTRO | NORMAL | 0 | skill_coordination |
| Aemeath.py | Aemeath | SUB_DPS | FIRE | NORMAL | 0 | startup, mecha_e, a4_until_buff, loop, skill_coordination |
| Mornye.py | Mornye | SUB_DPS | HAVOC | NORMAL | 0 | skill_coordination |
| qingxiao.py | qingxiao | SUB_DPS | WIND | NORMAL | 0 | a, a12, a123, main, skill_coordination |
| denia.py | denia | SUB_DPS | FIRE | NORMAL | 0 | er1, aafaa, eer2, qr, qrz, a123, z, eqr, r2, skill_coordination |
| jianxin.py | jianxin | MAIN_DPS | — | NORMAL | 0 | skill_coordination |
| xigelika.py | xigelika | MAIN_DPS | SPECTRO | NORMAL | 0 | main, skill_coordination |
| verina.py | verina | SUB_DPS | SPECTRO | NORMAL | 0 | main, skill_coordination |
| shorekeeper.py | shorekeeper | SUB_DPS | SPECTRO | NORMAL | 0 | qr, qrz, a123, z, eqr, skill_coordination |
| qiuyuan.py | qiuyuan | SUB_DPS | WIND | NORMAL | 0 | e, start, main, skill_coordination |
| jinxi.py | jinxi | MAIN_DPS | SPECTRO | NORMAL | 0 | main, skill_coordination (骨架, 待补充连招) |
| rebecca.py | rebecca | MAIN_DPS | ELECTRIC | NORMAL | 0 | main, skill_coordination (骨架, 待补充连招) |

### 3.2 共享函数 (`src/character/__init__.py`)

**枚举**: `CharType`(MAIN_DPS/SUB_DPS/HEALER), `SwitchPriority`(NO~MUST), `Elements`(6种属性)

**注册表**: `ACTION_REGISTRY` → `{角色名: {动作名: {force_clear}}}` (已移除 fg_time/total_time)

**角色库**: `CHARACTER_LIBRARY` → `{角色名: 模块}` (16 个已注册)

**导入约定**: 所有角色文件统一使用 `from src.character import *` 导入共享函数, 新增共享函数无需逐个修改角色文件

**核心函数**:
- `register_action()` — 注册动作 (仅 force_clear 参数)
- `check_skill_available()` — 技能可用性: 传 skill_image 二值化识图; 不传则严格纯白占比判 CD
- `check_skill_available_by_color()` — 纯找色检测
- `check_skill_available_by_size()` — 多尺度识图检测技能可用性 (模板 0.5~1.5 倍每 10% 一档逐档匹配, 任一档命中即可用; 详见 2026-08-22 变更历史)
- `check_skill_available_binary()` — 二值化检测技能可用性 (见下方"二值化找色使用方法")
- `calculate_binary_percentage()` — 区域二值化后计算白色像素占比
- `binarize_image()` — 灰度二值化 (亮度 > threshold 的像素变白)
- `continuous_click()` — 持续点击指定时长
- `continuous_send_key()` — 持续按指定按键指定时长 (continuous_click 的键盘版, 间隔同为 70ms)
- `wait_for_my_turn()` — 阻塞等待唤醒 (threading.Event)
- `freeze_time()` — 时停补偿 (延长所有倒计时)
- `f_execute()` — 处决检测与执行 (屏幕中央区域找图, 见下方"处决检测"说明); 返回 1=成功 (found 或 can_f 任一命中), 0=失败
- `detect_self_on_field()` — 检测当前角色是否在场 (模板匹配角色头像)
- `set_axis_command/result()` — 轴命令通信

#### 二值化找色使用方法

**适用场景**: 检测 UI 元素是否"亮起" (技能图标、共鸣回路、buff 图标等)。只依赖亮度，不依赖特定 RGB 颜色范围，对颜色偏移更鲁棒。

**三层函数** (由低到高):

| 函数 | 输入 | 输出 | 用途 |
|------|------|------|------|
| `binarize_image(image, threshold=244)` | BGR 图像 | 单通道二值图 (0/255) | 底层图像处理 |
| `calculate_binary_percentage(task, box, threshold=244)` | task + Box | 白色占比 0.0~1.0 | 自定义区域/自定义占比阈值 |
| `check_skill_available_binary(task, area, threshold=244, white_threshold=0.02)` | 区域名 (如 "e") | 1=可用 / 0=不可用 | 技能区域检测, 最常用 |

**调用示例**:

```python
# 方式 1: 高层 API — area 拼接成 "e_location" 自动获取区域
from src.character import check_skill_available_binary
if check_skill_available_binary(task, "e", threshold=244, white_threshold=0.02):
    ...  # e 技能可用

# 方式 2: 中层 API — 自定义特征区域 (Mornye.py / Linnai.py 实际用法)
from src.character import get_location_box, calculate_binary_percentage
box = get_location_box(task, "xxx_location")  # 从 _location 特征获取区域
if box and calculate_binary_percentage(task, box, 244) > 0.02:
    ...  # 区域亮起
```

**参数调节**:
- `threshold` (0-255): 二值化亮度阈值, 默认 244 仅保留极亮像素; 噪点多则调高, 目标偏暗则调低
- `white_threshold` / 占比阈值: 先用 ColorPercentageTask 实测"亮起"与"未亮起"的占比, 阈值取在两者之间

**调试/目视确认**: `ColorPercentageTask.py` 顶部改 `LOCATION_FEATURE` 和 `BINARY_THRESHOLD`, 调用 `get_binary_percentage()` 会保存"原图 | 二值化图 | 找色结果图"三联对比截图, 可直观查看二值化效果
- 保存位置: 项目根目录 `screenshots\`, 文件名 `{时分秒.毫秒}_binary_comparison_original.png` (框架 `screenshot()` 按 `screenshots_folder` 配置相对 cwd 解析)

#### 处决检测 (f_execute)

**背景**: 处决 F 提示出现在怪物头顶随怪物移动, 无法固定位置检测; 多波次连续战斗没有"脱离战斗"状态, 无法靠脱战清状态。
**方案** (方案 A, 参考 ok-wuthering-waves `check_f_break`): 角色动作中调用 `f_execute()` 现检测 → 屏幕中央区域找 `f_break` 按键图片 → 找到即一定可处决 → 按 F。每次调用都是新鲜检测, 无陈旧状态问题。
**参数** (`src/character/__init__.py` 模块级常量):
- `F_BREAK_REGION = (0.2, 0.2, 0.75, 0.8)` — 搜索区域比例 (x起点, y起点, x终点, y终点), 待调大
- `F_BREAK_THRESHOLD = 0.8` — 找图阈值
- `F_BREAK_TARGET_HEIGHT = 720` — 降采样匹配 (实测约 11ms)
**特征状态**: `f_break` 特征待用户在框架中标注生成 (曾临时复制参考项目模板, 已按用户要求删除以便从框架重新生成)。特征缺失期间 `f_execute` 记警告并返回 0, 不会崩溃

### 3.3 fg_time 收集器 (`fg_time_collector.py`)

- 在打轴模式中自动测量每个动作的实际前台时间
- 仅保存完整阶段的数据 (动作数 == 预期数)
- 每个动作保留最短的 3 次记录 (`KEEP_COUNT = 3`)
- 持久化到 `fg_time_data.json`
- 提供 `get_avg_fg_time()` 供未来自动模式调度使用

---

## 4. 任务系统

### 4.1 任务架构 (拆分后)

原 `CharacterAutoTask` 已拆分为基类 + 3 个子任务:

```
MyBaseTask
  └── CombatBaseTask (共享基类: 热键/角色检测/协奏检测/内存回收/run主循环)
        ├── AxisCombatTask (打轴战斗, 默认 F7)
        └── AutoCombatTask (自动战斗骨架, 默认 F8)

MyBaseTask
  └── AxisEditorTask (轴编辑工具: 新建轴/编辑轴/编辑角色)
```

#### CombatBaseTask (共享基类)

**功能**: 所有战斗模式共享的逻辑
- 热键注册/监听/F7 启停 (`RegisterHotKey` + `PeekMessageW`)
- 角色检测 + 协奏数据预计算 (`_precompute_con_data`)
- 角色脚本线程管理 (`_start_script_threads` / `_cleanup_script_threads`)
- 战斗状态重置 + 内存回收 (`_reset_combat_state` / `_trim_memory`)
- 协奏值检测 (`is_con_full`: `forte_location` 区域找色 >= 99%)
- 热重载 (`importlib.reload()` 角色脚本)
- WGC 管理 (任务销毁时关闭)
- 子类只需实现 `_execute_combat()` 方法

#### AxisCombatTask (打轴战斗)

**配置**: 启停热键 (默认 F7) + 导入轴
**功能**: 按轴定义的顺序执行动作, 支持 startup/loop/loop2/loop3/finish 阶段
- 轴命令/结果/完成事件机制
- FgTimeCollector 实测前台时间
- 角色匹配验证

#### AutoCombatTask (自动战斗, 骨架)

**配置**: 启停热键 (默认 F8)
**功能**: 后续开发调度逻辑 (优先级/冷却/协奏调度)

#### AxisEditorTask (轴编辑工具)

**配置**: 新建轴 / 编辑轴 / 编辑角色 (三个按钮)
**功能**: 一次性任务, 点击按钮打开对应编辑器, 不需要启停
- 在 CombatTab 中用 `ConfigCard` 渲染 (无 Start/Stop 按钮)

### 4.2 其他任务

| 文件 | 类型 | 功能 |
|------|------|------|
| ColorPercentageTask.py | 一次性 | 找色工具, 检测指定区域颜色占比; `get_binary_percentage()` 输出三联对比截图, `get_binary_image()` 返回二值化图并保存 4 倍放大版; 参数为任务配置, GUI 修改即时生效无需重启 |
| MyOneTimeTask.py | 一次性 | 示例任务, 展示所有配置控件类型 |
| MyTriggerTask.py | 触发器 | 示例触发器任务 |

---

## 5. GUI 组件

### 5.1 CombatTab (自定义战斗配置 Tab)

- **位置**: `src/ui/CombatTab.py`, 通过 `custom_tabs` 注册
- **功能**: 显示三个任务卡片:
  - 打轴战斗 (`TaskCard`, 含 Start/Stop + 导入轴按钮)
  - 自动战斗 (`TaskCard`, 含 Start/Stop 按钮)
  - 轴编辑器 (`ConfigCard`, 只有新建轴/编辑轴/编辑角色按钮, 无 Start/Stop)
- **自动展开**: `setExpand(True)` + `expandButton.hide()`, 无折叠按钮
- **main 模式精简**: `Globals.on_show_main_window()` 在 `debug=False` 时移除所有默认 Tab, 隐藏导航侧边栏和标题栏图标, 只保留 CombatTab
- **debug 模式**: 保留全部框架 GUI, 不触发精简

### 5.2 AxisEditor (轴编辑器)

- **数据结构**: `AxisAction{character_name, action_name}`, `Axis{startup, loop}`
- **GUI**: 角色动作方块 (可拖拽) + 横向时间线 (启动/循环)
- **头像系统**: 从 COCO 标注裁剪角色头像
- **深色主题**: `BG_PRIMARY=#202020`, `BG_CARD=#2D2D2D`, `TEXT_PRIMARY=#FFFFFF`
- **角色选择**: `QGridLayout` 网格布局, 每行 4 个角色卡片, 自动换行 (替代原 QHBoxLayout 单行排列)
- **fg_time 显示**: 动作方块从 `fg_time_data.json` 读取实测数据 (通过 `FgTimeCollector.get_avg_fg_time()`), 显示两位小数 (如 `fg:1.23s`); 替代原从 `ACTION_REGISTRY` 读取 (已移除 fg_time 参数)

### 5.3 CharacterEditor (角色属性编辑器)

- **可编辑属性**: CHAR_TYPE, SWITCH_PRIORITY, ELEMENT, RESONANCE_CHAIN
- **保存方式**: 正则替换 .py 文件中的属性赋值行, 保留注释, `importlib.reload()` 刷新
- **下拉选项全中文**: 主输出/副输出/治疗者, 衍射/导电/热熔/冰属性/气动/湮灭, 0链~6链

---

## 6. 资产文件

### COCO 标注 (33 个特征)

| 类别 | 特征 |
|------|------|
| 角色头像 | character_suisui, character_qianxiao, character_yangyang, character_feixue, character_verina |
| 槽位按键 | character1, character2, character3 |
| 头像搜索区域 | character1_location, character2_location, character3_location |
| 按键搜索区域 | hotkey1_location, hotkey2_location, hotkey3_location |
| 技能区域 | e_location, q_location, r_location, a_location, xiezou_location, f_location |
| 角色特有 | feixue_z, feixue_x, feixue_x_prepare, feixue_r1, feixue_r2, feixue_a_location, feixue_x5_location, feixue_r1_location, suisui_spuer_e, suisui_norm_e, qianxiao_a4, qianxiao_super_e, qianxiao_r |

**命名规则**:
- `character_<name>` — 角色头像模板
- `<name>_location` — 搜索区域 (仅用位置, 不做模板匹配)
- `<character>_<skill>` — 角色特有技能模板

---

## 7. 配置

**src/config.py 关键设置**:
- 窗口捕获: WGC > BitBlt_RenderFull > BitBlt
- 交互方式: Pynput / PostMessage / ForegroundPostMessage 等
- OCR: onnxocr + OpenVINO, 自动繁转简
- 模板匹配: 默认阈值 0.8
- 分辨率: 16:9, 最小 1280x720, 自动缩放到 [2560x1440, 1920x1080, 1600x900, 1280x900, 1280x720]
- 截图处理: `make_bottom_right_black()` 遮挡 UID
- 游戏热键: Echo=q, Liberation=r, Resonance=e, Tool=t
- 自定义 Tab: `'custom_tabs': [["src.ui.CombatTab", "CombatTab"]]`
- 应用名: `'my_app': ['src.globals', 'Globals']`

**pyappify.yml**:
- `name: "konghuiww"` (英文, 避免安装路径含中文导致 PyAppify 报错)
- `uac: true`, `use_pythonw: true`
- 更新源: `https://github.com/konghui111/konghuiww.git`

---

## 8. 关键架构

### 8.1 战斗流程 (打轴模式)

```
F7 启动 → _combat_active = True → 启动战斗线程
  → _detect_characters() 识别队伍
  → _precompute_con_data() 预计算协奏数据
  → 启动所有角色脚本线程 (daemon)
  → 循环执行轴动作:
      set_axis_command → event.set() 唤醒角色 → event.wait() 等待完成
      FgTimeCollector 记录实测 fg_time
  → startup 完成 → 进入 loop (无限循环)
F7 停止 → _combat_active = False → 角色脚本退出 → _reset_combat_state()
```

### 8.2 角色脚本标准结构

```python
import time
from src.character import *  # 统一导入所有共享函数和枚举

CHARACTER_NAME = "xxx"
CHAR_TYPE = CharType.MAIN_DPS
SWITCH_PRIORITY = SwitchPriority.NORMAL
ELEMENT = Elements.ICE
RESONANCE_CHAIN = 0

def _action_xxx(task): ...  # 动作函数, 返回 True/False
register_action(CHARACTER_NAME, "xxx")  # 注册 (紧跟动作函数, 不集中放底部)

def run(task):
    # 找到自己的槽位
    while task.enabled and task._combat_active:
        wait_for_my_turn(task, hotkey, CHARACTER_NAME)  # 阻塞等待
        axis_action = get_axis_command(task, CHARACTER_NAME)
        if axis_action:
            # 执行对应动作
            set_axis_result(task, CHARACTER_NAME, action_success)
        else:
            # 自动模式 (大部分角色暂不支持)
```

#### 标准技能释放模板

释放技能时, 先等待可用再持续按键直到消失, **动作在 `if not` 判定之前**:

```python
while task.enabled and task._combat_active:  # 等待 e 可用
    if check_skill_available(task, "e", skill_image="xxx_e"):
        break
    time.sleep(0.05)
while task.enabled and task._combat_active:  # 持续按 e 直到 e 消失
    task.send_key("e")              # ← 动作在前
    time.sleep(0.05)
    if not check_skill_available(task, "e", skill_image="xxx_e"):  # ← 判定在后
        break
```

### 8.3 角色注册流程

1. 在 `src/character/` 创建 .py 文件
2. 定义常量和动作函数
3. 调用 `register_action()` 注册动作
4. 在 `__init__.py` 中 import 并添加到 `CHARACTER_LIBRARY`
5. 在 COCO 标注中添加角色头像特征

---

## 9. 参考项目

### ok-wuthering-waves (OK-WW) — 重要参考项目

- **路径**: `E:\ok-wuthering-waves-master\`
- **文档索引**: `E:\ok-wuthering-waves-master\PROJECT_INDEX.md` (调研日期 2026-08-20)
- **定位**: 基于同一 ok-script 框架的成熟鸣潮 PC 端自动化项目 (~50 个角色、完整任务体系)，是本项目的主要设计参考来源

**参考对照**:

| OK-WW 模块 | 参考内容 | 本项目对应 |
|------|---------|-----------------|
| 类层次 | BaseWWTask → CombatCheck → BaseCombatTask | MyBaseTask → CharacterAutoTask |
| 战斗检测 | CombatCheck: 锁定框/血条颜色/倒计时 OCR | CharacterAutoTask 战斗状态检测 |
| 协奏值 | OpenCV 环形掩膜 + 连通域分析 | _precompute_con_data()/协奏值检测 |
| 切换调度 | SwitchPriority + buff/协奏/冷却多因子决策 | 自动模式调度器 |
| 角色系统 | BaseChar + CharFactory 注册 (53 角色) | src/character/ 注册表模式 |
| 时停补偿 | add_freeze_duration()/time_elapsed_accounting_for_freeze() | freeze_time() |
| 分辨率自适应 | 相对坐标/box_of_screen_scaled | references/ok-script-resolution.md |
| 更新/打包 | PyAppify + deploy.txt + 依赖内联流程 | pyappify.yml/deploy.txt |

**使用建议**:
- 实现新功能 (战斗检测、复活流程、副本任务等) 前，先查阅其 PROJECT_INDEX 对应模块，再按需看源码
- 其角色实现 (今汐/卡梅利亚/长离/守岸人/安可等) 可作为编写新角色循环逻辑的参照
- 注意: 本项目采用注册表 + 事件驱动打轴模式，与 OK-WW 的类继承 + perform() 模式不同，参考设计思路而非照搬结构

---

## 10. 决策与变更历史

### 2026-08-21 清理 fg_time/total_time

**决策**: 从 `register_action()` 移除 fg_time 和 total_time 参数
**原因**: 打轴模式用事件驱动 (`done_event.wait()`)，不依赖估算值；切换冷却 1s > 后台动作时间，天然同步
**影响**: 8 个角色文件 + CharacterAutoTask + AxisEditor 全部清理
**新增**: `fg_time_collector.py` 在运行时实测 fg_time，保留最短 3 次记录

### 2026-08-21 添加 RESONANCE_CHAIN 属性

**决策**: 所有角色文件添加 `RESONANCE_CHAIN = 0` (0-6)
**原因**: 支持共鸣链等级配置，不同链数可能有不同战斗逻辑

### 2026-08-21 创建角色属性编辑器

**决策**: 新建 `CharacterEditor.py` 独立对话框 (非 CustomTab)
**原因**: 与 AxisEditor 保持一致的交互模式，通过按钮打开
**实现**: 正则替换 .py 文件中的属性行 + `importlib.reload()` 刷新

### 2026-08-21 GUI 深色主题

**决策**: AxisEditor 和 CharacterEditor 统一使用深色主题
**颜色**: `BG_PRIMARY=#202020`, `BG_CARD=#2D2D2D`, `TEXT=#FFFFFF`, `BORDER=#404040`
**来源**: qfluentwidgets 框架的 `QColor(32, 32, 32)` 深色背景

### 2026-08-21 热键按钮持久化

**决策**: 在 config_type 定义时设置默认文字 `"当前: F7"`，run() 执行后更新为实际值
**旧方案 (已废弃)**: 在 __init__ 中读 config → 报错 (config 在 __init__ 时为 None)
**旧方案 (已废弃)**: QTimer 延迟查找按钮 → 无效 (ConfigCard 懒加载，按钮不存在)
**最终方案**: config_type 默认值 + run() 中更新 config_type["text"]

### 2026-08-21 鼠标卡死修复

**决策**: `_reset_combat_state()` 中释放所有鼠标和按键
**原因**: 角色脚本中断时 mouse_down 未配对 mouse_up，导致系统认为鼠标一直按住
**实现**: `mouse_up("left/right")` + `send_key_up("e/r/q/space")`，try/except 包裹

### 2026-08-21 退出延迟修复

**决策**: 添加 `_run_stopped` 标志 + `on_destroy` 唤醒所有线程
**原因**: 脚本线程阻塞在 `event.wait()`，`join(timeout=3)` × 3 = 最多 9 秒
**旧方案 (已废弃)**: `self.sleep(0.02)` → 框架 sleep 可能在任务禁用时卡住
**最终方案**: `time.sleep(0.02)` + `_run_stopped` 标志 + `event.set()` 唤醒
**注意**: 框架本身的退出延迟 (无 CharacterAutoTask 时也有) 不在我们控制范围内

### 2026-08-21 创建 ok-character-codegen skill

**决策**: 新建 skill 用于从文字轴描述生成角色动作代码
**位置**: `.agents/skills/ok-character-codegen/SKILL.md`
**功能**: 解析文字描述 → 生成动作函数 + register_action + run() 分发
**占位符**: 未指定的图片/区域用 `PLACEHOLDER_xxx` + `# TODO:` 标记

### 2026-08-21 分支感知的 fg_time 收集系统

**决策**: fg_time_collector 支持 branch_id，区分同一动作的不同执行路径
**原因**: 像 feixue.main 有处决/非处决、x5 可用/不可用等分支，实际耗时差异大
**实现**:
- `fg_time_collector.py`: `_make_key()` 新增 branch_id 参数，key 格式变为 `角色。动作。分支`
- `__init__.py`: `set_axis_result()` 新增 branch_id 参数，结果存储为 `(success, branch_id)` 元组
- `CharacterAutoTask.py`: 解析元组，传递 branch_id 给 collector
- `feixue.py`: `_action_main` 用 `branch_parts` 列表记录分支，最后统一返回 `True, branch_id`
**数据示例**:
```json
{
  "feixue.main.execute_with_x5": [10.2, 10.5, 10.3],
  "feixue.main.no_execute_no_x5": [13.1, 13.3, 13.0]
}
```
**向后兼容**: branch_id 默认为 "default"，现有角色脚本无需修改

### 2026-08-21 AxisEditor GUI 布局调整

**决策**: 角色动作栏整体一个大边框，动作块放大到 110x70
**变更过程**:
1. 角色动作栏：从每行独立边框 → 整体一个大边框（去掉 slot_widget 边框，保留 char_slots_widget 边框）
2. 动作块尺寸：90x57 → 110x70，头像 34px → 44px，时间字体 11px → 12px
3. 滚动区域：去掉 scroll 边框，设为透明背景
4. 时间线：高度 65/80 → 80/100，图标尺寸匹配动作块

### 2026-08-22 帧缓存陷阱修复 (Mornye 二值化循环卡死旧帧)

**现象**: Mornye.py 二值化等待循环运行时永远不成立, 游戏内能量明明在涨; 调试工具测量却正常
**原因**: `task.frame` 是缓存 (仅 `_frame is None` 时截图); 清缓存只有 `next_frame()`/`task.sleep()`/带 `after_sleep` 的方法; 循环用 `time.sleep` + `calculate_binary_percentage` (只读缓存不截图) → 永远判定 mouse_down 后那一帧旧帧
**修复**: 最终把 `task.next_frame()` 移入 `calculate_binary_percentage()` 内部 (与 check_skill_available 约定一致, 调用方无需自己刷帧, 此类 bug 结构性不可能); `check_skill_available_binary` 和 Mornye 循环里冗余的显式 next_frame 已移除 (避免重复截图)
**通用规则**: 共享检测函数内部自带刷帧; 若直接读 `task.frame` (calculate_color_percentage/box.crop_frame) 则调用方必须自己 `next_frame()`; 注意内部刷帧意味着每次调用截一帧, 需要"同一帧做多检测"时不要混用

### 2026-08-22 鼠标长按状态跟踪 (切换不打断预输入长按)

**决策**: `src/character/__init__.py` 新增 `enable_mouse_tracking()` / `is_mouse_held()`; 实例级包装 task.mouse_down/mouse_up 记录脚本按住状态; `wait_for_my_turn` 切换循环仅在无左键长按时才 click
**原因**: 上个角色可能以预输入长按左键结束动作 (飞雪蓄力), 切换循环的 click (down+up) 会打断长按; 框架交互层不记录按压状态, PostMessage 合成点击也无法用 GetAsyncKeyState 查询, 只能脚本侧记录
**零侵入**: 包装自动覆盖全部调用点 (角色脚本+任务的 mouse_down/up), 无需改调用点; set 操作幂等并发包装无害; `task.click()` 走 interaction.click 不经过包装, 不会误记录; `_reset_combat_state` 的 mouse_up 自动清跟踪
**机制** (已确认): 实例级 override (实例属性优先于类方法) → wait_for_my_turn 是每个动作前必经的第一个函数, 包装必定生效 → `_mouse_tracking` 标记保证只装一次 → `_held_mouse_keys` set 握手 (按下 add/释放 discard) + `is_mouse_held` 查询闭环
**注意**: `_held_mouse_keys` 不在 task 类中预定义, 由 `enable_mouse_tracking()` 在实例上动态创建 (__init__.py:362); `is_mouse_held` 用 getattr 带默认值读取, 包装前调用也安全

### 2026-08-22 check_skill_available 判定路径优化

**最终设计** (经历"改二值化"一轮后按用户洞察再优化):
- 传 `skill_image`: 二值化识图 — 帧区域和模板用同一 `binary_threshold` (默认 244) 二值化后匹配 (`template=` + `frame_processor=` 实现), 去掉白色占比检查
- 不传: 严格纯白 (255,255,255) 占比判 CD (CD 数字严格白色占比 <2%; 可用时图标大部分纯白 >86%)
- 二值化识图实测: feixue_r1 在图标存在帧 1.00、不存在/异状态帧 0.00, 区分度与原始彩色匹配等价; 各模板二值化@244 亮部存活 4~19% (彩色图标), 若识别不稳可下调 binary_threshold
**原因**: CD 数字严格白色, 严格找色区分度最好且与游戏内标定阈值直接对应; 二值化会把 CD 占比抬高 (+0.01~0.04) 使贴线阈值翻转
**实测对比** (源截图, 纯白/二值化): 可用 0.86~1.0 / 0.87~1.0; 中间态 0.06~0.13 / 0.07~0.15
**澄清**:
- 1.png 的 6~15% 并非真实 CD 态; 用户游戏内标定 (CD <2%) 成立
- 二值化看灰度亮度 Y=0.299R+0.587G+0.114B 而非逐通道阈值; RGB(252,228,255) 亮度 238、RGB(170,249,255) 亮度 226, 均 <244 二值化为黑 (测试图中并未变白)
- `check_skill_available_by_color` 不能改二值化: feixue_r1 两状态靠色相区分 (青 vs 粉), 亮度相近, 二值化丢失色相区分力
- `find_one` 默认是彩色模板匹配; 二值化识图通过 `template=` + `frame_processor=` 同阈值二值化实现 (已用于 check_skill_available 的 skill_image 路径)
**设计结论**: 可用 vs CD 是"亮度总量"问题, 严格纯白占比是正确信号; 不给所有技能上模板; 模板只用于亮度区分不了的特殊状态 (feixue_r1/suisui_spuer_e/qianxiao_super_e 等); 区域被杂散亮点污染时优先收紧 _location 框
**文档同步**: API.md find_feature 补 `template` (不自动缩放/不校验特征存在) 与 `frame_processor` (作用于 box 裁剪区域) 语义; ok-character-codegen skill 新增"检测方式选择"小节并更新关键词映射

### 2026-08-22 处决检测改造为中央找图 (方案 A)

**决策**: `f_execute()` 从固定位置找色改为屏幕中央区域找 `f_break` 图片 (`box_of_screen` 比例区域 + `target_height=720` 降采样匹配), 沿用角色动作内调用方式 (方案 A)
**原因**: 处决提示随怪物移动无法固定位置检测; 找色方案可能把没充满的处决条误判为满; 多波次连续战斗无脱战状态, 方案 B 的状态标志会陈旧, 而方案 A 每次现检测无此问题
**资产**: 曾临时复制参考项目 `f_break` 模板 (36x43@4K) 并验证通过 (1440p 下缩放为 24x29, 区域+720p 匹配置信度 0.82); 后按用户要求删除 (源图 4.png + COCO 三条记录), 由用户从框架重新标注生成
**保护**: 特征缺失时 `f_execute` 捕获 ValueError, 记警告返回 0 (避免连招中角色线程崩溃)
**待办**: 用户在框架中标注生成 `f_break` 特征, 按需调大 `F_BREAK_REGION`

### 2026-08-22 ColorPercentageTask 参数改为任务配置 (免重启)

**决策**: 模块级常量 (LOCATION_FEATURE/TARGET_COLOR_RGB/TOLERANCE/BINARY_THRESHOLD) 改为任务配置项 (位置特征/目标颜色RGB/颜色容差/二值化阈值), 方法调用时经 `_get_params()` 实时读取
**原因**: 调试模式下改参数需要重启整个框架, 效率低
**新流程**: 任务设置卡片改参数 → 开发工具 Tab 选截图 → 调用方法, 立即生效
**附加**: `validate_config()` 校验数值在 0-255; 颜色参考值注释保留在文件头部
**后续新增**: `get_binary_image()` 返回指定区域二值化图 (numpy 数组), 并保存 4 倍放大版 (`_binary_view_original.png`, INTER_NEAREST 保持黑白边缘) 便于目视检查小区域

**处决状态设计结论 (参考项目调研)**:
- OK-WW `can_break` 三层清除: 初始化 / 脱离战斗时 (`do_reset_to_false`) / 每次按 F 后 (`f_break` 循环持续执行依赖实时复检)
- 本项目方案: 检测线程周期复检自愈 (怪死提示消失→下轮清标志) + 按 F 后立即清标志; 陈旧时间 ≤ 检测间隔
- 残留风险: 怪死后一个间隔内可能白按一次 F (F 也是拾取键), OK-WW 同样接受此风险

### 2026-08-22 性能基准工具与关键耗时数据

**新增工具**:
- `bench_template_match.py`: 模板匹配耗时对比 (纯 cv2 + ok 框架真实调用对照)
- `bench_full_pipeline.py`: 复现 `check_skill_available()` 完整流程 (截图→找色→找图→返回), 使用框架真实截图类 (WGC/BitBlt), 优先对游戏窗口截图, 游戏未运行时自动选最大应用窗口替代

**实测数据 (2560x1440, 本机)**:
- 模板匹配: 全屏 133ms / 中央区域(0.2,0.2,0.75,0.8) 42ms / 降采样720p 32ms / 区域+720p **10.6ms** (框架调用额外开销仅 ~2-5ms 后处理)
- 完整检测循环: BitBlt 截图 ~17ms + 找色 0.03ms + 找图(小区域) 0.35~0.41ms ≈ **17ms**; 检测循环的实际节奏由截图方式决定
- WGC 特性: 等待新帧送达才返回 (60fps 上限), 静态窗口不送帧; 对静态内容的真实耗时需游戏运行时测量

**框架机制确认 (源码)**:
- `find_one` 默认路径 = 按 box 裁剪 + 可选 target_height 缩放 + 一次 `cv2.matchTemplate` (limit=1 走 minMaxLoc 轻量后处理)
- `next_frame()` 为同步截图, 无后台帧缓存线程
- 特征加载时模板图片本身会 `cv2.resize()` 到当前分辨率 (详见 references/ok-script-resolution.md)

**后续完成**: 处决检测已改造为方案 A (角色动作内现检测, 中央区域找图+720p 降采样), 见 3.2 节"处决检测"; 模板/区域待用户替换与调大

### 2026-08-22 记录二值化找色使用方法

**决策**: 在 3.2 节新增"二值化找色使用方法"小节 (三层函数表 + 调用示例 + 参数调节 + 调试方法)
**原因**: 二值化找色已在 Mornye.py/Linnai.py 中使用, 但索引中无使用文档
**关联**: `binarize_image()` / `calculate_binary_percentage()` / `check_skill_available_binary()` 位于 `src/character/__init__.py`; 调试用 `ColorPercentageTask.get_binary_percentage()` 输出三联对比截图

### 2026-08-22 添加参考项目并清理与记忆重复的内容

**决策 1**: 将 ok-wuthering-waves (`E:\ok-wuthering-waves-master\`) 作为重要参考项目写入索引 (见第 9 节)
**原因**: 同为 ok-script 框架的成熟实现，战斗/角色/任务系统设计可直接参照
**决策 2**: 删除本文件中与记忆文件重复的协作规则内容 (AxisEditor 条目的"教训"行和"用户记忆更新"条目)
**原因**: 协作规则已在 ~/.qwen/memories 中维护 (clarify-before-implement.md、layout-modification-workflow.md 等)，PROJECT_INDEX 只记录项目特有信息

### 2026-08-22 修复 Linnai 协奏值恒不满 (ELEMENT 误配)

**现象**: 跑 `zhenxie.json` 轴时, Mornye 的 `_check_special_skill` 能正确返回, Linnai 的永远返回 False (卡在等协奏满的循环)
**排查**: suisui 特殊 buff 分支无问题——该队伍无 suisui, 分支不激活; 且 Linnai/Mornye 同为 SUB_DPS, 分支即使激活也一视同仁, 无法解释差异
**真因**: `is_con_full` 的 `con_box` 是**全槽位共用的固定屏幕区域** (检测在场角色协奏环, 同 OK-WW 参考实现); 颜色按 `ELEMENT` 查 `CON_COLORS`。Linnai 与 Mornye 都误配成 `Elements.HAVOC`(索引5, 暗粉色), 两人计算逐字节相同 → 差别只在真实环色是否落在索引5范围。Linnai 实际是**衍射**(黄色, 索引0), 环色不在索引5范围 → `pixel_count < min_area` 恒成立 → 恒 False
**证据**: `Linnai.py` 该行注释本就写"衍射"但值是 `HAVOC`, 自相矛盾 (复制模板未改值)
**修复**: `Linnai.py` `ELEMENT` 改为 `Elements.SPECTRO`(索引0)
**遗留隐患 (未改)**: `is_con_full` 判定 `pixel_count >= _con_full_size[...]` 量纲不一致——运行时 `pixel_count` 是原始 `inRange` 计数, 校准值 `_con_full_size` 来自 `_count_rings` 的**闭运算后**面积 (填隙偏大); OK-WW 原版两处都用 `count_rings` 测量。环有细小间隙时可能边界漏判, 建议后续对齐
**排查方法沉淀**: 同队两角色 `is_con_full` 一空一满, 先核对各自 `ELEMENT` 与游戏内真实属性是否一致 (`CON_COLORS` 按索引取色)

### 2026-08-22 热键循环加固 (幽灵停止排查)

**现象**: 战斗中未按 F7 却被停止; 日志显示停止前所有角色动作循环瞬间短路 (`while task.enabled and task._combat_active` 条件已为 False), helper 日志零耗时, 仅剩 `_helper_r2_finish` 未受保护的 `time.sleep(0.1)` 可见
**定位**: `run()` 的 `PeekMessageW` 循环在 ~停止时刻取到 WM_HOTKEY 并走了停止分支 ("战斗已停止, 状态已重置" 仅该分支打印); 进程内热键核查——本任务 F7 注册在 TaskExecutor 线程, 框架 DebugTab (Ctrl+Alt+D/S) 与 StartCard (F9-F12) 各在自己 handler 线程, WM_HOTKEY 不跨线程, 故消息只能是系统检测到真实/注入的 F7 输入 (嫌疑: 键盘宏/鼠标映射/输入法)
**修复**: ① `_hotkey_id` 从 1 改为 0x1001 (避开框架 DebugTab ID 1/2、StartCard ID 999); ② 循环内校验 `msg.wParam == self._hotkey_id`, 非本任务消息记警告并忽略; ③ 每条热键消息打印 `消息id/本任务id/vk/mod/战斗状态` 诊断日志
**待观察**: 下次幽灵触发时看诊断日志——`消息id≠4097` = 抓到串入热键; `消息id=4097 vk=0x76` 但未按键 = 系统层输入注入, 往键盘宏/驱动方向查

### 2026-08-22 check_skill_available_by_size 多尺度识图

**决策**: `src/character/__init__.py` 新增 `check_skill_available_by_size(task, area, skill_image, img_threshold=0.7, min_scale=0.5, max_scale=1.5, scale_step=0.1, binary_threshold=244)`
**背景**: 框架 `find_one` 是单尺度 `matchTemplate` (特征加载缩放只适配分辨率, `target_height` 是帧+模板同步降采样, 都不是尺度容忍); 需要目标在 原大小~1.5 倍范围内都能识别成功
**实现**: 模板按 0.5/0.6/.../1.5 共 11 档缩放 (1.0 档用原模板免二次缩放误差; 缩小用 INTER_AREA, 放大用 INTER_LINEAR), 同一帧逐档 `find_one(template=...)` 匹配, 任一档命中即返回 1; 模板大于搜索区域时提前退出; 无白色占比逻辑, `skill_image` 必填
**二值化支持**: `binary_threshold>0` (默认 244) 时模板与帧区域同阈值二值化后匹配亮部形状 (`frame_processor=` 实现), 传 0 走彩色识图
**关键设计——先插值再二值化**: 插值必须作用在连续亮度上; 二值图直接缩放会丢细亮部 (缩小时白黑平均成灰, 再阈值化直接消失) 或产生灰边失真, 故流程固定为 彩色缩放 → 二值化
**与分辨率适配的关系**: 两者叠加不冲突——特征加载时框架已把模板缩到当前分辨率 (`cv2.resize` 默认 INTER_LINEAR), 本函数取 `feature.mat` (已适配) 再做相对倍率金字塔, 切换分辨率无需感知
**性能**: 技能区域小, 每档匹配亚毫秒级, 11 档总开销可忽略; 命中即提前返回

### 2026-08-24 main 模式精简 GUI (CombatTab + on_show_main_window)

**决策**: 新建 `src/ui/CombatTab.py` 自定义 Tab, 通过 `Globals.on_show_main_window()` 钩子在 non-debug 模式下移除所有默认 Tab 和导航元素
**原因**: 打包后的 exe 只展示用户需要的战斗配置界面, 不暴露框架其他功能
**实现**:
- `src/globals.py`: `on_show_main_window()` 检查 `config['debug']`, True 保留全部 GUI, False 移除 StartTab/OneTimeTaskTab/TriggerTaskTab/AboutTab/SettingTab 等所有默认 Tab, 隐藏导航侧边栏 (`navigationInterface.hide()`) 和标题栏图标 (`titleBar.iconLabel.hide()`)
- `src/ui/CombatTab.py`: 继承 `CustomTab`, 用 `TaskCard(task, onetime=True)` 渲染 CharacterAutoTask 的完整配置 (Start/Pause/Stop 按钮 + 配置控件), 自动展开并隐藏折叠按钮 (`setExpand(True)` + `expandButton.hide()`)
- `src/config.py`: 添加 `'custom_tabs': [["src.ui.CombatTab", "CombatTab"]]`
**效果**: `main_debug.py` 保留全部框架 GUI 用于调试; `main.py` 只显示 CharacterAutoTask 的展开配置卡片, 无导航栏/图标/折叠
**关键 API**: `TaskCard` 继承 `ConfigCard`, 自带 Start/Pause/Stop 按钮; `task.start()` 内部调用 `executor.start()` + `enable()`, 无需额外的全局启动按钮

### 2026-08-28 新增 6 个角色 + 动作注册

**新增角色**: xigelika(西格丽卡, MAIN_DPS, SPECTRO), verina(维里娜, SUB_DPS, SPECTRO), shorekeeper(守岸人, SUB_DPS, SPECTRO), qiuyuan(秋园, SUB_DPS, WIND), jinxi(今汐, MAIN_DPS, SPECTRO, 骨架), rebecca(雷贝卡, MAIN_DPS, ELECTRIC, 骨架)
**同时注册**: 之前未注册的 Linnai, Aemeath, Mornye, qingxiao, denia, jianxin 也完成动作注册和 run() 派发
**角色库**: 从 4 个扩展到 16 个

### 2026-08-28 角色文件导入统一为 `import *`

**决策**: 所有 17 个角色文件的 `from src.character import xxx, yyy, zzz` 统一替换为 `from src.character import *`
**原因**: 每次在 `__init__.py` 新增共享函数都要逐个修改角色文件, 维护成本高
**效果**: 新增共享函数后所有角色文件自动可用, 无需修改

### 2026-08-28 轴文件独立目录

**决策**: 轴 JSON 文件从 `src/character/` 移到 `src/axis/`
**原因**: 角色脚本和轴数据混在一起不清晰
**同步**: CharacterAutoTask 的导入轴/编辑轴和 AxisEditor 的保存轴对话框默认路径都改为 `src/axis/`

### 2026-08-28 战斗重启加速 (去除 join 等待)

**现象**: F7 停止后再按 F7 启动, 从按键到第一个技能释放延迟 1-3 秒
**原因**: `_execute_auto_mode()` 中 `t.join(timeout=1)` 等待旧线程退出, 但旧线程卡在 `time.sleep(2)` 等长睡眠中, `event.set()` 无法中断 `time.sleep()`, 每个线程最多等 1 秒, 3 个线程最多 3 秒
**修复**: 去掉 join, 直接清空 `_script_threads` 列表; daemon 线程在 `_combat_active=False` 后自行退出
**效果**: F7 重启即时生效, 旧线程在空闲期间自行消亡

### 2026-08-28 协奏值检测改为 forte_location 找色

**决策**: `is_con_full()` 从环形掩膜+连通域分析改为 `forte_location` 区域找色, 颜色占比 >= 99% 认为能量已满
**原因**: 环形掩膜方案需要校准 (`_con_full_size`), 闭运算面积和原始像素数量纲不一致, 边界漏判
**新方案**: `_precompute_con_data()` 只预计算颜色边界 (`lower`/`upper`), `is_con_full()` 在 `forte_location` 区域按角色属性颜色过滤, 统计像素占比
**保留**: 环形掩膜代码注释保留, suisui 特殊检查逻辑不变

### 2026-08-28 WGC 管理策略

**决策**: F7 停止战斗时不关闭 WGC, 任务销毁 (`on_destroy`) 时才关闭
**原因**: WGC 重建涉及 D3D11 设备创建+帧池+捕获会话, 耗时 1-3 秒; 战斗间隙保持 WGC 活跃可实现快速重启
**实现**: `_trim_memory()` 只清理 Python 工作集 (`EmptyWorkingSet`), 不调用 `method.close()`; `on_destroy()` 中单独调用 `method.close()` 释放 GPU 资源
**权衡**: 战斗停止期间游戏内存不会下降, 但重启速度从 2-3 秒降到即时

### 2026-08-28 角色脚本热重载

**决策**: F7 启动战斗时 `importlib.reload()` 所有已识别角色的脚本模块
**原因**: debug 模式下修改角色 .py 文件后需要重启整个程序才能生效, 效率低
**实现**: `_execute_combat()` 在启动角色脚本前遍历 `_detected_characters`, 对每个模块调用 `importlib.reload()`
**效果**: 修改角色脚本 → 按 F7 → 自动加载新代码, 无需重启; `register_action()` 重复调用安全 (字典覆盖)
**性能**: 每个模块 reload < 1ms, 对启动速度无影响

### 2026-08-28 f_execute 返回值修复

**现象**: 飞雪处决成功后走了 "处决失败" 分支
**原因**: `f_execute()` 的返回逻辑 `return 1 if found else 0` 只看 `found` (找图结果), 忽略了 `can_f` (二值化检测结果); 当 `can_f=True` 但 `found=False` 时, F 键已按但返回 0
**修复**: 在 `if found or can_f:` 分支内直接 `return 1`, `else` 分支 `return 0`, 返回值与实际行为一致

### 2026-08-28 AxisEditor fg_time 显示 + 角色选择网格布局

**fg_time**: 动作方块从 `fg_time_data.json` 读取实测数据 (通过 `FgTimeCollector`), 显示两位小数; 替代原从 `ACTION_REGISTRY` 读取 (fg_time 参数已移除, 永远显示 0.0)
**角色选择**: `CharacterSelectionDialog` 从 `QHBoxLayout` (单行) 改为 `QGridLayout` (每行 4 个, 自动换行), 解决角色增多后对话框过宽问题

### 2026-08-28 PyAppify 打包配置

**决策**: 配置 GitHub Actions 自动打包, `pyappify.yml` 应用名改为英文 `konghuiww`
**原因**: 中文名导致安装路径含中文, PyAppify 启动器报错 "必须是英文目录"
**CI/CD**: `.github/workflows/build.yml` 配置 push tag `v*` 触发构建, 添加 `permissions: contents: write`, `concurrency: cancel-in-progress: true` 自动取消旧构建
**跳过测试**: 模板测试 (`TestMain.py`) 不适用, `if: false` 跳过

### 2026-08-28 标准技能释放模板写入 codegen skill

**决策**: 在 `ok-character-codegen/SKILL.md` 中新增"标准技能释放模板"章节
**内容**: 两段式模式 (等待可用 → 持续按键直到消失), 关键规则: `if not` 退出条件时动作必须在判定之前
**原因**: 多个角色文件出现 `if not` 在 `send_key` 前面的错误模式, 导致技能消失时少按一次

### 2026-08-28 denia.py if-not 模式修复

**现象**: denia 的多个技能释放循环中 `if not check_skill_available` 在 `send_key` 前面
**影响**: 技能消失时循环直接 break, 最后一次按键被跳过
**修复**: 4 处循环全部改为动作在前、判定在后的标准模式 (r1 消失、super_e2 消失、r2 消失、q 消失)

### 2026-08-29 战斗任务拆分为基类 + 子任务

**决策**: 将 `CharacterAutoTask` 拆分为 `CombatBaseTask` (共享基类) + `AxisCombatTask` (打轴) + `AutoCombatTask` (自动骨架) + `AxisEditorTask` (编辑工具)
**原因**: 自动模式和打轴模式逻辑差异大, 混在一个类里难以维护; 编辑功能不应有启停按钮
**架构**:
- `CombatBaseTask`: 热键/角色检测/协奏检测/内存回收/run 主循环 (子类只需实现 `_execute_combat()`)
- `AxisCombatTask`: 继承基类, 只保留导入轴按钮, 完整保留打轴逻辑
- `AutoCombatTask`: 继承基类, 默认 F8 (与打轴 F7 不冲突), 骨架待开发
- `AxisEditorTask`: 继承 `MyBaseTask`, 新建轴/编辑轴/编辑角色三个按钮, 无启停
**CombatTab**: 打轴和自动用 `TaskCard` (含 Start/Stop), 编辑器用 `ConfigCard` (无 Start/Stop)

### 2026-08-29 新增角色 Galbrena/Lupa (热熔) + jinxi/rebecca 动作

**新增角色**: Galbrena (MAIN_DPS, FIRE), Lupa (MAIN_DPS, FIRE), 角色库扩至 18 个
**jinxi 动作**: e2, r, e4 (先 e3 → 普攻直到 e4 出现 → 释放 e4)
**rebecca 动作**: r, a12, a123, z (长按普攻直到 z 图标出现)

### 2026-08-29 角色编辑器网格布局

**问题**: CharacterEditor 角色选择区域用 QScrollArea + 固定高度 160px, 角色多了被挤出去看不到
**修复**: 去掉 QScrollArea, 改用 QGridLayout 直接显示, 每行 6 个角色, 对话框尺寸增大到 800x650

### 2026-08-29 角色文件导入统一为 `from src.character import *`

**决策**: 所有 17 个角色文件的导入行统一为一行 `from src.character import *`
**原因**: 之前每个角色文件有 3-5 行不同的 import, 新增共享函数时需要逐个修改; `import *` 后自动获取所有公开名称
**注意**: `import *` 只导入不以 `_` 开头的名称, 不会导入其他角色模块 (它们在 `__init__.py` 底部才导入, 无循环依赖)

### 2026-08-29 角色文件按属性分文件夹

**决策**: 将角色脚本从 `src/character/` 平铺改为按属性分 6 个子文件夹
**结构**:
- `spectro/` 衍射 (4): jinxi, Linnai, shorekeeper, verina
- `electric/` 导电 (1): rebecca
- `fire/` 热熔 (5): Aemeath, Mornye, denia, Galbrena, Lupa
- `ice/` 冰属性 (2): feixue, suisui
- `wind/` 气动 (4): qingxiao, jianxin, xigelika, qiuyuan
- `havoc/` 湮灭 (2): qianxiao, yangyang
**导入兼容**: 每个子文件夹有 `__init__.py` 导出角色模块, 主 `__init__.py` 从子包导入, 外部代码 `from src.character import CHARACTER_LIBRARY` 不受影响
**UI 同步**: 轴编辑器和角色编辑器的角色选择界面改为按属性分行显示, 每行一个属性标签 + 该属性角色卡片
