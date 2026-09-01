import time  # 导入时间模块, 用 time.sleep 代替 task.sleep (子线程中 task.sleep 可能不安全)
from src.character import *  # 导入所有共享工具函数和枚举
CHARACTER_NAME = "feixue"  # 角色名, 对应 COCO 标注中的 category 后缀
CHAR_TYPE = CharType.MAIN_DPS  # 角色定位: 主输出
SWITCH_PRIORITY = SwitchPriority.NORMAL  # 切换优先级: 普通
ELEMENT = Elements.ICE  # 角色属性: 湮灭
RESONANCE_CHAIN = 0  # 共鸣链等级 (0-6)
_auto_mode_logged = False  # 自动模式提示是否已输出 (避免重复刷屏) 

# ==== 动作模组 ====
# 每个动作函数返回是否成功执行 (True/False)
# 时间信息从 register_action 注册的数据中获取

def _action_a(task):
    """
    普通攻击连击
    """
    continuous_click(task, 0.2)
    return True
register_action(CHARACTER_NAME, "a")  # 注册普通攻击

def _action_aa(task):
    """
    普通攻击连击
    """
    continuous_click(task, 0.6)
    return True
register_action(CHARACTER_NAME, "aa")  # 注册普通攻击


def _action_e(task):
    while task.enabled and task._combat_active:
        if not check_skill_available(task, "e"):
            break
        task.send_key("e")
        time.sleep(0.05)
    # time.sleep(0.1)    
    return True
register_action(CHARACTER_NAME, "e")  # 注册 e 技能

def _action_ea(task):
    """
    e 技能接攻击
    """
    _action_e(task)
    continuous_click(task, 1.5)
    return True
register_action(CHARACTER_NAME, "ea")  # 注册 e 技能接攻击

def feixue_x(task):
    while task.enabled and task._combat_active:
        if check_skill_available(task, "a", skill_image="feixue_x_prepare"):    
        # if not check_skill_available(task, "a",white_threshold=0, skill_image="feixue_x_prepare"):
            task.mouse_down(key="right")
            break
        time.sleep(0.05)    
    while task.enabled and task._combat_active:
        if check_skill_available(task, "sa", skill_image="feixue_x"):    
        # if not check_skill_available(task, "a",white_threshold=0, skill_image="feixue_x_prepare"):
            task.mouse_up(key="right")
            break
        time.sleep(0.05)
    time.sleep(0.15)    
    while task.enabled and task._combat_active:
        if check_skill_available(task, "sa", skill_image="feixue_x"):
            break
        time.sleep(0.01)
    while task.enabled and task._combat_active:
        if not check_skill_available(task, "sa", skill_image="feixue_x"):
            break
        task.click()  
        time.sleep(0.06)

def _action_zr1(task):
    continuous_click(task, 0.65)
    task.mouse_down()  # 按住鼠标左键
    task.right_click(after_sleep=0.4)
    while task.enabled and task._combat_active:
        if check_skill_available_by_color(task, "feixue_r1",color={'r': (170, 170), 'g': (249, 249), 'b': (255, 255)},color_threshold=0.3):
            time.sleep(0.01)
            break
    while task.enabled and task._combat_active:
        if not check_skill_available_by_color(task, "feixue_r1",color={'r': (170, 170), 'g': (249, 249), 'b': (255, 255)},color_threshold=0.3):
            break      
        time.sleep(0.01)  
    task.mouse_up()  # 释放鼠标左键    
    time.sleep(0.05)    
    task.send_key("q")
    while task.enabled and task._combat_active:
        if check_skill_available(task, "r",skill_image="feixue_r1"):  # 检测 r 区域
            break 
        time.sleep(0.05)
    # while task.enabled and task._combat_active:
    #     if not check_skill_available(task, "r",skill_image="feixue_r1"):  # 检测 r 区域
    #         break
    #     task.send_key("r") 
        # time.sleep(0.05) 
    # time.sleep(1.0)
    continuous_send_key(task, "r",2)
    # task.mouse_down()
    while task.enabled and task._combat_active:
        if detect_self_on_field(task, CHARACTER_NAME):
            break
        time.sleep(0.05)    
    continuous_click(task, 1.2)

    # 查找自己的槽位 (用于计数)
    slot = None
    for s, name in task._detected_characters.items():
        if name == CHARACTER_NAME:
            slot = s
            break
    
    # 第 5 次调用时跳过 right_click 和 continuous_click
    skip_lines = False
    if slot is not None:
        states = task._char_data[slot].setdefault('states', {})
        count_key = "zr1_count"
        current_count = states.get(count_key, 0) + 1
        states[count_key] = current_count
        if current_count == 5:
            skip_lines = True
            states[count_key] = 0  # 重置计数器
    
    if not skip_lines:
        task.right_click(after_sleep=0.4)
        continuous_click(task, 0.1)
    return True
