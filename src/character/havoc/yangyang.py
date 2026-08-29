import time  # 导入时间模块, 用 time.sleep 代替 task.sleep (子线程中 task.sleep 可能不安全)
from src.character import *  # 导入所有共享工具函数和枚举
CHARACTER_NAME = "yangyang"  # 角色名, 对应 COCO 标注中的 category 后缀
CHAR_TYPE = CharType.MAIN_DPS  # 角色定位: 主输出
SWITCH_PRIORITY = SwitchPriority.NORMAL  # 切换优先级: 普通
DUAL_SKILL = True  # 是否双重技能 (仅 MAIN_DPS 类型角色有此属性)
ELEMENT = Elements.HAVOC  # 角色属性: 湮灭
RESONANCE_CHAIN = 0  # 共鸣链等级 (0-6)
_auto_mode_logged = False  # 自动模式提示是否已输出 (避免重复刷屏) 


# ==== 动作模组 ====
# 每个动作函数返回是否成功执行 (True/False)
# 时间信息从 register_action 注册的数据中获取

WHITE = {'b': (255, 255), 'g': (255, 255), 'r': (255, 255)}  # 白色 RGB 颜色范围, 函数内部按 BGR 顺序传参


def _action_aaaa(task):
    continuous_click(task, 3)
    return True
register_action(CHARACTER_NAME, "aaaa")  # 注册动作 aaaa

def _action_c_a1(task):
    task.click()
    return True
register_action(CHARACTER_NAME, "c_a1")  # 注册动作 c_a1

#只有启动用
def _action_c_a12(task):
    continuous_click(task, 0.2)
    return True
register_action(CHARACTER_NAME, "c_a12")  # 注册动作 c_a12 (只有启动用)

def _action_w_e_c_a2(task):
    task.send_key_down("w")
    # e等到苍a出现
    while task.enabled and task._combat_active: 
        if check_skill_available(task, "a",skill_image="yangyang_c_a"): 
            break
        task.send_key("e")
        time.sleep(0.01)    
    task.send_key_up("w")
    continuous_click(task, 0.25)
    return True
register_action(CHARACTER_NAME, "w_e_c_a2")  # 注册动作 w_e_c_a2

#只有启动用
def _action_c_a3e(task):
    continuous_click(task, 0.2)
    while task.enabled and task._combat_active: 
        if check_skill_available(task, "e",skill_image="yangyang_c_e"):
            break
        # task.click()
        time.sleep(0.01)
    task.send_key("e")
    return True
register_action(CHARACTER_NAME, "c_a3e")  # 注册动作 c_a3e (只有启动用)

#只有循环用
def _action_c_a34(task):
    continuous_click(task, 0.95)
    return True
register_action(CHARACTER_NAME, "c_a34")  # 注册动作 c_a34 (只有循环用)

#只有循环用
def _action_c_e(task):
    while task.enabled and task._combat_active: 
        if check_skill_available(task, "e",skill_image="yangyang_c_spuer_e"):
            break
        task.click()
        time.sleep(0.05) 
    while task.enabled and task._combat_active: 
        if not check_skill_available(task, "e",skill_image="yangyang_c_spuer_e"): 
            break
        task.send_key("e")
        time.sleep(0.1)
    return True
register_action(CHARACTER_NAME, "c_e")  # 注册动作 c_e (只有循环用)

def _action_c_z(task):
    task.mouse_down()
    while task.enabled and task._combat_active:
        if check_skill_available(task, "a",skill_image="yangyang_c_a"): 
            break
        time.sleep(0.02)
    time.sleep(1.1)
    return True
register_action(CHARACTER_NAME, "c_z")  # 注册动作 c_z

def _action_y_a12(task):
    continuous_click(task, 0.8)
    return True
register_action(CHARACTER_NAME, "y_a12")  # 注册动作 y_a12

def _action_y_a34(task):
    continuous_click(task, 0.9)
    return True
register_action(CHARACTER_NAME, "y_a34")  # 注册动作 y_a34


def _action_y_z1(task):
    # add buff
    task.mouse_down()
    time.sleep(1.4)
    task.mouse_up()
    return True
register_action(CHARACTER_NAME, "y_z1")  # 注册动作 y_z1

def _action_y_e(task):
    while task.enabled and task._combat_active: 
        if check_skill_available(task, "e",skill_image="yangyang_y_spuer_e"): 
            break
        # task.click()
        time.sleep(0.05) 
    while task.enabled and task._combat_active: 
        if not check_skill_available(task, "e",skill_image="yangyang_y_spuer_e"): 
            break
        task.send_key("e")
        time.sleep(0.1)
    return True
register_action(CHARACTER_NAME, "y_e")  # 注册动作 y_e

def _action_qr(task):
    # 需要识图
    task.send_key("q")
    task.send_key("r")
    freeze_time(task, 4.7)
    # 步骤7: 等待 4 秒
    time.sleep(4.6)
    while task.enabled and task._combat_active:
        if check_skill_available(task, "a",skill_image="yangyang_c_a"): 
            break
        time.sleep(0.05)
    return True
register_action(CHARACTER_NAME, "qr")  # 注册动作 qr

def _action_y_z(task):
    task.mouse_down()
    time.sleep(8.5)
    task.mouse_up()
    return True
register_action(CHARACTER_NAME, "y_z")  # 注册动作 y_z


def _action_main(task):
    _action_y_e(task)
    _action_c_z(task)
    _action_qr(task)
    _action_c_e(task)
    _action_y_z(task)
    return True
register_action(CHARACTER_NAME, "main")  # 注册动作 main

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
    time.sleep(0.7)
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
            if axis_action == "aaaa":  # 普攻
                action_success = _action_aaaa(task)
            elif axis_action == "c_a1":  # 苍色a1
                action_success = _action_c_a1(task)
            elif axis_action == "c_a12":  # 苍色a12 (启动用)
                action_success = _action_c_a12(task)
            elif axis_action == "w_e_c_a2":  # w+e+苍色a2
                action_success = _action_w_e_c_a2(task)
            elif axis_action == "c_a3e":  # 苍色a3e (启动用)
                action_success = _action_c_a3e(task)
            elif axis_action == "c_a34":  # 苍色a34 (循环用)
                action_success = _action_c_a34(task)
            elif axis_action == "c_e":  # 苍色e (循环用)
                action_success = _action_c_e(task)
            elif axis_action == "c_z":  # 苍色z
                action_success = _action_c_z(task)
            elif axis_action == "y_a12":  # 秧秧a12
                action_success = _action_y_a12(task)
            elif axis_action == "y_a34":  # 秧秧a34
                action_success = _action_y_a34(task)
            elif axis_action == "y_z1":  # 秧秧z1 (buff)
                action_success = _action_y_z1(task)
            elif axis_action == "y_e":  # 秧秧e
                action_success = _action_y_e(task)
            elif axis_action == "qr":  # q+r 变奏
                action_success = _action_qr(task)
            elif axis_action == "y_z":  # 秧秧z
                action_success = _action_y_z(task)
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
