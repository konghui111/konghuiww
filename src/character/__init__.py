import time  # 导入时间模块, 子线程中用 time.sleep 代替 task.sleep
import cv2  # 导入 OpenCV, 用于二值化处理
import numpy as np  # 导入 numpy, 用于图像数组运算
import inspect  # 导入 inspect, 用于从调用栈获取调用者的 CHARACTER_NAME
from enum import StrEnum, IntEnum  # 导入枚举基类
from ok import Box  # 导入 Box 类, 用于构造位置区域

MAX_CHARACTERS = 3  # 最多检测的角色槽位数量


class CharType(StrEnum):  # 角色定位枚举
    MAIN_DPS = 'MainDps'  # 主输出
    SUB_DPS = 'SubDps'  # 副输出
    HEALER = 'Healer'  # 治疗者


class SwitchPriority(IntEnum):  # 切换优先级枚举, 数值越大越优先切换上场
    NO = 0  # 不切换
    LOW = 100  # 低优先级
    NORMAL = 200  # 普通优先级
    HIGH = 300  # 高优先级
    MUST = 400  # 必须切换


class Elements(IntEnum):  # 角色属性枚举, 对应协奏值能量环颜色索引
    SPECTRO = 0  # 衍射 (黄色)
    ELECTRIC = 1  # 导电 (紫色)
    FIRE = 2  # 热熔 (红色)
    ICE = 3  # 冰属性 (蓝色)
    WIND = 4  # 气动 (绿色)
    HAVOC = 5  # 湮灭 (暗色)


# ==== 动作注册 ====
# 存储所有角色的动作信息, 用于打轴模式
# 格式: {角色名: {动作名: {force_clear}}}
ACTION_REGISTRY = {}


def register_action(character_name, action_name, force_clear=False):  # 注册动作信息
    """
    注册一个动作的信息, 用于打轴模式。
    :param character_name: 角色名 (如 "qianxiao")
    :param action_name: 动作名 (如 "ea23")
    :param force_clear: 是否在执行前强制清除残留状态 (默认 False, 预留)
    """
    if character_name not in ACTION_REGISTRY:  # 角色不存在
        ACTION_REGISTRY[character_name] = {}  # 初始化角色动作字典
    ACTION_REGISTRY[character_name][action_name] = {  # 注册动作信息
        "force_clear": force_clear,  # 是否强制清除自己的 end_time
    }


def get_my_slot(task, character_name):  # 查找自己在 _detected_characters 中的槽位编号
    """
    从 task._detected_characters 中查找指定角色的槽位编号。
    :param task: 任务对象
    :param character_name: 角色名
    :return: 槽位编号 (int), 未找到返回 None
    """
    return next((s for s, n in task._detected_characters.items() if n == character_name), None)


def get_character_actions(character_name):  # 获取角色的所有动作信息
    """
    获取指定角色的所有已注册动作。
    :param character_name: 角色名
    :return: 动作字典 {动作名: {force_clear}}, 不存在返回空字典
    """
    return ACTION_REGISTRY.get(character_name, {})  # 返回角色的动作字典


# ==== 轴命令机制 (打轴模式用) ====
def set_axis_command(task, character_name, action_name):  # 设置轴命令
    """
    设置轴命令, 让角色脚本执行指定动作。
    :param task: 任务对象
    :param character_name: 角色名
    :param action_name: 动作名
    """
    task._axis_command[character_name] = action_name  # 设置命令
    task._axis_result.pop(character_name, None)  # 清除旧结果


def get_axis_command(task, character_name):  # 获取并清除轴命令
    """
    获取轴命令并清除。角色脚本调用此函数检查是否有待执行的命令。
    :param task: 任务对象
    :param character_name: 角色名
    :return: 动作名, 无命令返回 None
    """
    return task._axis_command.pop(character_name, None)  # 获取并清除命令


def set_axis_result(task, character_name, success, branch_id="default"):  # 设置轴结果
    """
    设置轴执行结果。角色脚本执行完动作后调用此函数报告结果。
    同时通过 _axis_done_events 通知等待方 (task), 无需轮询。
    :param task: 任务对象
    :param character_name: 角色名
    :param success: 是否成功执行
    :param branch_id: 分支标识 (可选), 用于区分同一动作的不同执行路径
    """
    task._axis_result[character_name] = (success, branch_id)  # 设置结果 (元组)
    done_event = task._axis_done_events.get(character_name)  # 获取该角色的完成事件
    if done_event:  # 事件存在
        done_event.set()  # 通知等待方: 动作已完成


def get_axis_result(task, character_name):  # 获取并清除轴结果
    """
    获取轴执行结果并清除。任务调用此函数获取角色执行结果。
    :param task: 任务对象
    :param character_name: 角色名
    :return: (是否成功，分支标识), 无结果返回 None
    """
    return task._axis_result.pop(character_name, None)  # 获取并清除结果


