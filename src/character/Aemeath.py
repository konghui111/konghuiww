import time  # 导入时间模块, 用 time.sleep 代替 task.sleep (子线程中 task.sleep 可能不安全)
from src.character import *  # 导入所有共享工具函数和枚举

CHARACTER_NAME = "Aemeath"  # 角色名, 对应 COCO 标注中的 category 后缀
CHAR_TYPE = CharType.SUB_DPS  # 角色定位: 副输出
SWITCH_PRIORITY = SwitchPriority.NORMAL  # 切换优先级: 普通
ELEMENT = Elements.FIRE  # 角色属性: 衍射
RESONANCE_CHAIN = 0  # 共鸣链等级 (0-6)


# ==== 辅助函数 (提取重复逻辑) ====

def _helper_mecha_super_e_cycle(task):
    while task.enabled and task._combat_active:  # 等待找 e
        if check_skill_available(task, "e", skill_image="Aemeath_mecha_super_e"):
            break
        task.click()
        time.sleep(0.07)   
    # time.sleep(0.07)     
    while task.enabled and task._combat_active:  # 放 e
        task.send_key("e")
        time.sleep(0.1)
        if not check_skill_available(task, "e", skill_image="Aemeath_mecha_super_e"):
            break
        

def _helper_super_e_cycle(task):        
    while task.enabled and task._combat_active:  # 等待找 e
        if check_skill_available(task, "e", skill_image="Aemeath_super_e"):
            break
        task.click()
        time.sleep(0.07)  
    # time.sleep(0.07)    
    while task.enabled and task._combat_active:  # 放 e
        task.send_key("e")
        time.sleep(0.1)
        if not check_skill_available(task, "e", skill_image="Aemeath_super_e"):
            break
        


def _helper_r2_finish(task):
    """
    公共逻辑: 按住左键 → 等待r2出现 → 按r → 等待e消失
    被 startup 和 loop 共用。
    """
    task.mouse_down()  # 按住左键
    while task.enabled and task._combat_active:  # 等待 r2 出现
        if check_skill_available(task, "e", skill_image="mecha2Aemeath_e1"):
            break
        time.sleep(0.02)
    # time.sleep(0.1)    
    # while task.enabled and task._combat_active:  # 等待 r2 消失
    #     task.send_key("r")  # 按 r
    #     time.sleep(0.02)
    #     if not check_skill_available(task, "e", skill_image="mecha2Aemeath_e1"):
    #         break    
    continuous_send_key(task,"r", 2)
    # while task.enabled and task._combat_active:  # 等待 r2 出现
    #     if check_skill_available_binary(task, "Aemeath_r", threshold=110, white_threshold=0.1):
    #         break
    #     time.sleep(0.02)
    # # time.sleep(0.1)    
    # while task.enabled and task._combat_active:  # 等待 r2 消失
    #     task.send_key("r")  # 按 r
    #     time.sleep(0.02)
    #     if not check_skill_available_binary(task, "Aemeath_r", threshold=110, white_threshold=0.1):
    #         break    
    # while task.enabled and task._combat_active:  # 等待 r2 出现
    #     if check_skill_available(task, "r", skill_image="Aemeath_r2"):
    #         break
    #     time.sleep(0.02)
    # # time.sleep(0.1)    
    # while task.enabled and task._combat_active:  # 等待 r2 消失
    #     task.send_key("r")  # 按 r
    #     time.sleep(0.02)
    #     if not check_skill_available(task, "r", skill_image="Aemeath_r2"):
    #         break

    task.mouse_up()    

# ==== 动作函数 ====

