import time  # 导入时间模块, 用 time.sleep 代替 task.sleep (子线程中 task.sleep 可能不安全)
from src.character import get_location_box, wait_for_my_turn, continuous_click, register_action, CharType, SwitchPriority, Elements  # 导入共享工具函数和枚举
from src.character import get_axis_command, set_axis_result  # 导入轴命令机制函数
from src.character import check_skill_available, check_skill_available_by_color  # 导入技能检测函数
from src.character import calculate_binary_percentage  # 导入二值化找色函数

CHARACTER_NAME = "Mornye"  # 角色名, 对应 COCO 标注中的 category 后缀
CHAR_TYPE = CharType.SUB_DPS  # 角色定位: 副输出
SWITCH_PRIORITY = SwitchPriority.NORMAL  # 切换优先级: 普通
ELEMENT = Elements.FIRE  # 角色属性: 衍射
RESONANCE_CHAIN = 0  # 共鸣链等级 (0-6)


# ==== 动作函数 ====

def _action_aa_a3rz(task):
    """
    3arz: 普攻等待找色 → 循环点击r等待找不到r → 按住鼠标左键
    """
    # task.mouse_down() 
    # while task.enabled and task._combat_active:  # 普攻直到找色条件满足 (255,167,119)
    #     if check_skill_available_by_color(task, "feixue_r1",
    #             color={'r': (255, 255), 'g': (167, 167), 'b': (119, 119)}, color_threshold=0.3):
    #         break
    #     task.click()
    #     time.sleep(0.07)
    while task.enabled and task._combat_active:  # 循环点击直到 r 消失
        task.click()
        time.sleep(0.07)
        if check_skill_available(task, "a", skill_image="Mornye_z"):
            break   
    # while task.enabled and task._combat_active:  # 循环点击直到 r 消失
    #     task.click()
    #     time.sleep(0.07)
    #     if not check_skill_available(task, "lock", skill_image="lock_location"):
    #         break         
    # time.sleep(0.1)    
    while task.enabled and task._combat_active:  # 循环点击直到 r 消失
        task.send_key_down("r")
        time.sleep(0.05)
        if not check_skill_available(task, "r", skill_image="Mornye_r"):
            break
    time.sleep(1)    
    task.mouse_down()  # 按住鼠标左键
    return True
register_action(CHARACTER_NAME, "aa_a3rz")  # 注册 3arz 动作

def _action_3aez(task):
    """
    3aez: 按住鼠标左键 → 等待二值化找色 e
    """
    task.mouse_down()  # 按住鼠标左键
    box = get_location_box(task, "Mornye_forte_location")
    while task.enabled and task._combat_active:  # 等待二值化条件满足 (calculate_binary_percentage 内部自动刷帧)
        if box and calculate_binary_percentage(task, box, 192) < 0.05: #0.07859078
            break
        time.sleep(0.05) 
    # time.sleep(0.1)       
    # while task.enabled and task._combat_active:  # 等待二值化条件满足 (calculate_binary_percentage 内部自动刷帧)
    #     if box and calculate_binary_percentage(task, box, 192) >= 0.7: #0.07859078 (193,197,241) 0.2552552552552553
    #         break
    #     time.sleep(0.05)
    time.sleep(1.8)    
    # continuous_click(task, 2)
    task.log_info(f"{CHARACTER_NAME} 回路足够释放e")    
    while task.enabled and task._combat_active:  #
        task.send_key("e")
        time.sleep(0.05)
        if not check_skill_available(task, "e",skill_image="Mornye_e"):
            break
    # while task.enabled and task._combat_active:  # 等待二值化条件满足 (calculate_binary_percentage 内部自动刷帧)
    #     if box and calculate_binary_percentage(task, box, 192) < 0.05: #0.07859078
    #         break
    #     time.sleep(0.05)    
    # time.sleep(0.7)
    task.log_info(f"{CHARACTER_NAME} 回路足够释放重击")    
    time.sleep(1)     #  z  
    while task.enabled and task._combat_active:
        if _check_special_skill(task):
            break
        time.sleep(0.05)  
    task.mouse_up()           
    return True
register_action(CHARACTER_NAME, "3aez")  # 注册 3aez 动作

def _action_3aezr(task):
    """
    3aezr: 按住鼠标左键 → 等待二值化找色 e → r → 等待找不到 e
    """
    task.mouse_down()  # 按住鼠标左键
    box = get_location_box(task, "Mornye_forte_location")
    while task.enabled and task._combat_active:  # 等待二值化条件满足 (calculate_binary_percentage 内部自动刷帧)
        if box and calculate_binary_percentage(task, box, 192) < 0.05: #0.07859078
            break
        time.sleep(0.05) 
    time.sleep(1.8)    #TODO
    task.log_info(f"{CHARACTER_NAME} 回路足够释放e")    
    while task.enabled and task._combat_active:  #
        task.send_key("e")
        time.sleep(0.05)
        if not check_skill_available(task, "e",skill_image="Mornye_e"):
            break
    task.log_info(f"{CHARACTER_NAME} 等待z")    
    while task.enabled and task._combat_active:  # 等待二值化条件满足 (calculate_binary_percentage 内部自动刷帧)
        if box and calculate_binary_percentage(task, box, 192) < 0.05: #0.07859078
            break
        time.sleep(0.05)    
    time.sleep(0.7)     #  z 
    # wait r
    task.log_info(f"{CHARACTER_NAME} 等待r") 
    while task.enabled and task._combat_active:  # 
        if check_skill_available(task, "r", skill_image="Mornye_r2"):
            break    
        time.sleep(0.05)
    task.log_info(f"{CHARACTER_NAME} 释放r")     
    while task.enabled and task._combat_active:  # 
        task.send_key("r")
        time.sleep(0.1)
        if not check_skill_available(task, "r", skill_image="Mornye_r2"):
            break
    task.log_info(f"{CHARACTER_NAME} 等待r结束")    
    time.sleep(2)    
    while task.enabled and task._combat_active:  # 
        if check_skill_available(task, "a"):
            break
        time.sleep(0.05)
    task.send_key("q")
    time.sleep(0.05)         
    while task.enabled and task._combat_active:
        if _check_special_skill(task):
            break
        task.click()
        time.sleep(0.05)
    return True


def _action_skill_coordination(task):
    """变奏动作"""
    task._character_jumping = True  # 标记角色跳跃中
    continuous_click(task, 0.70)  # 持续点击 0.8 秒
    return True


# ==== 动作注册 ====
register_action(CHARACTER_NAME, "3aezr")  # 注册 3aezr 动作
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
            if axis_action == "aa_a3rz":  # aa_a3rz 动作
                action_success = _action_aa_a3rz(task)
            elif axis_action == "3aez":  # 3aez 动作
                action_success = _action_3aez(task)
            elif axis_action == "3aezr":  # 3aezr 动作
                action_success = _action_3aezr(task)
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