def get_location_box(task, location_name):  # 获取 _location 特征的预定义位置, 返回 Box
    """
    通过 get_feature_by_name 获取特征的位置信息 (x, y, width, height), 构造 Box。
    仅使用位置信息, 不做模板匹配。
    """
    feature = task.get_feature_by_name(location_name)  # 获取 Feature 对象
    if not feature:  # 特征不存在
        return None
    return Box(feature.x, feature.y, feature.width, feature.height,  # 用位置构造 Box
               name=location_name)


def detect_hotkey(task, character_name):  # 检测当前角色占据的是哪个按键槽位 (1/2/3)
    """
    依次在 "character<N>_location" 区域中查找 "character_<name>" 图片。
    _location 图片仅使用位置信息作为搜索区域, 不使用其图片进行匹配。
    找到后将角色→槽位映射存入 task._character_slots, 供 detect_self_on_field 使用。
    返回槽位编号字符串, 未找到则返回 None。
    
    支持多头像 (皮肤): 如果角色模块定义了 AVATAR_ALTS 列表, 会依次尝试所有头像。
    """
    if not hasattr(task, '_character_slots'):  # 首次调用时初始化映射字典
        task._character_slots = {}
    
    # 获取备选头像列表 (用于支持多皮肤)
    avatar_alts = []
    module = CHARACTER_LIBRARY.get(character_name)
    if module and hasattr(module, 'AVATAR_ALTS'):
        avatar_alts = module.AVATAR_ALTS
    
    # 构建所有要尝试的头像名称列表 (主头像 + 备选头像)
    avatar_names = [f"character_{character_name}"] + [f"character_{alt}" for alt in avatar_alts]
    
    task.next_frame()  # 获取新帧用于找图
    for i in range(1, MAX_CHARACTERS + 1):  # 依次检查第 1 到第 3 个槽位
        location_name = f"character{i}_location"  # 构造位置特征名, 如 "character1_location"
        location_feature = task.get_feature_by_name(location_name)  # 获取 _location 的预定义位置 (不做模板匹配)
        if not location_feature:  # 该槽位位置不存在则跳过
            continue
        
        # 尝试所有头像 (主头像 + 备选头像)
        for avatar_name in avatar_names:
            found = task.find_one(avatar_name, box=location_feature)  # 在该位置区域内查找角色图片
            if found:  # 如果在此槽位找到了角色 (任意头像匹配)
                task._character_slots[character_name] = str(i)  # 存储角色→槽位映射
                task.log_info(f"检测到 {character_name} 在槽位 {i} (头像: {avatar_name})")  # 记录找到的槽位和头像
                return str(i)  # 返回槽位编号作为按键
    
    task.log_warning(f"未在任何槽位中找到 {character_name}")  # 所有槽位都未找到
    return None  # 未匹配到任何槽位


def detect_self_on_field(task, character_name):  # 检测指定角色是否在场
    """
    原理: detect_hotkey 已将角色→槽位映射存入 task._character_slots。
    在该角色的槽位区域同时检查:
    1. 按键图片 ("character1"/"character2"/"character3") 不存在
    2. 角色头像 ("character_<name>") 存在
    两个条件都满足才视为角色在场。
    :param task: 任务对象
    :param character_name: 角色名 (如 "qianxiao")
    :return: True=该角色在场, False=不在场
    """
    slot = task._character_slots.get(character_name)  # 从映射中获取该角色的槽位
    if not slot:  # 没有槽位信息
        return False
    location_name = f"hotkey{slot}_location"  # 构造位置特征名
    location_box = get_location_box(task, location_name)  # 获取该槽位的 Box
    if not location_box:  # 位置不存在
        return False
    task.next_frame()  # 获取新帧用于找图
    button_name = f"character{slot}"  # 按键图片名, 如 "character1"
    button_found = task.find_one(button_name, box=location_box)  # 查找按键图片
    if button_found is not None:  # 按键图片存在 → 角色不在场
        return False
    location_name = f"character{slot}_location"
    location_box = get_location_box(task, location_name)
    avatar_name = f"character_{character_name}"  # 角色头像名, 如 "character_qianxiao"
    avatar_found = task.find_one(avatar_name, box=location_box)  # 查找角色头像
    return avatar_found is not None  # 找到角色头像 → 角色在场