def _action_startup(task):
    """
    启动连招:
    aa → r等待找不到r → 等待找e → 按住左键 → 等待 → 处决 → 松开左键
    → 持续按e直到找不到super_e → aaa等待找到super_e → 持续按e直到找不到super_e
    → 按住左键 → 等待r2出现 → 按r → 等待e消失
    """
    _action_a4_until_buff(task)    
    while task.enabled and task._combat_active:  # r 等待找不到 e
        task.send_key("r")
        time.sleep(0.02)
        if not check_skill_available(task, "e"):
            break
    #重击
    task.log_info(f"{CHARACTER_NAME} 重击")
    time.sleep(1)
    task.mouse_down()  # 按住鼠标左键 
    #等待界面返回
    while task.enabled and task._combat_active:  # 等待恢复
        if check_skill_available(task, "e", skill_image="mecha2Aemeath_e1"):
            break   
        time.sleep(0.02)   
    task.log_info(f"{CHARACTER_NAME} 等待重击结束")    
    box = get_location_box(task, "Aemeath_forte_location")
    # while task.enabled and task._combat_active:  # 等待二值化条件满足
    #     if box and calculate_binary_percentage(task, box, 155) >= 0.99: #0.492671
    #         break
    #     time.sleep(0.05)   
    while task.enabled and task._combat_active:  # 等待找 e
        if check_skill_available(task, "e", skill_image="Aemeath_mecha_super_e"):
            break
        time.sleep(0.05)   
    task.log_info(f"{CHARACTER_NAME} 处决")
    f_execute(task, 1.5)  # 处决  
    task.mouse_up()  # 松开左键  
    task.send_key("q")
    task.log_info(f"{CHARACTER_NAME} 机兵强化e")
    _helper_mecha_super_e_cycle(task)
    task.log_info(f"{CHARACTER_NAME} 爱弥斯强化e")
    _helper_super_e_cycle(task)  # 公共: super_e 循环
    task.log_info(f"{CHARACTER_NAME} r2")
    _helper_r2_finish(task)  # 公共: r2 收尾
    return True
register_action(CHARACTER_NAME, "startup")  # 注册启动动作

def _action_mecha_e(task):
    """
    机兵eaaae: 等待机兵e出现 → 按e → 等待机兵e消失 → 持续a一段时间 → 按e等待e消失
    """
    # 等待机兵e出现
    while task.enabled and task._combat_active:
        if check_skill_available(task, "e", skill_image="Aemeath2mecha_e1"):  # 机兵e可用
            break
        time.sleep(0.05)  # 轮询间隔
    while task.enabled and task._combat_active:
        task.send_key("e")
        time.sleep(0.05)  # 轮询间隔
        if not check_skill_available(task, "e", skill_image="Aemeath2mecha_e1"):  # 机兵e已不可用
            break
    _action_a4_until_buff(task)    
    task.send_key("e")    
    return True
register_action(CHARACTER_NAME, "mecha_e")  # 注册机兵e动作

def _action_a4_until_buff(task):
    """
    aaa: 持续普攻一段时间
    """
    while task.enabled and task._combat_active:
        if check_skill_available_by_size(task, "buff",skill_image="Aemeath_a4_buff_large",img_threshold=0.6, min_scale=0.8, max_scale=1,binary_threshold=200):  # e已不可用
        # if check_skill_available(task, "buff",skill_image="Aemeath_a4_buff",img_threshold=0.6):  # e已不可用
            break
        task.click()  # 按 e 键
        time.sleep(0.05)  # 间隔
    # time.sleep(0.1)    
    return True

register_action(CHARACTER_NAME, "a4_until_buff")  # 注册a4_until_buff

def _action_loop(task):
    """
    循环:
    aaa找到超级e → 处决 → (公共: super_e循环) → (公共: r2收尾)
    """
    _action_a4_until_buff(task)  
    f_execute(task, 1.5)  # 处决 
    while task.enabled and task._combat_active:  # r 等待找不到 r
        task.send_key("q")
        task.send_key("r")
        time.sleep(0.1)
        if not check_skill_available(task, "e"):
            break
    _helper_super_e_cycle(task)  # 公共: super_e 循环    
    _helper_mecha_super_e_cycle(task)  # 公共: super_e 循环
    _helper_r2_finish(task)  # 公共: r2 收尾
    return True
register_action(CHARACTER_NAME, "loop")  # 注册循环动作

def _action_skill_coordination(task):
    """变奏动作"""
    task._character_jumping = True  # 标记角色跳跃中
    continuous_click(task, 0.7)  # 持续点击 0.8 秒
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
            if axis_action == "startup":  # 启动连招
                action_success = _action_startup(task)
            elif axis_action == "mecha_e":  # 机兵e
                action_success = _action_mecha_e(task)
            elif axis_action == "a4_until_buff":  # aaa普攻
                action_success = _action_a4_until_buff(task)
            elif axis_action == "loop":  # 循环连招
                action_success = _action_loop(task)
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
