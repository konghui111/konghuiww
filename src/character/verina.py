import time  # 导入时间模块, 用 time.sleep 代替 task.sleep (子线程中 task.sleep 可能不安全)
from src.character import get_location_box, wait_for_my_turn, continuous_click, register_action, CharType, SwitchPriority, Elements  # 导入共享工具函数和枚举
from src.character import get_axis_command, set_axis_result  # 导入轴命令机制函数
from src.character import freeze_time, find_sub_dps_slot, check_skill_available, check_buff,get_my_slot
from src.character import check_skill_available_by_color,detect_self_on_field
CHARACTER_NAME = "verina"  # 角色名, 对应 COCO 标注中的 category 后缀
CHAR_TYPE = CharType.SUB_DPS  # 角色定位: 主输出
SWITCH_PRIORITY = SwitchPriority.NORMAL  # 切换优先级: 普通
ELEMENT = Elements.SPECTRO  # 角色属性: 衍射 (对应协奏值环颜色索引 0)
RESONANCE_CHAIN = 0  # 共鸣链等级 (0-6)


def _action_main(task):
    while task.enabled and task._combat_active:  
        if check_skill_available(task, "e",skill_image="verina_e"):
            break
        time.sleep(0.05) 
    while task.enabled and task._combat_active:  
        if not check_skill_available(task, "e",skill_image="verina_e"):
            break
        task.send_key("e")
        task.send_key("q")
        time.sleep(0.05)  
    while task.enabled and task._combat_active:  
        if check_skill_available(task, "r",skill_image="verina_r"):
            break
        time.sleep(0.05) 
    while task.enabled and task._combat_active:  
        if not check_skill_available(task, "r",skill_image="verina_r"):
            break
        task.send_key("r")
        time.sleep(0.05)
    time.sleep(2)    
    while task.enabled and task._combat_active:  
        if detect_self_on_field(task, CHARACTER_NAME):
            break
        time.sleep(0.05)
    time.sleep(0.1)    
    task.send_key("space")  
    time.sleep(0.3)
    while task.enabled and task._combat_active:  
        if _check_special_skill(task):
            break
        task.click()    
        time.sleep(0.07)                                  
    return True
register_action(CHARACTER_NAME, "main")  # 注册动作 ea3



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
    continuous_click(task, 0.80)
    return True
register_action(CHARACTER_NAME, "skill_coordination", force_clear=True)  # 注册变奏动作

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
            if axis_action == "main":  # 主连招
                action_success = _action_main(task)
            elif axis_action == "skill_coordination":  # 变奏
                action_success = _action_skill_coordination(task)
            else:  # 未知动作
                task.log_error(f"轴配置错误: {CHARACTER_NAME} 未知动作 {axis_action}")
            # 报告轴执行结果
            set_axis_result(task, CHARACTER_NAME, action_success)
        else:  # 无轴命令, 自动模式
            task.log_info(f"{CHARACTER_NAME} 暂不支持自动模式")
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