def find_sub_dps_slot(task):  # 查找当前队伍中副输出角色所在的槽位
    """
    遍历已识别角色, 找到 CHAR_TYPE 为 SUB_DPS 的角色, 返回其槽位编号。
    :param task: 任务对象
    :return: 槽位编号 (int), 未找到返回 None
    """
    for slot, name in task._detected_characters.items():  # 遍历已识别角色
        module = CHARACTER_LIBRARY.get(name)  # 获取角色模块
        if module and getattr(module, "CHAR_TYPE", None) == CharType.SUB_DPS:  # 检查定位
            return slot  # 返回槽位编号 (int)
    return None  # 未找到副输出角色


def check_buff(task, slot, buff_name):  # 检查指定角色的 buff 是否激活中
    """
    根据 buff 的结束时间判断是否激活中。
    buff 在 states 中以 {buff_name}_time 存储结束时间戳。
    :param task: 任务对象
    :param slot: 角色槽位编号 (int)
    :param buff_name: buff 名称 (如 "buff_end", 对应 states 中的 "buff_end_time")
    :return: 1=激活中, 0=未激活或已过期
    """
    states = task._char_data[slot].get('states', {})  # 获取自定义状态
    end_time = states.get(f"{buff_name}_time", 0)  # 获取结束时间戳
    return 1 if time.time() < end_time else 0  # 当前时间 < 结束时间则激活中

def check_skill_available(task, area, white_threshold=0.02, skill_image="",img_threshold=0.7, binary_threshold=244):  # 识别技能是否可用
    """
    判断技能是否可用, 两条路径:
    - 传 skill_image: 二值化识图 — 帧区域和模板用同一 binary_threshold 二值化后再匹配,
      只依赖亮部形状, 对颜色偏移/变暗鲁棒; 模板本身即区分特征, 无需白色占比检查
    - 不传 skill_image: 用严格纯白 (255,255,255) 占比判断 CD
      原理: 技能可用时图标大部分为纯白 (占比高, 实测 >86%);
      进入 CD 时只有倒计时数字是纯白 (占比 <2%, 数字为严格白色)。
      CD 数字严格白色, 严格找色的区分度最好, 且与游戏内标定的阈值直接对应。
    :param task: 任务对象
    :param area: 区域名, 如 "e"、"q", 内部拼接为 "e_location"、"q_location"
    :param white_threshold: 纯白占比阈值, 大于此值视为可用, 默认 0.02
    :param skill_image: 技能图片名, 不为空时做二值化识图 (置信度 0.7), 找到即视为可用
    :param binary_threshold: 二值化亮度阈值 (0-255), 默认 244, 仅二值化识图路径使用;
                             彩色图标若二值化后亮部过少可下调 (如 200)
    :return: 1=技能可用, 0=技能不可用
    """
    # task.log_info(f"check_skill_available 开始")
    location_name = f"{area}_location"  # 拼接位置特征名, 如 "e_location"
    box = get_location_box(task, location_name)  # 获取该区域的 Box
    if not box:  # 位置不存在
        return 0
    task.next_frame()  # 获取新帧
    if skill_image:  # 传了技能图片: 二值化识图
        feature = task.get_feature_by_name(skill_image)  # 获取已按当前分辨率自动缩放的模板
        if feature is None:  # 特征未标注
            task.log_warning(f"特征 {skill_image} 不存在, 无法识图")
            return 0
        bin_template = binarize_image(feature.mat, binary_threshold)  # 模板二值化 (与帧同一阈值)
        # 帧区域二值化后与二值化模板匹配: 匹配亮部形状, 不受颜色偏移影响
        found = task.find_one(skill_image, box=box, threshold=img_threshold, template=bin_template,
                              frame_processor=lambda img: binarize_image(img, binary_threshold))
        return 1 if found is not None else 0
    white = {'b': (255, 255), 'g': (255, 255), 'r': (255, 255)}  # 严格纯白 RGB 范围
    pct = task.calculate_color_percentage(white, box)  # 计算区域内纯白像素占比
    # task.log_info(f"check_skill_available 结束")
    return 1 if pct >= white_threshold else 0  # 纯白占比超过阈值视为可用


def check_image_match(task, area, skill_image, img_threshold=0.7):  # 纯找图匹配
    """
    纯模板匹配, 不做二值化也不识别颜色, 只在指定区域找图。
    :param task: 任务对象
    :param area: 区域名, 如 "e"、"q", 内部拼接为 "e_location"
    :param skill_image: 技能图片名, 必须提供
    :param img_threshold: 匹配阈值, 默认 0.7
    :return: 1=找到, 0=未找到
    """
    if not skill_image:  # 必须提供图片名
        task.log_warning("check_image_match: skill_image 不能为空")
        return 0
    location_name = f"{area}_location"  # 拼接位置特征名
    box = get_location_box(task, location_name)  # 获取该区域的 Box
    if not box:  # 位置不存在
        return 0
    task.next_frame()  # 获取新帧
    found = task.find_one(skill_image, box=box, threshold=img_threshold)  # 纯模板匹配
    return 1 if found is not None else 0