register_action(CHARACTER_NAME, "zr1")  # 注册 zr1 (蓄力+r1)

def _action_main(task):
    # 查找自己的槽位
    slot = None
    for s, name in task._detected_characters.items():
        if name == CHARACTER_NAME:
            slot = s
            break
    
    if slot is not None:
        states = task._char_data[slot].setdefault('states', {})  # 获取自定义状态
        count_key = "main_count"  # 计数器键名
        current_count = states.get(count_key, 0) + 1  # 计数+1
        states[count_key] = current_count  # 更新计数器
        
        # 第 5 次执行 main_3z, 其余执行 main_4z
        if current_count == 5:
            action_success = _action_main_3z(task)
            states[count_key] = 0  # 重置计数器
        else:
            action_success = _action_main_4z(task)
    else:
        action_success = _action_main_4z(task)  # 找不到槽位时默认执行 main_4z
    
    return action_success
register_action(CHARACTER_NAME, "main")

def _action_main_4z(task):
    """
    飞雪主连招动作
    """
    branch_parts = []  # 记录各分支标识, 最后统一返回
    # 步骤1: 按住鼠标左键直到 check_skill_available 识别 "r" 区域返回是
    # _action_zr1(task)

    # a123
    # continuous_click(task, 1.2)
    continuous_click(task, 0.8)
    
    # send_a_num_by_con(task,slot,4)
    # time.sleep(0.2)

    # a123
    # continuous_click(task, 1.2)
    # --x跳e--
    feixue_x(task)   
    time.sleep(0.05)     
    task.send_key("space")
    time.sleep(0.05)
    task.send_key_down("e")
    while task.enabled and task._combat_active:
        if check_skill_available(task, "sa", skill_image="feixue_x"):
            task.send_key_up("e")
            break  
        time.sleep(0.01)
    time.sleep(0.35)    
    while task.enabled and task._combat_active:
        if not check_skill_available(task, "sa", skill_image="feixue_x"):
            break
        task.click()
        time.sleep(0.05)
    # --x--
    time.sleep(0.05)
    # 步骤13: 预留处决函数位置
    if not f_execute(task,1.5):
        branch_parts.append("no_execute")  # 处决失败
        # continuous_click(task, 1.2)
        # task.right_click(after_sleep=0.5)
        # continuous_click(task, 1.2)
        # feixue_x(task)
        # time.sleep(0.05)
        # task.send_key("space")
        # time.sleep(0.01)
        time.sleep(0.3)
        continuous_click(task, 1.05)
        task.mouse_down()
        time.sleep(0.5)
        task.mouse_up()
        # time.sleep(0.3)
        continuous_click(task, 0.9)
    else:
        branch_parts.append("execute")  # 处决成功
        continuous_click(task, 0.3)
        task.right_click(after_sleep=0.4)
        continuous_click(task, 1.2)
        
    feixue_x(task)
    time.sleep(0.05)
    task.send_key("space")
    time.sleep(0.05)
    # a123
    # --x跳e--
    while task.enabled and task._combat_active:
        if not check_skill_available(task, "e"):
            break
        task.send_key("e")
        time.sleep(0.01)
    task.send_key_down("e")
    while task.enabled and task._combat_active:
        if check_skill_available(task, "sa", skill_image="feixue_x"):
            task.send_key_up("e")
            time.sleep(0.01)
            task.click()
            break 
        time.sleep(0.01)
    # --x--z--
    if check_skill_available(task, "feixue_x5", skill_image="feixue_x5_location"):
        branch_parts.append("with_x5")  # x5 技能可用
        while task.enabled and task._combat_active:
            if not check_skill_available(task, "feixue_x5", skill_image="feixue_x5_location"):
                continuous_click(task, 0.35)
                task.mouse_down()
                time.sleep(0.4)
                break
            task.click()
            time.sleep(0.05)
    else:
        branch_parts.append("no_x5")  # x5 技能不可用
        continuous_click(task, 0.25)
        task.mouse_down()
        time.sleep(0.3)    # -0.2
    task.send_key("space")
    time.sleep(0.05)
    while task.enabled and task._combat_active:
        if not check_skill_available_by_color(task, "feixue_r1",color={'r': (252, 252), 'g': (228, 228), 'b': (255, 255)},color_threshold=0.3):
            break
        time.sleep(0.01)
    time.sleep(0.05)    
    task.mouse_up()
    while task.enabled and task._combat_active:
        if check_skill_available(task, "r",white_threshold=0.01):
            break
        time.sleep(0.01)        
    # --r--
    task.send_key_down("r")
    time.sleep(1)
    while task.enabled and task._combat_active:
        if not check_skill_available(task, "r",white_threshold=0.01):
            break
        time.sleep(0.01)
    task.send_key_up("r")
    branch_id = "_".join(branch_parts) if branch_parts else "default"  # 组合分支标识
    return True, branch_id
