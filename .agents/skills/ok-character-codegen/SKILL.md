---
name: ok-character-codegen
description: Generate Python character action functions for ok-script combat automation from text axis descriptions. Use when the user provides a text-based combat rotation (轴) with action flow descriptions and needs complete character script files with action functions, register_action calls, and run() dispatch logic. Supports placeholder image/region names for later manual refinement.
---

# OK Character Codegen

## Purpose

根据用户提供的文字轴描述, 生成完整的角色战斗脚本文件。包括:
- 动作函数 (`_action_xxx`)
- `register_action` 注册调用
- `run()` 函数中的动作分发逻辑
- 导入和常量定义

用户会在轴描述中提供每个动作的详细流程, 但图片/区域名称可能尚未确定, 用 "识图"、"找色" 等关键词代替。生成的代码对这些未指定的部分使用占位符, 方便用户后续修改调试。

## 参考文件

生成代码前, 必须阅读以下参考文件了解代码模式和项目约定:

- `src/character/feixue.py` — 最复杂的角色: 蓄力 (mouse_down/up)、色相检测 (check_skill_available_by_color)、二值化识图 (check_skill_available + skill_image)、处决分支 (f_execute)、多阶段连招
- `src/character/qianxiao.py` — 中等复杂度: 多动作类型 (ea3, a4, z, qre, super_z2a3)、buff 检测
- `src/character/suisui.py` — 条件分支: buff 检查 (check_buff)、多种动作类型
- `src/character/__init__.py` — 共享函数定义: register_action, check_skill_available (不传 skill_image=严格纯白占比判 CD; 传=二值化识图, binary_threshold 可调), check_skill_available_by_color (色相区分), check_skill_available_binary/calculate_binary_percentage (亮度占比), f_execute (中央区域找处决按键), continuous_click 等

## 输入格式

用户以文字描述提供轴信息, 格式灵活, 但应包含:

```
角色名: feixue
角色定位: MainDps (MainDps / SubDps / Healer)
角色属性: ICE (SPECTRO / ELECTRIC / FIRE / ICE / WIND / HAVOC)

startup:
  - feixue.charge: 按住左键, 识图等待 feixue_r1 区域出现白色, 松开左键, 按q, 按r, 识图等待r图标消失, 等待1秒, 找色等待e可用
  - feixue.combo1: 持续点击1.2秒, 右键, 等待0.5秒

loop:
  - feixue.main: (完整流程描述...)
  - qianxiao.ea3: 按e, 等待0.1秒, 持续点击0.5秒
```

### 流程描述关键词映射

| 用户描述 | 生成代码 |
|---------|---------|
| "按e" / "按r" / "按q" | `task.send_key("e")` |
| "按住e" / "长按e" | `task.send_key_down("e")` |
| "松开e" / "释放e" | `task.send_key_up("e")` |
| "按住左键" / "按住鼠标" | `task.mouse_down()` |
| "松开左键" / "松开鼠标" | `task.mouse_up()` |
| "a" / "aa" / "aaa" / "普攻" | 循环点击鼠标左键, 根据描述决定退出条件 (见下方规则) |
| "持续点击X秒" / "普攻X秒" | `continuous_click(task, X)` — 固定时长, 无退出条件 |
| "点击一下" / "单击" | `task.click()` |
| "右键" / "右键点击" | `task.right_click(after_sleep=0)` |
| "等待X秒" / "等X秒" | `time.sleep(X)` |
| "找e" / "找r" / "找技能" / "找e技能" / "等待技能" | `check_skill_available(task, "X")` — 严格纯白占比判 CD (图标亮起=可用) |
| "识图等待X" / "找图等待X" | `while` 循环 + `check_skill_available(task, "X")` |
| "识图等待X消失" / "找e直到消失" | `while` 循环 + `not check_skill_available(task, "X")` |
| "释放技能X" / "放e" / "放r" (完整技能释放) | 标准技能释放模式: 先等待可用 → 再持续按键直到消失 (见下方模板) |
| "识图X状态" / "识图X图标" (指定了具体图片) | `check_skill_available(task, "X", skill_image="Y")` — 二值化识图 |
| "找色" / "找色检测X" | `check_skill_available_by_color(task, "X", color=PLACEHOLDER)` — 按色相找色检测 |
| "找色等待X" / "颜色检测等待X" | `while` 循环 + `check_skill_available_by_color(task, "X", color=PLACEHOLDER)` |
| "找色等待X消失" | `while` 循环 + `not check_skill_available_by_color(...)` |
| "等待X可用" / "等X就绪" | `while` 循环 + `check_skill_available(task, "X")` |
| "如果X可用" / "X可用时" | `if check_skill_available(task, "X"):` |
| "如果buff激活" / "检查X buff" | `if check_buff(task, slot, "X"):` |
| "处决" / "F处决" | `f_execute(task, 时间)` |
| "跳跃" / "空格" | `task.send_key("space")` |

### 标准技能释放模板

当描述为"释放某技能"或"放e/r/q"时, 生成以下标准模式 (动作在判定前, 确保最后一次按键不被跳过):