def check_skill_available_by_color(task, area, color, color_threshold=0.02):  # 识别技能是否可用
    """
    通过找色来判断技能是否可用。
    :param task: 任务对象
    :param area: 区域名, 如 "e"、"q", 内部拼接为 "e_location"、"q_location"
    :param color: 颜色范围字典, 如 {'b': (255, 255), 'g': (255, 255), 'r': (255, 255)}
    :param color_threshold: 颜色占比阈值, 大于此值视为通过, 默认 0.02
    :return: 1=技能可用, 0=技能不可用
    """
    location_name = f"{area}_location"  # 拼接位置特征名, 如 "e_location"
    box = get_location_box(task, location_name)  # 获取该区域的 Box
    if not box:  # 位置不存在
        return 0
    task.next_frame()  # 获取新帧用于找色
    pct = task.calculate_color_percentage(color, box)  # 计算区域内指定颜色像素占比
    color_ok = pct >= color_threshold  # 颜色占比是否超过阈值
    return color_ok


def check_enemy_on(task):  # 检测敌人是否在场 (通过血条颜色)
    """
    在 enemy_health_location 区域检测 RGB(255,178,69) 颜色, 判断敌人是否在场。
    :param task: 任务对象
    :param color_threshold: 颜色占比阈值, 大于此值视为敌人存在, 默认 0.02
    :return: True=敌人存在, False=不存在
    """
    box = get_location_box(task, "enemy_health_location")  # 获取敌人血条区域
    if not box:  # 位置不存在
        return False
    task.next_frame()  # 获取新帧用于找色
    color = {'r': (252, 255), 'g': (175, 181), 'b': (66, 72)}  # RGB(255,178,69) 颜色范围
    pct = task.calculate_color_percentage(color, box)  # 计算区域内该颜色像素占比
    return pct >= 0.99  # 占比超过阈值视为敌人存在


def check_skill_available_by_size(task, area, skill_image, img_threshold=0.7,
                                  min_scale=1, max_scale=1, scale_step=0.1,
                                  binary_threshold=244):  # 多尺度识图判断技能是否可用
    """
    多尺度模板匹配判断技能是否可用: 目标在 原图大小*min_scale ~ 原图大小*max_scale
    范围内任意尺寸都算匹配成功 (默认 0.5~1.5 倍, 每 10% 一档)。
    框架 find_one 是单尺度 matchTemplate, 这里把模板缩放到多档倍率,
    在同一帧上逐档匹配, 任一档命中即返回 1。不含白色占比判断。
    二值化识图 (默认): 模板和帧区域用同一阈值二值化后匹配亮部形状, 对颜色偏移鲁棒。
    顺序必须是 先插值再二值化——插值作用在连续亮度上才能正确平均/过渡,
    二值图直接缩放会丢细亮部 (缩小时白黑平均成灰, 再阈值化直接消失) 或产生灰边失真。
    :param task: 任务对象
    :param area: 区域名, 如 "e"、"q", 内部拼接为 "e_location"、"q_location"
    :param skill_image: 技能图片名, 必填 (为空直接返回 0)
    :param img_threshold: 匹配置信度阈值, 默认 0.7
    :param min_scale: 最小倍率, 默认 0.5 (模板原大小的 50%)
    :param max_scale: 最大倍率, 默认 1.5 (模板原大小的 150%)
    :param scale_step: 倍率步长, 默认 0.1 (每 10% 做一次识图)
    :param binary_threshold: 二值化亮度阈值 (0-255), 默认 244 即二值化识图; 传 0 关闭二值化走彩色识图
    :return: 1=技能可用, 0=技能不可用
    """
    if not skill_image:  # 多尺度识图必须提供模板图片
        task.log_warning("check_skill_available_by_size: skill_image 不能为空")
        return 0
    location_name = f"{area}_location"  # 拼接位置特征名, 如 "e_location"
    box = get_location_box(task, location_name)  # 获取该区域的 Box
    if not box:  # 位置不存在
        return 0
    feature = task.get_feature_by_name(skill_image)  # 获取已按当前分辨率缩放的模板
    if feature is None:  # 特征未标注
        task.log_warning(f"特征 {skill_image} 不存在, 无法识图")
        return 0
    task.next_frame()  # 刷新一帧, 所有倍率共用同一帧 (一次截图多档检测)
    # 二值化识图时帧区域用同一阈值二值化 (每档重复处理同一区域, 区域小开销可忽略)
    frame_processor = (lambda img: binarize_image(img, binary_threshold)) if binary_threshold > 0 else None
    step_count = round((max_scale - min_scale) / scale_step)  # 档位数 (用整数计数避免浮点累积误差)
    for i in range(step_count + 1):  # 逐档匹配, 含首尾两端 (默认 0.5~1.5 共 11 档)
        scale = min_scale + i * scale_step  # 当前档倍率
        if abs(scale - 1.0) < 1e-6:  # 1.0 档直接用原模板, 避免二次缩放引入误差
            scaled = feature.mat
        else:  # 按倍率缩放模板 (先在彩色图上插值, 保证亮度插值正确)
            interp = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LINEAR  # 缩小用区域插值, 放大用线性插值
            scaled = cv2.resize(feature.mat, (0, 0), fx=scale, fy=scale, interpolation=interp)
        if scaled.shape[0] > box.height or scaled.shape[1] > box.width:  # 模板已大于搜索区域
            break  # 倍率递增只会更大, 后续档位都不可能匹配, 提前退出
        if binary_threshold > 0:  # 二值化识图: 插值完成后再二值化, 只比亮部形状
            template = binarize_image(scaled, binary_threshold)
        else:  # 彩色识图
            template = scaled
        found = task.find_one(skill_image, box=box, threshold=img_threshold, template=template,
                              frame_processor=frame_processor)  # 单尺度匹配
        if found is not None:  # 任一档命中即视为技能可用
            return 1
    return 0  # 所有倍率档位都未命中


