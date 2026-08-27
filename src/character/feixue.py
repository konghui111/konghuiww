import time  # 导入时间模块, 用 time.sleep 代替 task.sleep (子线程中 task.sleep 可能不安全)
from src.character import get_location_box, wait_for_my_turn, continuous_click, register_action, CharType, SwitchPriority, Elements  # 导入共享工具函数和枚举
from src.character import get_axis_command, set_axis_result  # 导入轴命令机制函数
from src.character import freeze_time, find_sub_dps_slot, check_skill_available,f_execute,send_a_num_by_con  # 导入时停、查找副输出、技能检测
from src.character import check_skill_available_by_color
CHARACTER_NAME = "feixue"  # 角色名, 对应 COCO 标注中的 category 后缀
CHAR_TYPE = CharType.MAIN_DPS  # 角色定位: 主输出
SWITCH_PRIORITY = SwitchPriority.NORMAL  # 切换优先级: 普通
ELEMENT = Elements.ICE  # 角色属性: 湮灭
RESONANCE_CHAIN = 0  # 共鸣链等级 (0-6)
_auto_mode_logged = False  # 自动模式提示是否已输出 (避免重复刷屏) 

# ==== 动作模组 ====
# 每个动作函数返回是否成功执行 (True/False)
# 时间信息从 register_action 注册的数据中获取

def _action_aa(task):
    """
    普通攻击连击
    """
    continuous_click(task, 0.45)
    return True
register_action(CHARACTER_NAME, "aa")  # 注册普通攻击

def _action_ea(task):
    """
    e 技能接攻击
    """
    while task.enabled and task._combat_active:
        if not check_skill_available(task, "e"):
            break
        task.send_key("e")
        time.sleep(0.01)
    continuous_click(task, 1.5)
    return True
register_action(CHARACTER_NAME, "ea")  # 注册 e 技能接攻击

def feixue_x(task):
    task.mouse_down(key="right")
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

def _action_main(task,slot):
    """
    飞雪主连招动作
    """
    branch_parts = []  # 记录各分支标识, 最后统一返回
    # 步骤1: 按住鼠标左键直到 check_skill_available 识别 "r" 区域返回是
    task.mouse_down()  # 按住鼠标左键
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
    while task.enabled and task._combat_active:
        if not check_skill_available(task, "r",skill_image="feixue_r1"):  # 检测 r 区域
            break
        task.send_key("r") 
        time.sleep(0.05) 
    time.sleep(1.0)
    while task.enabled and task._combat_active:
        if check_skill_available(task, "e"):
            break
        time.sleep(0.01)

    # a123
    continuous_click(task, 1.2)
    task.right_click(after_sleep=0.5)
    # send_a_num_by_con(task,slot,4)
    # time.sleep(0.2)

    # a123
    continuous_click(task, 1.2)
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
    if not f_execute(task,1.6):
        branch_parts.append("no_execute")  # 处决失败
        # continuous_click(task, 1.2)
        # task.right_click(after_sleep=0.5)
        # continuous_click(task, 1.2)
        # feixue_x(task)
        # time.sleep(0.05)
        # task.send_key("space")
        # time.sleep(0.01)
    else:
        branch_parts.append("execute")  # 处决成功
        continuous_click(task, 0.3)
        task.right_click(after_sleep=0.5)
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
    branch_id = "_".join(branch_parts) if branch_parts else "default"  # 组合分支标识
    return True, branch_id
register_action(CHARACTER_NAME, "main")  # 注册主连招

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
    continuous_click(task, 1.35)
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
            elif axis_action == "ea":  # e 技能接攻击
                action_success = _action_ea(task)
            elif axis_action == "main":  # 主连招
                action_success = _action_main(task,slot)
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

        if action_success:  # 动作成功执行
            # 自动模式下: 检测特殊技能并切换角色 (打轴模式由 task 控制切换, 不执行此逻辑)
            if task.config.get("战斗模式", "自动") != "打轴":
                if _check_special_skill(task):  # 识图判断特殊技能是否就绪
                    task._char_data[slot]['skill_ready'] = True  # 标记自己的特殊技能就绪
                    task.log_info(f"{CHARACTER_NAME} 特殊技能就绪, 强制切换")
                    task.schedule_next_character(force=True)  # 强制切换, 无视冷却
                else:  # 特殊技能未就绪
                    task.schedule_next_character()  # 普通切换
        
    task.log_info(f"{CHARACTER_NAME} 战斗脚本已停止")  # 输出停止日志
