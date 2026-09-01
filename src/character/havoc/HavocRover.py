import time  # 导入时间模块, 用 time.sleep 代替 task.sleep (子线程中 task.sleep 可能不安全)
from src.character import *  # 导入所有共享工具函数和枚举

CHARACTER_NAME = "HavocRover"  # 角色名, 对应 COCO 标注中的 category 后缀 (湮灭属性漂泊者)
CHAR_TYPE = CharType.MAIN_DPS  # 角色定位: 主输出
SWITCH_PRIORITY = SwitchPriority.NORMAL  # 切换优先级: 普通
ELEMENT = Elements.HAVOC  # 角色属性: 湮灭
RESONANCE_CHAIN = 0  # 共鸣链等级 (0-6)


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

def _action_r(task):
    """释放 r 技能: 等待 r 可用 → 持续按 r 直到 r 消失"""
    while task.enabled and task._combat_active:  # 等待 r 可用
        if check_skill_available(task, "r", skill_image="HavocRover_r"):
            break
        time.sleep(0.05)
    while task.enabled and task._combat_active:  # 持续按 r 直到 r 消失
        task.send_key("r")
        time.sleep(0.05)
        if not check_skill_available(task, "r", skill_image="HavocRover_r"):
            break
    while task.enabled and task._combat_active:  
        if detect_self_on_field(task, CHARACTER_NAME):
            break
        time.sleep(0.05)    
    return True
register_action(CHARACTER_NAME, "r")


def _action_e(task):
    """释放 e 技能: 等待 e 可用 → 持续按 e 直到 e 消失"""
    while task.enabled and task._combat_active:  # 等待 e 可用
        if check_skill_available(task, "e", skill_image="HavocRover_e"):
            break
        time.sleep(0.05)
    while task.enabled and task._combat_active:  # 持续按 e 直到 e 消失
        task.send_key("e")
        time.sleep(0.05)
        if not check_skill_available(task, "e", skill_image="HavocRover_e"):
            break
    return True
register_action(CHARACTER_NAME, "e")


def _action_q(task):
    """释放 q 技能: 直接按 q (不需要检测)"""
    task.send_key("q")
    time.sleep(0.05)
    # time.sleep(0.1)
    task.right_click()
    time.sleep(0.05)
    # task.send_key("e")
    return True
register_action(CHARACTER_NAME, "q")


def _action_ze(task):
    """
    ze: 普攻直到在 forte_begin 区域找到颜色 → 长按鼠标 → 在 forte 区域找到图片后按 e
    """
    # 普攻直到 forte_begin 区域找到颜色
    _click_interval = 0.07  # 点击间隔
    _last_click = 0  # 上次点击时间戳 HavocRover_forte_begin_location (255,48,131)
    # while task.enabled and task._combat_active:
    #     if check_skill_available_by_color(task, "HavocRover_forte_begin",
    #             color={'r': (250, 255), 'g': (43, 53), 'b': (126, 136)}, color_threshold=0.99):
    #         break
    #     if time.time() - _last_click >= _click_interval:
    #         task.click()
    #         _last_click = time.time()
    #     time.sleep(0.01)
    
    # 长按鼠标一段时间
    task.mouse_down()
    # time.sleep(1.5)
    
    # 等待 forte 区域找到图片
    while task.enabled and task._combat_active:
        if check_skill_available(task, "e", skill_image="HavocRover_super_e"):
            break
        time.sleep(0.05)
    
    task.mouse_up()
    # time.sleep(0.1)
    # 按 e 直到 e 消失
    while task.enabled and task._combat_active:
        task.send_key("e")
        time.sleep(0.05)
        if not check_skill_available(task, "e", skill_image="HavocRover_super_e"):
            break 
    time.sleep(1.4)    
    return True
register_action(CHARACTER_NAME, "ze")