register_action(CHARACTER_NAME, "main_4z")  # 注册主连招

def _action_main_3z(task):
    # continuous_click(task, 1.2)
    continuous_click(task, 0.8)
    # task.right_click(after_sleep=0.4)
    # continuous_click(task, 1.2)  
    feixue_x(task)

    while task.enabled and task._combat_active:
        if not check_skill_available(task, "e"):
            break
        task.send_key("e")
        time.sleep(0.01)
    task.send_key_down("e")
    while task.enabled and task._combat_active:
        if check_skill_available(task, "sa", skill_image="feixue_x"):
            task.send_key_up("e")
            time.sleep(0.01)
            task.click()
            break 
        time.sleep(0.01)
    # --x--z--
    continuous_click(task, 0.25)
    task.mouse_down()
    time.sleep(0.3)    
    task.send_key("space")
    time.sleep(0.05)
    while task.enabled and task._combat_active:
        if not check_skill_available_by_color(task, "feixue_r1",color={'r': (252, 252), 'g': (228, 228), 'b': (255, 255)},color_threshold=0.3):
            break
        time.sleep(0.01)
    time.sleep(0.05)    
    task.mouse_up()
    while task.enabled and task._combat_active:
        if check_skill_available(task, "r",white_threshold=0.01):
            break
        time.sleep(0.01)        
    # --r--
    task.send_key_down("r")
    time.sleep(1)
    while task.enabled and task._combat_active:
        if not check_skill_available(task, "r",white_threshold=0.01):
            break
        time.sleep(0.01)
    task.send_key_up("r")   
    return True
register_action(CHARACTER_NAME, "main_3z")  # 注册 main_3z 动作

def _check_special_skill(task):  # 检测协奏值是否已满 (特殊技能是否可以释放)
    """
    通过 task.is_con_full() 检测当前角色的协奏值是否已满。
    协奏值满 (get_current_con == 1) 对应特殊技能就绪。
    """
    hotkey = None  # 当前角色槽位
    for slot, name in task._detected_characters.items():  # 查找自己的槽位
        if name == CHARACTER_NAME:  # 找到自己的槽位
            hotkey = slot  # 记录槽位编号
            break
    if hotkey is None:  # 未找到自己的槽位
        return False  # 无法检测
    return task.is_con_full(hotkey)  # 检查协奏值是否已满 (内部已调用 next_frame)