```python
# 步骤1: 等待技能可用
while task.enabled and task._combat_active:  # 等待 e 可用
    if check_skill_available(task, "e", skill_image="xxx_e"):
        break
    time.sleep(0.05)
# 步骤2: 持续按键直到技能消失 (动作在前, 判定在后)
while task.enabled and task._combat_active:  # 持续按 e 直到 e 消失
    task.send_key("e")
    time.sleep(0.05)
    if not check_skill_available(task, "e", skill_image="xxx_e"):
        break
```

**关键规则**: 当循环退出条件是 `if not` (技能消失) 时, 动作语句 (`send_key`) 必须放在 `if not` **之前**, 保证技能消失前的最后一次按键被执行。

### 检测方式选择 (重要)

按被检测目标的性质选检测方法, 选错会导致误判:

| 场景 | 方法 | 原理与注意 |
|------|------|------|
| 技能可用/CD (亮度亮灭) | `check_skill_available(task, "X")` | 严格纯白占比: 可用时图标大部分纯白 (>86%), CD 时只有倒计时数字 (<2%); 阈值 `white_threshold` 默认 0.02, 个别技能微调 |
| 特定图标形状/状态 | `check_skill_available(task, "X", skill_image="Y")` | 二值化识图: 帧区域和模板同阈值二值化后匹配, 对颜色偏移鲁棒; 彩色图标识别不稳时可下调 `binary_threshold` (默认 244, 可降到 200) |
| 靠色相区分 (如青 vs 粉) | `check_skill_available_by_color(task, "X", color=..., color_threshold=...)` | 二值化只看亮度、丢失色相, 色相区分**必须**用找色, 不能改二值化 |
| 只要亮度占比 | `check_skill_available_binary(task, "X")` 或 `calculate_binary_percentage(task, box)` | 二值化白色占比, 见 PROJECT_INDEX "二值化找色使用方法" |

处决检测统一用 `f_execute(task, f_time)` — 屏幕中央区域找处决按键图片 (提示随怪物移动, 不能固定位置检测)。

### 占位符规则

当用户用 "识图"、"找色" 等关键词但未指定具体名称时:

- **区域/图片名**: 使用 `PLACEHOLDER_描述` 格式, 如 `PLACEHOLDER_r1_color`
- **颜色值**: 使用 `PLACEHOLDER_COLOR` 并在注释中说明需要替换
- **时间值**: 如果用户未指定, 使用合理默认值并注释 `# TODO: 调整时间`

生成的占位符示例:
```python
# TODO: 替换为实际的区域名和颜色值
if check_skill_available_by_color(task, "PLACEHOLDER_r1_region",
    color={'r': (0, 0), 'g': (0, 0), 'b': (0, 0)}, color_threshold=0.3):
    break
```

### "a" / "aa" / "aaa" 普攻生成规则

"a" 系列描述生成循环点击, 根据退出条件不同生成不同代码:

**情况 1: 固定时长 (无退出条件)**
```
用户描述: "a 1.2秒" 或 "持续点击1.2秒"
```
```python
continuous_click(task, 1.2)  # 普攻1.2秒
```

**情况 2: 有条件退出 (无时长限制)**
```
用户描述: "a 直到e可用" 或 "aaa 直到找色X"
```
```python
while task.enabled and task._combat_active:  # 循环普攻直到条件满足
    if check_skill_available(task, "e"):  # 退出条件: e技能可用
        break
    task.click()  # 点击鼠标左键
    time.sleep(0.07)  # 点击间隔
```

**情况 3: 有条件退出 + 最大时长兜底**
```
用户描述: "a 最多2秒, 直到找e" 或 "aaa 2秒内直到e可用"
```
```python
end_time = time.time() + 2.0  # 最大时长2秒
while task.enabled and task._combat_active:
    if time.time() >= end_time:  # 超时退出
        break
    if check_skill_available(task, "e"):  # 条件退出
        break
    task.click()
    time.sleep(0.07)
```

**判断规则:**
- 描述中有 "X秒" / "X秒内" / "最多X秒" → 有时长限制
- 描述中有 "直到..." / "直到..." → 有退出条件
- 同时有两者 → 情况 3 (条件 + 时长兜底)
- 只有时长 → 情况 1 (直接用 continuous_click)
- 只有条件 → 情况 2 (无限循环直到条件满足)

## 输出结构

生成的角色文件应包含以下部分, 顺序固定:

```python
import time  # 导入时间模块
from src.character import (  # 导入共享工具
    get_location_box, wait_for_my_turn, continuous_click,
    register_action, get_character_actions,
    CharType, SwitchPriority, Elements,
)
from src.character import get_axis_command, set_axis_result  # 导入轴命令机制
# ... 按需导入: freeze_time, check_skill_available, check_buff, f_execute 等

CHARACTER_NAME = "xxx"  # 角色名
CHAR_TYPE = CharType.MAIN_DPS  # 角色定位
SWITCH_PRIORITY = SwitchPriority.NORMAL  # 切换优先级
ELEMENT = Elements.ICE  # 角色属性

# ==== 动作函数 + 注册 (每个 register_action 紧跟对应动作) ====
def _action_xxx(task):
    """动作描述"""
    # ... 动作逻辑 ...
    return True
register_action(CHARACTER_NAME, "xxx")  # 注册动作 xxx

# ==== 变奏动作 ====
def _action_skill_coordination(task):
    """变奏动作"""
    task._character_jumping = True
    continuous_click(task, 1.0)
    return True
register_action(CHARACTER_NAME, "skill_coordination", force_clear=True)  # 注册变奏动作

# ==== 入口函数 ====
def run(task):
    # ... 标准 run 函数 (从参考文件复制模式) ...
```

