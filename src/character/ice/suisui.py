import time  # 导入时间模块, 用 time.sleep 代替 task.sleep (子线程中 task.sleep 可能不安全)
from src.character import *  # 导入所有共享工具函数和枚举
CHARACTER_NAME = "suisui"  # 角色名, 对应 COCO 标注中的 category 后缀
CHAR_TYPE = CharType.HEALER  # 角色定位: 主输出
SWITCH_PRIORITY = SwitchPriority.NORMAL  # 切换优先级: 普通
ELEMENT = Elements.ICE  # 角色属性: 湮灭
RESONANCE_CHAIN = 0  # 共鸣链等级 (0-6)
_auto_mode_logged = False  # 自动模式提示是否已输出 (避免重复刷屏) 


# ==== 动作模组 ====
# 每个动作函数返回是否成功执行 (True/False)
# 时间信息从 register_action 注册的数据中获取

WHITE = {'b': (255, 255), 'g': (255, 255), 'r': (255, 255)}  # 白色 RGB 颜色范围, 函数内部按 BGR 顺序传参


def _action_aaaa(task):
    continuous_click(task, 0.6)
    return True
register_action(CHARACTER_NAME, "aaaa")  # 注册动作 aaaa

def _action_normal_a23(task):
    continuous_click(task, 0.75)
    slot = int(task._character_slots[CHARACTER_NAME])
    task._char_data[slot]['attack_counts'][0] = 4
    return True
register_action(CHARACTER_NAME, "normal_a23")  # 注册普通连击

def _action_super_a12(task):
    continuous_click(task, 0.5)
    slot = int(task._character_slots[CHARACTER_NAME])
    task._char_data[slot]['attack_counts'][1] = 3
    return True
register_action(CHARACTER_NAME, "super_a12")  # 注册强化连击

def _action_a4e(task):
    """
    1. 点击鼠标左键直到 check_skill_available 识图 "suisui_spuer_e" 成功
    2. 点击按键 e 直到 check_skill_available 识图 "suisui_spuer_e" 失败
    3. 成功后进入 5 秒强化状态
    """
    slot = int(task._character_slots[CHARACTER_NAME])
    # 阶段1: 点击鼠标左键直到技能图标出现
    while task.enabled and task._combat_active:
        if check_skill_available(task, "e", skill_image="suisui_spuer_e"):
            break
        task.click()
        time.sleep(0.07)
    # 阶段2: 点击按键 e 直到技能图标消失
    while task.enabled and task._combat_active:
        if not check_skill_available(task, "e", skill_image="suisui_spuer_e"):
            break
        task.send_key("e")
        time.sleep(0.02)
    # 阶段3: 强化状态 5 秒
    task._char_data[slot]['states']['e_buff_time'] = time.time() + 8.0
    return True
register_action(CHARACTER_NAME, "a4e")  # 注册技能 (带强化)

def _action_ea4qr(task):
    """
    1. 持续按 e 直到 check_skill_available 识别失败
    2. 等待 900ms
    3. continuous_click 持续点击鼠标左键 850ms
    4. 点击 q
    5. 点击 r
    6. freeze_time 加上 4.3s 延迟
    7. 等待 4 秒
    8. _check_special_skill 等待协奏值满
    """
    # 步骤1: 持续按 e 直到技能图标消失
    while task.enabled and task._combat_active:
        if not check_skill_available(task, "e", skill_image="suisui_norm_e"):
            break
        task.send_key("e")
        time.sleep(0.05)
    # 步骤2: 等待 900ms
    time.sleep(0.9)
    # 步骤3: 持续点击鼠标左键 850ms
    continuous_click(task, 0.85)
    # 步骤4: 点击 q
    while task.enabled and task._combat_active:  
        if check_skill_available(task, "r",skill_image="suisui_r"):
            break
        task.click()
        time.sleep(0.05)   
    task.send_key("q")     
    while task.enabled and task._combat_active:  
        if not check_skill_available(task, "r",skill_image="suisui_r"):
            break
        task.send_key("r")
        time.sleep(0.05)    
    # 步骤5: 点击 r
    # task.send_key("r")
    # 步骤6: 时停 4.3s
    freeze_time(task, 4.3)
    # 步骤7: 等待 4 秒
    time.sleep(4.2)
    while task.enabled and task._combat_active:
        if detect_self_on_field(task, CHARACTER_NAME):
            break
        time.sleep(0.05)
    # 步骤8: 等待协奏值满
    # while task.enabled and task._combat_active:
    #     if _check_special_skill(task):
    #         break
    #     time.sleep(0.01)
    return True
register_action(CHARACTER_NAME, "ea4qr")  # 注册终结技


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


def _action_skill_coordination_z(task):  # 特殊技能-变奏: 新登场角色触发的变奏动作
    """
    被特殊技能强制切换上场后执行的变奏动作。
    首次释放时设置 buff noa12, 后续释放时检测 buff 存在则执行短版动作。
    """
    slot = int(task._character_slots[CHARACTER_NAME])
    task._char_data[slot]['states']['e_buff_time'] = time.time() + 8.0
    task._character_jumping = True
    states = task._char_data[slot]['states']  # 获取自定义状态
    if states.get('noa12', 0):  # buff 已存在, 执行短版动作
        continuous_click(task, 0.8)
    else:  # 首次释放, 设置 buff 并执行完整动作
        states['noa12'] = 1
        continuous_click(task, 1.4)
        # task.click()
    return True
register_action(CHARACTER_NAME, "skill_coordination_z", force_clear=True)  # 注册变奏动作

def _action_skill_coordination(task):  # 特殊技能-变奏: 新登场角色触发的变奏动作
    """
    被特殊技能强制切换上场后执行的变奏动作。
    触发时清空残留的 end_time, 打断上个动作 (强制置为已完成)。
    """
    slot = int(task._character_slots[CHARACTER_NAME])
    task._char_data[slot]['states']['e_buff_time'] = time.time() + 8.0
    continuous_click(task, 1.4)
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
            if axis_action == "aaaa":  # 轴命令执行 aaaa
                action_success = _action_aaaa(task)
            elif axis_action == "normal_a23":  # 普通连击
                action_success = _action_normal_a23(task)
            elif axis_action == "super_a12":  # 强化连击 (需要 e_buff)
                # if check_buff(task, slot, "e_buff"):  # 检查 e_buff 是否激活
                action_success = _action_super_a12(task)
                # else:
                    # task.log_error(f"轴配置错误: {CHARACTER_NAME} 执行 super_a12 需要 e_buff, 当前未激活")
            elif axis_action == "a4e":  # 技能 (带强化)
                action_success = _action_a4e(task)
            elif axis_action == "ea4qr":  # 终结技 (需要 e_buff)
                # if check_buff(task, slot, "e_buff"):  # 检查 e_buff 是否激活
                action_success = _action_ea4qr(task)
                # else:
                    # task.log_error(f"轴配置错误: {CHARACTER_NAME} 执行 ea4qr 需要 e_buff, 当前未激活")
            elif axis_action == "skill_coordination_z":  # 变奏
                action_success = _action_skill_coordination_z(task)
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