def _action_skill_coordination(task):  # 特殊技能-变奏: 新登场角色触发的变奏动作
    """
    被特殊技能强制切换上场后执行的变奏动作。
    触发时清空残留的 end_time, 打断上个动作 (强制置为已完成)。
    """
    task._character_jumping = True
    continuous_click(task, 1.1)
    return True
register_action(CHARACTER_NAME, "skill_coordination", force_clear=True)  # 注册变奏动作

def run(task):  # 脚本入口函数, 由 CharacterAutoTask 在子线程中调用
    global SWITCH_PRIORITY, _auto_mode_logged  # 声明修改模块级变量
    SWITCH_PRIORITY = SwitchPriority.NORMAL  # 每次战斗开始时重置自己的切换优先级
    _auto_mode_logged = False  # 重置自动模式提示标记
    task.log_info(f"{CHARACTER_NAME} 战斗脚本开始执行")  # 输出启动日志

    hotkey = None  # 当前角色对应的槽位编号, 初始为空
    for slot, name in task._detected_characters.items():  # 从 task 的识别结果中查找自己
        if name == CHARACTER_NAME or task._detected_characters[slot] == CHARACTER_NAME:  # 找到自己的槽位
            hotkey = str(slot)  # 槽位编号转为字符串
            break
    if not hotkey:  # 未在识别结果中找到自己
        task.log_warning(f"{CHARACTER_NAME} 未在识别结果中找到, 无法执行脚本")
        return  # 退出脚本
    task.info_set("按键", hotkey)  # 在任务信息面板显示检测到的按键

    slot = int(hotkey)  # 槽位编号 (int), 用于访问 _char_data

    while task.enabled and task._combat_active:  # 任务启用且战斗激活时才循环
        wait_for_my_turn(task, hotkey, CHARACTER_NAME)  # 等待 task 唤醒 (握手同步)

        attack_counts = task._char_data[slot]['attack_counts']  # 获取当前角色的攻击计数数组
        action_success = False  # 动作是否成功执行

        # 检查是否有轴命令 (打轴模式)
        axis_action = get_axis_command(task, CHARACTER_NAME)  # 获取并清除轴命令
        if axis_action:  # 有轴命令
            task.log_info(f"{CHARACTER_NAME} 收到轴命令: {axis_action}")
            if axis_action == "aa":  # 普通攻击
                action_success = _action_aa(task)
            elif axis_action == "a":  # 短普攻
                action_success = _action_a(task)
            elif axis_action == "e":  # e 技能
                action_success = _action_e(task)
            elif axis_action == "ea":  # e 技能接攻击
                action_success = _action_ea(task)
            elif axis_action == "main_3z":  # main_3z
                action_success = _action_main_3z(task)
            elif axis_action == "main_4z":  # main_4z
                action_success = _action_main_4z(task)
            elif axis_action == "zr1":  # 蓄力+r1
                action_success = _action_zr1(task)
            elif axis_action == "main":  # 主连招
                action_success = _action_main(task)
            elif axis_action == "skill_coordination":  # 变奏
                action_success = _action_skill_coordination(task)
            else:  # 未知动作
                task.log_error(f"轴配置错误: {CHARACTER_NAME} 未知动作 {axis_action}")
            # 报告轴执行结果
            set_axis_result(task, CHARACTER_NAME, action_success)
        else:  # 无轴命令, 自动模式
            if not _auto_mode_logged:
                task.log_info(f"{CHARACTER_NAME} 暂不支持自动模式")
                _auto_mode_logged = True
            time.sleep(0.1)

            if action_success:  # 动作成功执行 (仅自动模式)
                # 检测特殊技能并切换角色
                if _check_special_skill(task):  # 识图判断特殊技能是否就绪
                    task._char_data[slot]['skill_ready'] = True  # 标记自己的特殊技能就绪
                    task.log_info(f"{CHARACTER_NAME} 特殊技能就绪, 强制切换")
                    task.schedule_next_character(force=True)  # 强制切换, 无视冷却
                else:  # 特殊技能未就绪
                    task.schedule_next_character()  # 普通切换
        
    task.log_info(f"{CHARACTER_NAME} 战斗脚本已停止")  # 输出停止日志