## 生成规则

1. **每个动作一个函数**: 函数名 `_action_{动作名}`, 接收 `task` 参数, 返回 `True`
2. **register_action 紧跟动作函数**: 每个 `register_action` 调用必须放在对应动作函数的 `return True` 下方, 不要集中放在文件底部。这样方便增删动作时同步修改注册。
3. **增量添加, 不删除已有技能**: 添加新技能时, 保留文件中已有的所有动作函数和注册, 只在合适位置插入新动作。绝对不要覆盖整个文件。
4. **提取重复逻辑为辅助函数**: 当多个动作函数包含相同的逻辑片段时 (如 startup 和 loop 共享一段连招), 将该片段提取为独立的辅助函数 (命名 `_helper_xxx`), 各动作函数调用它。辅助函数放在动作函数之前, 不需要 register_action。
5. **while 循环必须检查活跃状态**: `while task.enabled and task._combat_active:`
6. **轮询间隔**: 识图/找色轮询用 `time.sleep(0.01)` ~ `time.sleep(0.05)`
7. **蓄力模式**: 按住 → 轮询条件 → 松开, 参考 feixue 的 `_action_main`
8. **条件等待模式**: `while` + 条件 + `break`, 不用 timeout (由外层 `task.enabled` 控制退出)
9. **变奏动作**: 固定模式 `task._character_jumping = True` + `continuous_click`
10. **run 函数**: 从参考文件复制标准模板, 只需在 `if/elif` 分支中添加新动作
11. **注释**: 每行代码加中文注释, 与项目风格一致
12. **占位符注释**: 所有占位符旁加 `# TODO:` 注释说明需要替换什么

## 标准 run 函数模板

run 函数结构固定, 从参考文件复制并修改动作分发部分:

```python
def run(task):
    global SWITCH_PRIORITY
    SWITCH_PRIORITY = SwitchPriority.NORMAL
    task.log_info(f"{CHARACTER_NAME} 战斗脚本开始执行")

    hotkey = None
    for slot, name in task._detected_characters.items():
        if name == CHARACTER_NAME:
            hotkey = str(slot)
            break
    if not hotkey:
        task.log_warning(f"{CHARACTER_NAME} 未在识别结果中找到")
        return
    task.info_set("按键", hotkey)

    slot = int(hotkey)

    while task.enabled and task._combat_active:
        wait_for_my_turn(task, hotkey, CHARACTER_NAME)

        attack_counts = task._char_data[slot]['attack_counts']
        action_success = False

        axis_action = get_axis_command(task, CHARACTER_NAME)
        if axis_action:
            task.log_info(f"{CHARACTER_NAME} 收到轴命令: {axis_action}")
            if axis_action == "action1":
                action_success = _action_action1(task)
            elif axis_action == "action2":
                action_success = _action_action2(task)
            # ... 更多动作分支 ...
            elif axis_action == "skill_coordination":
                action_success = _action_skill_coordination(task)
            else:
                task.log_error(f"轴配置错误: {CHARACTER_NAME} 未知动作 {axis_action}")
            set_axis_result(task, CHARACTER_NAME, action_success)
        else:
            task.log_info(f"{CHARACTER_NAME} 暂不支持自动模式")
            time.sleep(0.1)

        if action_success:
            if task.config.get("战斗模式", "自动") != "打轴":
                if _check_special_skill(task):
                    task._char_data[slot]['skill_ready'] = True
                    task.log_info(f"{CHARACTER_NAME} 特殊技能就绪, 强制切换")
                    task.schedule_next_character(force=True)
                else:
                    task.schedule_next_character()
```

## 检查清单

生成代码后验证:

- [ ] 每个动作都有对应的 `_action_xxx` 函数
- [ ] 每个 `register_action` 紧跟在对应动作函数的 `return True` 下方, 不集中放在文件底部
- [ ] run 函数的 if/elif 分支覆盖所有动作
- [ ] 所有 while 循环都检查 `task.enabled and task._combat_active`
- [ ] 占位符都有 `# TODO:` 注释
- [ ] 每行代码都有中文注释
- [ ] 导入了实际用到的函数 (check_skill_available, check_buff 等)
- [ ] 检测方式选择正确: 亮度亮灭用 check_skill_available, 指定图片用 skill_image 二值化识图, 色相区分用 check_skill_available_by_color (见"检测方式选择")
- [ ] CHAR_TYPE, ELEMENT 与用户指定一致
- [ ] 变奏动作 `skill_coordination` 已包含
