import time  # 导入时间模块, 用 time.sleep 代替 task.sleep (子线程中 task.sleep 可能不安全)
from src.character import *  # 导入所有共享工具函数和枚举
CHARACTER_NAME = "qianxiao"  # 角色名, 对应 COCO 标注中的 category 后缀
CHAR_TYPE = CharType.SUB_DPS  # 角色定位: 主输出
SWITCH_PRIORITY = SwitchPriority.NORMAL  # 切换优先级: 普通
ELEMENT = Elements.HAVOC  # 角色属性: 衍射 (对应协奏值环颜色索引 0)
RESONANCE_CHAIN = 0  # 共鸣链等级 (0-6)


def combat_template(task):  # 战斗模板: 按固定流程执行一套战斗操作
    """
    战斗流程:
    1. 等待 "a_location" 区域白色占比达到 10%
    2. 持续循环点击鼠标左键 0.5 秒
    3. 按住鼠标左键 5 秒
    4. 等待 "a_location" 中出现图片 "character1"
    5. 点击按键 "3"
    """
    task.log_info("开始执行战斗模板")  # 记录战斗模板开始

    # 步骤1: 等待 "a_location" 中白色 (255,255,255) 占比达到 0.10
    color = {'b': (255, 255), 'g': (255, 255), 'r': (255, 255)}  # RGB 白色, 函数内部按 BGR 顺序传参
    box = get_location_box(task, "a_location")  # 获取 "a_location" 特征的预定义位置
    while task.enabled and task._combat_active:  # 任务启用且战斗激活时持续检测
        task.next_frame()  # 获取新的屏幕帧
        percentage = task.calculate_color_percentage(color, box)  # 计算该区域内白色像素占比
        if percentage >= 0.10:  # 占比达到 10% 阈值, 满足条件退出等待
            break
        time.sleep(0.05)  # 每 50ms 检测一次, 子线程中用 time.sleep

    # 步骤2: 持续循环点击鼠标左键, 持续 0.5 秒
    continuous_click(task, 0.5, check_active=False)  # 调用封装函数, 不检查任务状态

    # 步骤3: 按住鼠标左键 5 秒
    task.mouse_down()  # 按下鼠标左键 (不释放)
    time.sleep(5)  # 保持按住状态 5 秒
    task.mouse_up()  # 释放鼠标左键

    # 步骤4: 等待 "a_location" 区域中出现图片 "character1"
    task.wait_feature("character1", box="a_location")  # 循环截帧直到在 a_location 内匹配到 character1 图片

    # 步骤5: 点击按键 "3"
    task.send_key("3")  # 模拟按下并释放键盘按键 3

    task.log_info("战斗模板执行完成")  # 记录战斗模板结束


# ==== 动作模组 ====
# 每个动作函数返回是否成功执行 (True/False)
# 时间信息从 register_action 注册的数据中获取

def _action_ea3(task):
    task.send_key("e")
    while task.enabled and task._combat_active:
        if not check_skill_available(task, "e"):
            break
        task.send_key("e")
        time.sleep(0.01)
    continuous_click(task, 0.3)
    return True
register_action(CHARACTER_NAME, "ea3")  # 注册动作 ea3

def _action_a4(task):
    while task.enabled and task._combat_active:
        if check_skill_available(task, "a",skill_image="qianxiao_a4"):
            break
        task.click()
        time.sleep(0.07)    
    continuous_click(task, 0.3)
    return True
register_action(CHARACTER_NAME, "a4")  # 注册动作 a4

def _action_short_a4(task):  
    while task.enabled and task._combat_active:
        if check_skill_available(task, "a",skill_image="qianxiao_a4"):
            break
        task.click()
        time.sleep(0.05) 
    continuous_click(task, 0.1)
    return True
register_action(CHARACTER_NAME, "short_a4")  # 注册动作 a4

def _action_z(task):
    continuous_click(task, 0.2)
    return True
register_action(CHARACTER_NAME, "z")

def _action_qre(task):
    # continuous_click(task, 0.25)
    while task.enabled and task._combat_active:
        if not check_skill_available(task, "r",white_threshold=0,skill_image="qianxiao_r"):
            break
        task.send_key("q")
        task.send_key("r")
        time.sleep(0.01)  
    time.sleep(3.5)      
    while task.enabled and task._combat_active:
        if check_skill_available(task, "e",white_threshold=0.01,skill_image="qianxiao_super_e"):
            break
        time.sleep(0.01)
    task.send_key("e")
    time.sleep(0.05)    
    while task.enabled and task._combat_active:
        if not check_skill_available(task, "e",white_threshold=0.01,skill_image="qianxiao_super_e"):
            break
        task.send_key("e")
        time.sleep(0.05)
    return True
register_action(CHARACTER_NAME, "qre", force_clear=True)

def _action_super_z2a3(task):
    task.mouse_down()
    time.sleep(1.05)
    continuous_click(task, 0.1)
    return True
register_action(CHARACTER_NAME, "super_z2a3")

def _action_super_a4(task):
    while task.enabled and task._combat_active:
        if _check_special_skill(task):
            break
        task.click()
        time.sleep(0.07)
    return True
register_action(CHARACTER_NAME, "super_a4")

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
    continuous_click(task, 0.7)
    return True

register_action(CHARACTER_NAME, "skill_coordination", force_clear=True) 

# ==== 动作注册 (模块加载时自动注册) ====
 # 注册变奏动作



def run(task):  # 脚本入口函数, 由 CharacterAutoTask 在子线程中调用
    global SWITCH_PRIORITY  # 声明修改模块级变量
    SWITCH_PRIORITY = SwitchPriority.NORMAL  # 每次战斗开始时重置自己的切换优先级
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
            if axis_action == "ea3":  # 轴命令执行 ea3
                action_success = _action_ea3(task)
            elif axis_action == "a4":  # 轴命令执行 a4
                action_success = _action_a4(task)
            elif axis_action == "short_a4":  # 轴命令执行 a4
                action_success = _action_short_a4(task)
            elif axis_action == "z":  # 轴命令执行 z
                action_success = _action_z(task)
            elif axis_action == "qre":  # 轴命令执行 qre
                action_success = _action_qre(task)
            elif axis_action == "super_z2a3":  # 轴命令执行 super_z2a3
                action_success = _action_super_z2a3(task)
            elif axis_action == "super_a4":  # 轴命令执行 super_a4
                action_success = _action_super_a4(task)
            elif axis_action == "skill_coordination":  # 轴命令执行变奏
                action_success = _action_skill_coordination(task)
            else:  # 未知动作
                task.log_error(f"轴配置错误: {CHARACTER_NAME} 未知动作 {axis_action}")
            # 报告轴执行结果
            set_axis_result(task, CHARACTER_NAME, action_success)
        else:  # 无轴命令, 自动模式
            if attack_counts[0] == 0:
                action_success = _action_ea3(task)
            elif attack_counts[0] == 3:
                action_success = _action_a4(task)
            time.sleep(0.01)

            if action_success:  # 动作成功执行 (仅自动模式)
                # 检测特殊技能并切换角色
                if _check_special_skill(task):  # 识图判断特殊技能是否就绪
                    task._char_data[slot]['skill_ready'] = True  # 标记自己的特殊技能就绪
                    task.log_info(f"{CHARACTER_NAME} 特殊技能就绪, 强制切换")
                    task.schedule_next_character(force=True)  # 强制切换, 无视冷却
                else:  # 特殊技能未就绪
                    task.schedule_next_character()  # 普通切换

    
    task.log_info(f"{CHARACTER_NAME} 战斗脚本已停止")  # 输出停止日志