def _action_aaa(task):
    """
    aaa: 持续攻击循环
    1. 判断能否释放大招, 可以就释放 r 然后等到自己在场, 不能就调用处决函数
    2. 持续攻击时间超过 a5_time 后, 点击 q 等待 50ms 点击右键闪避然后等待 0.5s, 重置 a_time
    3. 退出条件: 总时间超过 aaa_finish_time (扣除 r 和 f 的动画时间)
    """
    aaa_start_time = time.time()  # 记录 aaa 开始时间 (用于计算总时长) HavocRover_forte_location
    a_start_time = time.time()  # 记录开始攻击时间 (用于计算闪避间隔)
    a5_time = 2.75  # 持续攻击时间阈值, 超过后触发闪避
    _click_interval = 0.07  # 点击间隔
    _last_click = 0  # 上次点击时间戳 
    aaa_finish_time = 9
    while task.enabled and task._combat_active:
        # 1. 判断能否释放大招
        if check_skill_available(task, "r", skill_image="HavocRover_r"):
            # 释放 r 直到 r 消失
            while task.enabled and task._combat_active:
                task.send_key("r")
                time.sleep(0.05)
                if not check_skill_available(task, "r", skill_image="HavocRover_r"):
                    break
            # 等待自己在场
            while task.enabled and task._combat_active:
                if detect_self_on_field(task, CHARACTER_NAME):
                    break
                time.sleep(0.05)
            time.sleep(0.3)
            aaa_finish_time += 2.3
            a_start_time = time.time()  # 重置攻击时间
            continue

        # 2. 检查持续攻击时间
        a_elapsed = time.time() - a_start_time
        if a_elapsed >= a5_time:
            if f_execute(task, f_time=1.5):
                aaa_finish_time += 1.5
            else:
                task.right_click() # 右键闪避
                continuous_click(task, 0.4)
            a_start_time = time.time()  # 重置攻击时间
            # 在 f_execute 后立即检查退出条件: 时间到 且 forte 区域找不到图
            if time.time() - aaa_start_time >= aaa_finish_time:
                task.send_key("q")
                time.sleep(0.05)
                break
            continue
        if not check_image_match(task, "HavocRover_forte", skill_image="HavocRover_forte_location"):  
            task.send_key("q")
            time.sleep(0.05)
            break 
        # 3. 持续攻击
        if time.time() - _last_click >= _click_interval:
            task.click()
            _last_click = time.time()
        time.sleep(0.02)

    return True
register_action(CHARACTER_NAME, "aaa")


def _action_aaae(task):
    """
    aaae: 持续攻击一段时间后释放 e
    """
    _click_interval = 0.07  # 点击间隔
    _last_click = 0  # 上次点击时间戳
    attack_duration = 2.7  # 攻击持续时间
    start_time = time.time()
    
    # while task.enabled and task._combat_active:
    #     if time.time() - start_time >= attack_duration:
    #         break
    #     if time.time() - _last_click >= _click_interval:
    #         task.click()
    #         _last_click = time.time()
    #     time.sleep(0.02)
    continuous_click(task, 2.8)
    # 释放 e 直到 e 消失
    # task.send_key("r")
    # while task.enabled and task._combat_active:  # 等待 e 可用
    #     time.sleep(0.05)
    #     if check_skill_available(task, "e", skill_image="HavocRover_e"):
    #         break
    while task.enabled and task._combat_active:
        task.send_key("e")
        time.sleep(0.05)
        if not check_skill_available(task, "e", skill_image="HavocRover_e"):
            break
    return True
register_action(CHARACTER_NAME, "aaae")


def _action_skill_coordination(task):
    """变奏动作"""
    continuous_click(task, 1.5)  # 持续点击 1 秒
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
            if axis_action == "r":
                action_success = _action_r(task)
            elif axis_action == "e":
                action_success = _action_e(task)
            elif axis_action == "q":
                action_success = _action_q(task)
            elif axis_action == "ze":
                action_success = _action_ze(task)
            elif axis_action == "aaa":
                action_success = _action_aaa(task)
            elif axis_action == "aaae":
                action_success = _action_aaae(task)
            elif axis_action == "skill_coordination":
                action_success = _action_skill_coordination(task)
            else:
                task.log_error(f"轴配置错误: {CHARACTER_NAME} 未知动作 {axis_action}")
            set_axis_result(task, CHARACTER_NAME, action_success)
        else:
            task.log_info(f"{CHARACTER_NAME} 暂不支持自动模式")
            time.sleep(0.1)

    task.log_info(f"{CHARACTER_NAME} 战斗脚本已停止")