def binarize_image(image, threshold=244):  # 灰度二值化: 亮度 > threshold 的像素变白, 其余变黑
    """
    将 BGR 图像转为灰度后做二值化, 用于抗颜色偏移的模板匹配或亮度检测。
    :param image: BGR 图像 (numpy ndarray)
    :param threshold: 亮度阈值 (0-255), 默认 244 仅保留极亮像素
    :return: 单通道二值图像 (numpy ndarray, 0 或 255)
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)  # BGR 转灰度
    _, binary = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)  # 灰度二值化
    return binary


def calculate_binary_percentage(task, box, threshold=244):  # 二值化后计算白色像素占比
    """
    对指定区域做灰度二值化, 计算白色像素占总像素的比例。
    适用于检测 UI 元素是否 "亮起" (如技能图标、共鸣回路等), 不受颜色偏移影响。
    内部自带 next_frame(): task.frame 是缓存, 不刷新会永远判定同一帧
    (与 check_skill_available 约定一致, 调用方无需自己刷帧)。
    :param task: 任务对象
    :param box: 检测区域 (Box)
    :param threshold: 亮度阈值 (0-255), 默认 244
    :return: 白色像素占比 (0.0~1.0)
    """
    task.next_frame()  # 刷新帧, 保证判定的是最新截图
    cropped = box.crop_frame(task.frame)  # 裁剪出目标区域
    binary = binarize_image(cropped, threshold)  # 灰度二值化
    white_pixels = cv2.countNonZero(binary)  # 统计白色像素数
    total_pixels = binary.size  # 总像素数
    return white_pixels / total_pixels if total_pixels > 0 else 0  # 返回占比


def check_skill_available_binary(task, area, threshold=244, white_threshold=0.02):  # 二值化方式检测技能是否可用
    """
    通过灰度二值化后计算白色像素占比来判断技能是否可用。
    与 check_skill_available 的区别: 不依赖特定颜色范围, 仅依赖亮度, 对颜色偏移更鲁棒。
    :param task: 任务对象
    :param area: 区域名, 如 "e"、"q", 内部拼接为 "e_location"
    :param threshold: 二值化亮度阈值 (0-255), 默认 244
    :param white_threshold: 白色占比阈值, 大于此值视为技能可用, 默认 0.02
    :return: 1=技能可用, 0=技能不可用
    """
    location_name = f"{area}_location"  # 拼接位置特征名
    box = get_location_box(task, location_name)  # 获取该区域的 Box
    if not box:  # 位置不存在
        return 0
    pct = calculate_binary_percentage(task, box, threshold)  # 二值化后计算白色占比 (内部已刷帧)
    return 1 if pct >= white_threshold else 0  # 超过阈值视为可用


# ==== 处决 (F 键) 检测配置 ====
# 处决 F 提示出现在怪物头顶, 随怪物移动, 不能在固定位置检测;
# 也不依赖"脱离战斗"清状态 (多波次连续战斗不会脱战), 每次调用现检测, 无陈旧状态问题。
# 方案: 在屏幕中央区域找处决按键图片 (参考 ok-wuthering-waves 的 check_f_break),
#       找到图片 = 一定可以处决, 避免原找色方案"处决条没满误判为满"。
# 搜索区域为相对屏幕的比例 (x起点, y起点, x终点, y终点), 可按需调大
F_BREAK_REGION = (0.2, 0.2, 0.75, 0.8)  # 处决按键搜索区域 (暂用参考项目值, 待调大)
F_BREAK_THRESHOLD = 0.7  # 找图阈值
F_BREAK_TARGET_HEIGHT = 720  # 搜索区域与模板降采样到 720p 匹配 (实测约 11ms, 参考项目同款优化)


def f_execute(task, f_time=1.6):  # 处决检测与执行: 屏幕中央找处决按键图片
    """
    在屏幕中央区域找处决 F 按键图片, 找到即按 F 处决。
    :param task: 任务对象
    :param f_time: 按 F 后的等待时间 (处决动画)
    :return: 1=处决成功, 0=不可处决
    """
    x1, y1, x2, y2 = F_BREAK_REGION  # 解包区域比例
    # 构造中央搜索区域 (比例自动换算为当前分辨率的像素坐标)
    can_f = check_skill_available_binary(task,"f",threshold=200,white_threshold=0.99)
    box = task.box_of_screen(x1, y1, x2, y2, hcenter=True, vcenter=True, name="f_break_search")
    # task.next_frame()  # 获取新帧用于找图
    # 找处决按键图片: 降采样到 720p 匹配提速, 结果坐标自动换算回原尺度
    found = task.find_one("f_break", box=box, threshold=F_BREAK_THRESHOLD,
                              target_height=F_BREAK_TARGET_HEIGHT)
    # if found or can_f:  # 找到 = 一定可处决
    if can_f:  # 找到 = 一定可处决    
        task.log_info(f"处决 开始")
        task.send_key("f")  # 按 F 处决
        time.sleep(f_time)  # 等处决动画
        return 1  # 处决成功 (found 或 can_f 任一命中即算成功)
    else:  # 未找到处决按键
        task.log_info(f"不能处决")
        return 0

def enable_mouse_tracking(task):  # 包装 task 的 mouse_down/mouse_up, 记录脚本长按状态
    """
    框架交互层不记录按压状态 (PostMessage 后台合成点击也无法用 GetAsyncKeyState 查询),
    故在脚本侧包装记录"脚本当前按住哪些键", 供切换逻辑判断。
    实例级包装: 所有 task.mouse_down/mouse_up 调用点 (角色脚本/任务) 自动被记录, 无需改调用点。
    并发重复包装无害 (set 操作幂等)。
    """
    if getattr(task, "_mouse_tracking", False):  # 已包装过
        return
    task._held_mouse_keys = set()  # 脚本当前按住的按键集合
    orig_down, orig_up = task.mouse_down, task.mouse_up  # 保存原始方法

    def mouse_down(x=-1, y=-1, name=None, key="left"):  # 按住并记录
        result = orig_down(x=x, y=y, name=name, key=key)  # 先执行原始按住
        task._held_mouse_keys.add(key)  # 记录长按
        return result

    def mouse_up(name=None, key="left"):  # 释放并清除记录
        result = orig_up(name=name, key=key)  # 先执行原始释放
        task._held_mouse_keys.discard(key)  # 清除长按记录
        return result

    task.mouse_down = mouse_down  # 实例属性覆盖, 优先于类方法被调用
    task.mouse_up = mouse_up
    task._mouse_tracking = True  # 包装标记


def is_mouse_held(task, key="left"):  # 脚本当前是否按住指定鼠标键
    return key in getattr(task, "_held_mouse_keys", ())  # 未包装时返回 False


# ==== 断点继续 (pause) 功能 ====
_pause_flag = False  # pause 触发标记 (配置的 pause 热键设置为 True, pause() 读取后清除)


def set_pause():  # pause 热键回调中调用, 设置 pause 标记
    global _pause_flag
    _pause_flag = True


def pause(task, action_name=None, trigger_counts=None, sleep_duration=0.4):
    """
    断点继续: 支持简单模式和计数模式。

    简单模式: pause(task)
        按 pause 热键后 sleep, 每次触发只生效一次。

    计数模式: pause(task, "action_a", [2, 4, 6])
        每次调用计数+1, 计数达到指定值时 sleep。
        例如 [2, 4, 6] 表示第 2/4/6 次调用时触发 sleep。

    :param task: 任务对象
    :param action_name: 动作名称 (用于区分不同 pause 计数器), 不传则使用简单模式
    :param trigger_counts: 触发计数的数组 (如 [2, 4, 6]), 不传则使用简单模式
    :param sleep_duration: 暂停时长 (秒), 默认 0.4
    """
    global _pause_flag

    # 从调用栈获取调用者的 CHARACTER_NAME (角色脚本中的模块级变量)
    caller_frame = inspect.stack()[1].frame  # 获取调用者的栈帧
    char_name = caller_frame.f_locals.get('CHARACTER_NAME', None)  # 从调用者局部变量获取
    if char_name is None:
        char_name = caller_frame.f_globals.get('CHARACTER_NAME', '未知角色')  # 回退到全局变量

    # 简单模式: 没有传 action_name 和 trigger_counts
    if action_name is None or trigger_counts is None:
        if not _pause_flag:
            return
        _pause_flag = False  # 清除标记, 本轮只触发一次
        task.log_info(f"{char_name} pause 触发, 暂停 {sleep_duration}s")
        time.sleep(sleep_duration)
        return

    # 计数模式: 需要获取当前角色的槽位
    slot = None
    for s, name in task._detected_characters.items():
        if name == char_name:
            slot = s
            break
    if slot is None:
        task.log_warning(f"{char_name} 未找到槽位, pause 计数模式失效")
        return

    states = task._char_data[slot].setdefault('states', {})  # 获取自定义状态
    count_key = f"{action_name}_pause_count"  # 计数器键名
    current_count = states.get(count_key, 0) + 1  # 计数+1
    states[count_key] = current_count  # 更新计数器

    # 检查是否达到触发条件, 计数模式自动触发 sleep, 不需要按键
    if current_count in trigger_counts:
        task.log_info(f"{char_name} pause[{action_name}] 第{current_count}次触发, 暂停 {sleep_duration}s")
        time.sleep(sleep_duration)


def wait_for_my_turn(task, hotkey, character_name):  # 等待轮到自己上场, 不在场时线程挂起, 零 CPU
    """
    阻塞当前线程, 直到 task 调用 event.set() 唤醒。
    唤醒后立即清除事件, 确保下次 wait() 会真正阻塞。
    唤醒后循环点击角色按键, 直到 detect_self_on_field 确认角色在场。
    如果角色已在场, detect_self_on_field 立即返回 True, 不会浪费时间。
    上个角色可能预输入了长按左键 (如飞雪蓄力), 切换过程中不能打断:
    仅在脚本没有按住左键时才 click, 有长按时只发角色按键。
    :param task: 任务对象
    :param hotkey: 角色对应的槽位按键 (如 "1", "2", "3")
    :param character_name: 角色名 (如 "qianxiao")
    """
    enable_mouse_tracking(task)  # 确保长按状态记录已启用 (包装幂等)
    event = task._char_events.get(int(hotkey))  # 获取该角色对应的唤醒事件
    if event:  # 事件存在
        event.wait()  # 阻塞直到 event.set() 被调用 (始终等待, 保持同步)
        event.clear()  # 唤醒后立即清除, 确保下次 wait() 会阻塞
    # 唤醒后, 点击直到在场 (如果已在场会立即返回)
    task.send_key(hotkey)  # 先点击一次自己的角色按键
    while task.enabled and task._combat_active:  # 任务启用且战斗激活时持续检测
        if detect_self_on_field(task, character_name):  # 检测自己是否在场
            task.log_info(f"{character_name}上场")
            break  # 已上场, 退出循环
        else:
            # if not is_mouse_held(task):  # 有预输入长按时不点击, 避免打断长按
                # task.click()  # 点击鼠标左键
            task.send_key(hotkey)  # 点击自己的角色按键
            time.sleep(0.02)


def release_turn(task, hotkey):  # 主动释放控制权, 让自己进入睡眠
    """
    清除该角色的唤醒事件, 使下次 wait_for_my_turn 时线程挂起。
    通常在检测到需要切换角色时调用。
    """
    event = task._char_events.get(int(hotkey))  # 获取该角色对应的唤醒事件
    if event:  # 事件存在
        event.clear()  # 清除事件, 下次 wait 时会阻塞


def freeze_time(task, duration):  # 时停: 将所有倒计时延长 (游戏内动画期间时间暂停)
    """
    游戏内播放动画时相当于时间停止, 脚本的实时时钟仍在走。
    调用此函数将所有倒计时截止时间向后推 duration 秒, 保持游戏与脚本的时间同步。
    影响的倒计时: _pending_resets (攻击计数重置), _switch_cooldowns (切换冷却),
    _char_data[slot]['states'] 中以 _time 结尾的自定义倒计时。
    :param task: 任务对象
    :param duration: 动画时长 (秒)
    """
    for slot in task._pending_resets:  # 遍历攻击计数重置倒计时
        task._pending_resets[slot] += duration  # 延长截止时间
    # _switch_cooldowns 仅在自动模式下存在, 打轴模式没有
    if hasattr(task, '_switch_cooldowns'):
        for slot in task._switch_cooldowns:  # 遍历切换冷却时间
            task._switch_cooldowns[slot] += duration  # 延长截止时间
    for slot in task._char_data:  # 遍历所有角色槽位
        states = task._char_data[slot].get('states', {})  # 获取自定义状态
        for key in states:  # 遍历状态键
            if key.endswith('_time'):  # 以 _time 结尾的是倒计时
                states[key] += duration  # 延长截止时间


def wait_previous_action(action_finish_time):  # 等待上个动作完成
    """
    如果上个动作的完成时间还没到, 则 sleep 等待剩余时间。
    :param action_finish_time: 上个动作的完成时间戳
    :return: 等待后的时间戳
    """
    now = time.time()  # 获取当前时间
    if now < action_finish_time:  # 上个动作还在进行中
        time.sleep(action_finish_time - now)  # 等待剩余时间结束
        return action_finish_time  # 返回动作完成时间
    return now  # 没有待等待的动作, 返回当前时间


def continuous_click(task, duration, check_active=True):  # 持续点击鼠标左键指定时长
    """
    在指定时间内持续点击鼠标左键, 每次点击间隔 30ms。
    :param task: 任务对象
    :param duration: 持续时间 (秒)
    :param check_active: 是否检查 task.enabled 和 task._combat_active
    """
    end_time = time.time() + duration  # 计算结束时间戳
    while time.time() < end_time:  # 在指定时间内持续点击
        if check_active and not (task.enabled and task._combat_active):  # 检查是否需要继续
            break  # 任务已停止, 退出循环
        task.click()  # 点击鼠标左键
        time.sleep(0.07)  # 每次点击间隔 20ms


def continuous_send_key(task, key, duration, check_active=True):  # 持续按指定按键指定时长
    """
    在指定时间内持续按指定按键, 每次按键间隔 70ms (与 continuous_click 一致)。
    :param task: 任务对象
    :param key: 按键名, 如 "a"、"e"、"space" (与 task.send_key 的按键词表一致)
    :param duration: 持续时间 (秒)
    :param check_active: 是否检查 task.enabled 和 task._combat_active
    """
    end_time = time.time() + duration  # 计算结束时间戳
    while time.time() < end_time:  # 在指定时间内持续按键
        if check_active and not (task.enabled and task._combat_active):  # 检查是否需要继续
            break  # 任务已停止, 退出循环
        task.send_key(key)  # 按一次指定按键
        time.sleep(0.07)  # 每次按键间隔 70ms


def send_a_num_by_con(task, slot, num):  # 通过协奏值变化次数控制攻击次数
    """
    持续点击鼠标左键，直到协奏值增加指定次数。
    每次检测到协奏值比上次大时，计数+1，达到目标次数后停止。
    :param task: 任务对象
    :param slot: 角色槽位编号 (int)
    :param num: 目标协奏值增加次数
    """
    last_con = task.get_current_con(slot)  # 获取初始协奏值
    count = 0  # 协奏值增加次数计数
    while task.enabled and task._combat_active:  # 任务启用且战斗激活时持续
        if count >= num:  # 达到目标次数
            break  # 退出循环
        task.click()  # 点击鼠标左键
        current_con = task.get_current_con(slot)  # 获取当前协奏值
        if current_con > last_con:  # 协奏值增加了
            count += 1  # 计数+1
            last_con = current_con  # 更新 last_con
        time.sleep(0.01)  # 每次点击间隔 10ms


# ==== 角色库 (按属性分文件夹导入) ====
# 新增角色时: 1. 在对应属性文件夹下创建脚本文件  2. 在此处 import 并注册
# 脚本文件必须有 CHARACTER_NAME 常量和 run(task) 函数

# 衍射 (SPECTRO)
from src.character.spectro import jinxi, Linnai, shorekeeper, verina
# 导电 (ELECTRIC)
from src.character.electric import rebecca
# 热熔 (FIRE)
from src.character.fire import Aemeath, Mornye, denia, Galbrena, Lupa
# 冰属性 (ICE)
from src.character.ice import feixue, suisui, sanhua
# 气动 (WIND)
from src.character.wind import qingxiao, jianxin, xigelika, qiuyuan
# 湮灭 (HAVOC)
from src.character.havoc import qianxiao, yangyang, HavocRover

CHARACTER_LIBRARY = {  # 角色库: 角色名 → 脚本模块, 新增角色在此注册
    "qianxiao": qianxiao,  # 千晓
    "yangyang": yangyang,
    "HavocRover": HavocRover,  # 漂泊者 (湮灭)
    "suisui": suisui,
    "Linnai": Linnai,
    "feixue": feixue,
    "sanhua": sanhua,  # 散华
    "Aemeath": Aemeath,
    "Mornye": Mornye,
    "qingxiao": qingxiao,
    "denia": denia,
    "jianxin": jianxin,
    "xigelika": xigelika,
    "verina": verina,
    "shorekeeper": shorekeeper,
    "qiuyuan": qiuyuan,
    "jinxi": jinxi,
    "rebecca": rebecca,
    "Galbrena": Galbrena,
    "Lupa": Lupa,
}
