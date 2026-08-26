import time  # 导入时间模块, 用 time.sleep 代替 task.sleep (子线程中 task.sleep 可能不安全)
from src.character import get_location_box, wait_for_my_turn, continuous_click, register_action, CharType, SwitchPriority, Elements  # 导入共享工具函数和枚举
from src.character import get_axis_command, set_axis_result  # 导入轴命令机制函数
from src.character import check_skill_available  # 导入技能检测函数
from src.character import calculate_binary_percentage  # 导入二值化找色函数

CHARACTER_NAME = "Linnai"  # 角色名, 对应 COCO 标注中的 category 后缀
CHAR_TYPE = CharType.SUB_DPS  # 角色定位: 副输出
SWITCH_PRIORITY = SwitchPriority.NORMAL  # 切换优先级: 普通
ELEMENT = Elements.SPECTRO  # 角色属性: 衍射 (协奏值环颜色索引 0, 黄色; 原误配为 HAVOC 导致 is_con_full 恒 False)
RESONANCE_CHAIN = 0  # 共鸣链等级 (0-6)


# ==== 动作函数 ====

def _action_e(task):
    """
    e 技能: 找技能e → 点击e → 等待e消失
    """
    continuous_click(task, 0.2)
    while task.enabled and task._combat_active:  # 等待 e 可用
        if check_skill_available(task, "e"):
            break
        time.sleep(0.05)
    while task.enabled and task._combat_active:  # 持续按 e 直到 e 消失
        if not check_skill_available(task, "e"):
            break
        task.send_key("e")
        time.sleep(0.05)
    # time.sleep(0.1)    
    return True
register_action(CHARACTER_NAME, "e")  # 注册 e 技能动作

def _action_r(task):
    """
    r 技能: 循环点击r等待找不到r → 释放左键 → 再按住左键
    """
    # end_time = time.time() + 1  # 计算结束时间戳
    # while time.time() < end_time:  # 在指定时间内持续点击
    #     if task.enabled and task._combat_active:  # 检查是否需要继续
    #         break  # 任务已停止, 退出循环
    #     task.send_key("r")  # 点击鼠标左键
    #     time.sleep(0.07)  # 每次点击间隔 20ms
    # task.send_key_down("r")
    # task.send_key_up("r")
    # task.send_key_down("r")
    task.log_info(f"{CHARACTER_NAME} 等待r就绪")
    while task.enabled and task._combat_active: 
        if check_skill_available(task, "r"):
            break
        time.sleep(0.07)
    while task.enabled and task._combat_active:  # 循环点击直到 r 消失
        task.send_key("r")
        time.sleep(0.05)
        if not check_skill_available(task, "q"):
            # task.send_key_up("r")
            break
    task.log_info(f"{CHARACTER_NAME} r释放完毕")    
    task.mouse_up()  # 释放左键
    time.sleep(1)
    task.mouse_down()  # 再按住左键
    return True
register_action(CHARACTER_NAME, "r")  # 注册 r 技能动作

def _action_jump_a(task):
    """
    跳a: 等待二值化找色 → 空格跳跃 → 松开左键 → 普攻
    """
    task.mouse_down()
    # time.sleep(0.2)
    task.send_key("q")
    time.sleep(0.6)
    while task.enabled and task._combat_active:  #
        if check_skill_available(task, "Linnai_120", skill_image="Linnai_120_location"):
            break
    #等待重击命中    
    time.sleep(0.5)
    while task.enabled and task._combat_active:  # 
        if check_skill_available(task, "Linnai_80", skill_image="Linnai_80_location"):
            break   
        task.send_key("space") # 空格跳跃
        time.sleep(0.05) 
    time.sleep(0.1)    
    task.mouse_up()  # 松开左键
    while task.enabled and task._combat_active:
        if _check_special_skill(task):
            break
        task.send_key("space")
        task.click()
        time.sleep(0.05)
    time.sleep(0.1)    
    return True
register_action(CHARACTER_NAME, "jump_a")  # 注册跳a动作

def _action_zr_jump_a(task):
    """
    zr跳跳跳a:
    等待二值化找色 → 空格 → 松开左键 → a
    → r → 等待找不到e → 连续空格直到找到super_a → 连续a直到super_a消失
    """
    task.mouse_down()
    # time.sleep(0.2)
    task.send_key("q")
    time.sleep(0.6)
    while task.enabled and task._combat_active:  #
        if check_skill_available(task, "Linnai_120", skill_image="Linnai_120_location"):
            break
    time.sleep(0.5)
    # task.send_key("q")
    task.send_key("r")  # 按 r 键
    task.mouse_up()
    time.sleep(1)
    # while task.enabled and task._combat_active:
    #     if not check_skill_available(task, "a"):  # a 已不可用
    #         break
    #     time.sleep(0.07)  # 轮询间隔    
    while task.enabled and task._combat_active:
        if check_skill_available(task,"Linnai_0", skill_image="Linnai_0_location"):  # super_a 可用
            break
        task.send_key("space")  # 按空格键
        time.sleep(0.1)  # 点击间隔
    while task.enabled and task._combat_active:
        if check_skill_available(task,"e", skill_image="Linnai_super_a"):  # super_a 可用
            break
        time.sleep(0.05)  # 点击间隔          
    while task.enabled and task._combat_active:
        task.click()
        time.sleep(0.1)  # 点击间隔 
        if not check_skill_available(task,"e", skill_image="Linnai_super_a"):  # super_a 已不可用
            break
    time.sleep(0.05)
    while task.enabled and task._combat_active:
        if _check_special_skill(task):
            break
        task.click()
        time.sleep(0.05)
    return True
register_action(CHARACTER_NAME, "zr_jump_a")  # 注册 zr跳跳跳a 动作


def _action_skill_coordination(task):
    """变奏动作"""
    continuous_click(task, 0.8)  # 持续点击 0.8 秒
    return True
register_action(CHARACTER_NAME, "skill_coordination", force_clear=True)  # 注册变奏动作



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
            if axis_action == "e":  # e 技能
                action_success = _action_e(task)
            elif axis_action == "r":  # r 技能
                action_success = _action_r(task)
            elif axis_action == "jump_a":  # 跳a
                action_success = _action_jump_a(task)
            elif axis_action == "zr_jump_a":  # zr跳跳跳a
                action_success = _action_zr_jump_a(task)
            elif axis_action == "skill_coordination":  # 变奏
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

    task.log_info(f"{CHARACTER_NAME} 战斗脚本已停止")
