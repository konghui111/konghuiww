import time  # 导入时间模块, 用 time.sleep 代替 task.sleep (子线程中 task.sleep 可能不安全)
from src.character import *  # 导入所有共享工具函数和枚举

CHARACTER_NAME = "sanhua"  # 角色名, 对应 COCO 标注中的 category 后缀
CHAR_TYPE = CharType.MAIN_DPS  # 角色定位: 主输出
SWITCH_PRIORITY = SwitchPriority.NORMAL  # 切换优先级: 普通
ELEMENT = Elements.ICE  # 角色属性: 冰
RESONANCE_CHAIN = 0  # 共鸣链等级 (0-6)

# ==== 多头像 (皮肤) 支持 ====
# 如果角色有多个皮肤导致头像不同, 可以在此定义备选头像列表
# 检测时会依次尝试主头像和所有备选头像, 任意一个匹配即认为找到该角色
# 使用方法:
#   1. 在 COCO 标注中添加备选头像特征, 如 "character_sanhua_skin2", "character_sanhua_skin3"
#   2. 在此处添加 AVATAR_ALTS 列表, 如: AVATAR_ALTS = ["sanhua_skin2", "sanhua_skin3"]
#   3. 检测时会自动尝试 character_sanhua, character_sanhua_skin2, character_sanhua_skin3
# 注意: 如果没有多皮肤需求, 可以不定义 AVATAR_ALTS 或留空列表
# AVATAR_ALTS = ["sanhua_skin2"]  # 示例: 散华有第二皮肤


# ==== 辅助函数 ====

def _check_special_skill(task):  # 检测协奏值是否已满
    """通过 task.is_con_full() 检测当前角色的协奏值是否已满。"""
    hotkey = None
    for slot, name in task._detected_characters.items():
        if name == CHARACTER_NAME:
            hotkey = slot
            break
    if hotkey is None:
        return False
    return task.is_con_full(hotkey)


# ==== 动作函数 ====

def _action_zer(task):
    """
    zer: 按住鼠标左键 → 等待 e 可用 → 释放 e → 等 0.1s → 等待 r 可用 → 释放 r → 检测到自己在场 → 等待 0.1s
    """
      # 按住鼠标左键
    
    # 等待 e 可用并释放
    while task.enabled and task._combat_active:
        if check_skill_available(task, "e", skill_image="sanhua_e"):
            break
        time.sleep(0.05)
    while task.enabled and task._combat_active:
        task.send_key("e")
        time.sleep(0.05)
        if not check_skill_available(task, "e", skill_image="sanhua_e"):
            break
    time.sleep(0.3)
    
    # 等待 r 可用并释放
    while task.enabled and task._combat_active:
        if check_skill_available(task, "r", skill_image="sanhua_r"):
            break
        task.click()
        time.sleep(0.05)
    while task.enabled and task._combat_active:
        task.send_key("r")
        time.sleep(0.05)
        if not check_skill_available(task, "r", skill_image="sanhua_r"):
            break
    task.mouse_down()
    # 等待自己在场
    while task.enabled and task._combat_active:
        if detect_self_on_field(task, CHARACTER_NAME):
            break
        time.sleep(0.05)
    
    time.sleep(0.65)
    task.mouse_up()  # 释放鼠标
    time.sleep(0.05)
    return True
register_action(CHARACTER_NAME, "zer")


def _action_aa(task):
    """
    aa: 持续普攻直到 _check_special_skill 成功 → 点击 q
    """
    _click_interval = 0.07  # 点击间隔
    _last_click = 0  # 上次点击时间戳
    
    # while task.enabled and task._combat_active:
    #     # 检查协奏值是否已满
    #     if _check_special_skill(task):
    #         break
    #     # 持续攻击
    #     if time.time() - _last_click >= _click_interval:
    #         task.click()
    #         _last_click = time.time()
    #     time.sleep(0.05)
    
    # 点击 q
    # task.click()
    # time.sleep(0.03)
    continuous_click(task, 0.9)
    task.send_key("q")
    return True
register_action(CHARACTER_NAME, "aa")


def _action_skill_coordination(task):
    """变奏动作"""
    continuous_click(task, 0.8)  # 持续点击 1 秒
    return True
register_action(CHARACTER_NAME, "skill_coordination", force_clear=True)  # 注册变奏动作


# ==== 入口函数 ====

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
            if axis_action == "zer":
                action_success = _action_zer(task)
            elif axis_action == "aa":
                action_success = _action_aa(task)
            elif axis_action == "skill_coordination":
                action_success = _action_skill_coordination(task)
            else:
                task.log_error(f"轴配置错误: {CHARACTER_NAME} 未知动作 {axis_action}")
            set_axis_result(task, CHARACTER_NAME, action_success)
        else:
            task.log_info(f"{CHARACTER_NAME} 暂不支持自动模式")
            time.sleep(0.1)

    task.log_info(f"{CHARACTER_NAME} 战斗脚本已停止")
