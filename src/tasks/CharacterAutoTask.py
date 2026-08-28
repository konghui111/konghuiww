import os  # 导入操作系统模块, 用于文件路径操作
import ctypes  # 导入 ctypes 模块, 用于调用 Windows API 注册全局热键
import ctypes.wintypes  # 导入 Windows 数据类型 (MSG 等)
import threading  # 导入线程模块, 脚本在子线程中运行, 主线程继续监听热键
import time  # 导入时间模块, 用于协同函数中的计时和等待
import importlib  # 导入 importlib 模块, 用于热重载角色脚本
import numpy as np  # 导入 numpy, 用于协奏值环的颜色掩膜运算
import cv2  # 导入 OpenCV, 用于协奏值环的形态学运算和轮廓检测
from decimal import Decimal, ROUND_DOWN, ROUND_UP  # 导入.Decimal 用于精确计算环掩膜半径

from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QApplication, QFileDialog  # 导入 Qt 控件
from PySide6.QtCore import Qt  # 导入 Qt 常量
from qfluentwidgets import FluentIcon, PushButton  # 导入图标和按钮控件

from src.tasks.MyBaseTask import MyBaseTask  # 导入项目自定义基类
from src.character import CHARACTER_LIBRARY, detect_hotkey, ACTION_REGISTRY, CharType, get_location_box,calculate_binary_percentage,check_skill_available_binary  # 导入角色库和角色检测函数
from src.tasks.AxisEditor import Axis, AxisEditorDialog, CharacterSelectionDialog  # 导入轴编辑器模块
from src.tasks.CharacterEditor import CharacterEditorDialog  # 导入角色编辑器
from src.character.fg_time_collector import FgTimeCollector  # 导入 fg_time 自动收集器

# ---- 协奏值能量环颜色范围 (对应不同角色属性) ----

CON_COLORS = [
    {'r': (205, 235), 'g': (190, 222), 'b': (90, 130)},   # 0: 衍射 (黄色)
    {'r': (150, 190), 'g': (95, 140), 'b': (210, 249)},   # 1: 导电 (紫色)
    {'r': (200, 230), 'g': (100, 130), 'b': (75, 105)},   # 2: 热熔 (红色)
    {'r': (60, 95), 'g': (150, 180), 'b': (210, 245)},    # 3: 冰属性 (蓝色)
    {'r': (70, 110), 'g': (215, 250), 'b': (155, 190)},   # 4: 气动 (绿色)
    {'r': (190, 220), 'g': (65, 105), 'b': (145, 175)},   # 5: 湮灭 (暗色)
]


# ---- Windows API 常量 ----
WM_HOTKEY = 0x0312  # Windows 热键消息编号
MOD_NONE = 0x0000  # 不需要组合键

# 按键名称 → Windows 虚拟键码映射
_VK_MAP = {
    "Escape": 0x1B, "Tab": 0x09, "Space": 0x20, "Return": 0x0D,
    "Enter": 0x0D, "Backspace": 0x08,
    "Up": 0x26, "Down": 0x28, "Left": 0x25, "Right": 0x27,
}


def _get_vk(name):  # 把按键名称转换为 Windows 虚拟键码
    if name in _VK_MAP:  # 查映射表
        return _VK_MAP[name]
    if name.startswith("F") and name[1:].isdigit():  # F1-F12
        return 0x70 + int(name[1:]) - 1
    if len(name) == 1 and name.isalpha():  # A-Z
        return ord(name.upper())
    return 0


# ==== 按键捕获对话框 ====
class _HotkeyCaptureDialog(QDialog):  # 弹出窗口, 等待用户按一个键

    def __init__(self, parent=None):
        super().__init__(parent)
        self.hotkey = None  # 捕获到的按键名称
        self.setWindowFlags(Qt.WindowType.Popup)  # 弹出式, 不显示在任务栏
        self.setModal(True)  # 模态, 必须操作完才能继续
        self.setWindowTitle("设置热键")
        layout = QVBoxLayout()
        layout.addWidget(QLabel("请按下您想要设置的按键..."))
        self.setLayout(layout)
        self.resize(300, 100)
        if parent:
            self.move(parent.x() + parent.width() // 2 - 150, parent.y() + parent.height() // 2 - 50)

    def keyPressEvent(self, event):  # 用户按键时触发
        key = event.key()
        self.hotkey = self._key_name(key)
        self.accept()

    def _key_name(self, key):  # Qt 键码 → 可读名称
        special = {
            Qt.Key.Key_Escape: "Escape", Qt.Key.Key_Tab: "Tab",
            Qt.Key.Key_Space: "Space", Qt.Key.Key_Return: "Return",
            Qt.Key.Key_Enter: "Enter", Qt.Key.Key_Backspace: "Backspace",
            Qt.Key.Key_Up: "Up", Qt.Key.Key_Down: "Down",
            Qt.Key.Key_Left: "Left", Qt.Key.Key_Right: "Right",
        }
        if key in special:
            return special[key]
        if Qt.Key.Key_F1 <= key <= Qt.Key.Key_F12:
            return f"F{key - Qt.Key.Key_F1 + 1}"
        if Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
            return chr(key)
        return f"Key_{key}"


# ==== 角色自动战斗任务 ====
class CharacterAutoTask(MyBaseTask):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "角色自动战斗"
        self.description = "启用任务后按热键开始/停止战斗, GUI 开关控制整个任务。"
        self.icon = FluentIcon.PLAY

        # ---- 默认配置 ----
        self.default_config.update({
            "启停热键": "F7",  # 控制战斗开始/停止的按键
            "战斗模式": "自动",  # 战斗模式: "自动" 或 "打轴"
            "编辑角色": "编辑角色",  # 占位符, 用于显示按钮
            "新建轴": "新建轴",  # 占位符, 用于显示按钮
            "编辑轴": "编辑轴",  # 占位符, 用于显示按钮
            "导入轴": "导入轴",  # 占位符, 用于显示按钮
        })
        self.config_description.update({
            "启停热键": "点击按钮后按下要设置的键, 按此键开始/停止战斗。",
            "战斗模式": "自动: 使用调度算法自动切换角色; 打轴: 按固定轴顺序执行动作。",
            "编辑角色": "打开角色属性编辑器, 修改角色定位、属性、共鸣链等, 保存到脚本文件。",
            "新建轴": "创建新的轴: 先选择角色, 再编辑动作时间线。",
            "编辑轴": "选择已有的轴文件, 打开编辑器修改后保存。",
            "导入轴": "从文件加载已有的轴配置。",
        })
        self.config_type.update({
            "启停热键": {
                "type": "button",
                "text": "当前: F7",  # 默认值, run() 执行后更新为实际保存的值
                "callback": self._capture_hotkey,
            },
            "战斗模式": {
                "type": "drop_down",
                "options": ["自动", "打轴"],
                "sub_configs": {
                    "打轴": ["新建轴", "编辑轴", "导入轴"],  # 打轴模式下显示这些配置项
                },
            },
            "编辑角色": {
                "type": "button",
                "text": "编辑角色",
                "callback": self._edit_character,
            },
            "新建轴": {
                "type": "button",
                "text": "新建轴",
                "callback": self._create_new_axis,
            },
            "编辑轴": {
                "type": "button",
                "text": "编辑轴",
                "callback": self._edit_axis,
            },
            "导入轴": {
                "type": "button",
                "text": "导入轴",
                "callback": self._import_axis,
            },
        })

        # ---- 状态变量 ----
        self._combat_active = False  # 战斗是否激活 (热键切换)
        self._hotkey_btn = None  # 缓存按钮引用
        self._hotkey_id = 0  # Windows 热键 ID, 0=未注册
        self._run_stopped = False  # run() 循环退出标志 (on_destroy 设置)
        self._detected_characters = {}  # 识别到的角色 {槽位编号: 角色名}, 如 {1: "qianxiao", 3: "other"}
        self._script_threads = []  # 角色脚本线程列表, 用于清理旧线程

        # ---- 角色协同变量 (各角色脚本可读写, 用于跨脚本协同) ----
        self._char_data = {  # 按槽位组织的角色协同数据
            1: {'switchable': False, 'skill_ready': False, 'attack_counts': [0, 0, 0, 0], 'states': {}},
            2: {'switchable': False, 'skill_ready': False, 'attack_counts': [0, 0, 0, 0], 'states': {}},
            3: {'switchable': False, 'skill_ready': False, 'attack_counts': [0, 0, 0, 0], 'states': {}},
        }
        self._character_jumping = False  # 角色跳跃状态

        # ---- 角色切换自动检测 ----
        self._current_character_index = 0  # 当前检测到的在场角色编号 (0=未知, 1/2/3=对应角色)
        self._pending_resets = {}  # 待处理的攻击计数重置 {角色编号: 截止时间戳}
        self._char_events = {1: threading.Event(), 2: threading.Event(), 3: threading.Event()}  # 每个角色的唤醒事件, 脚本用 event.wait() 挂起, task 用 event.set() 唤醒

        # ---- 轴命令机制 (打轴模式用) ----
        self._axis_command = {}  # 轴命令 {角色名: 动作名}, 角色脚本检查并执行
        self._axis_result = {}  # 轴结果 {角色名: 是否成功 (bool)}
        self._axis_done_events = {}  # 轴完成事件 {角色名: Event}, 角色脚本完成后 set(), task 用 wait() 等待
        self._axis_same_char_next = False  # 下个轴动作是否同一角色, True 时角色脚本跳过 wait_for_my_turn

        # ---- 角色调度器 ----
        self._switch_cooldowns = {}  # 各槽位的切换冷却结束时间 {槽位: 时间戳}, 被切离后 1 秒内不可再上场
        self._last_scheduled_slot = 0  # 上次被调度上场的槽位编号, 用于避免连续安排同一角色

        # ---- 协奏值相关 ----
        self._con_full_size = {str(i): 0 for i in range(len(CON_COLORS))}  # 各属性协奏值环充满时的大小记录
        self._ring_indices = {}  # 各槽位角色的协奏值环颜色索引 {槽位: 颜色索引}
        self._con_data = {}  # 预计算的协奏检测数据 {槽位: {box, lower, upper, min_area, mask, color_index}}

        # ---- 打轴模式相关 ----
        self._current_axis = None  # 当前加载的轴对象
        self._axis_phase = "startup"  # 当前轴阶段: "startup" 或 "loop"
        self._axis_index = 0  # 当前轴动作索引

        # ---- fg_time 收集器 ----
        self._fg_collector = FgTimeCollector()  # 自动收集打轴时的实测前台时间

    # ---- 重置战斗状态到初始 ----
    def _reset_combat_state(self):  # 将所有战斗运行时状态恢复到初始值, 角色识别和预计算数据保留
        self._combat_active = False  # 战斗未激活
        # 释放可能残留的鼠标和按键状态, 防止脚本中断后鼠标失灵
        try:
            self.mouse_up(key="left")  # 释放左键
            self.mouse_up(key="right")  # 释放右键
            for k in ("e", "r", "q", "space"):  # 释放可能按住的技能键
                self.send_key_up(k)
        except Exception:  # 清理操作不应影响后续重置
            pass
        self._char_data = {  # 重置角色协同数据
            1: {'switchable': False, 'skill_ready': False, 'attack_counts': [0, 0, 0, 0], 'states': {}},
            2: {'switchable': False, 'skill_ready': False, 'attack_counts': [0, 0, 0, 0], 'states': {}},
            3: {'switchable': False, 'skill_ready': False, 'attack_counts': [0, 0, 0, 0], 'states': {}},
        }
        self._character_jumping = False  # 重置跳跃状态
        self._current_character_index = 0  # 重置在场角色
        self._pending_resets = {}  # 清空待处理重置
        for e in self._char_events.values():  # 清空所有角色唤醒事件
            e.clear()
        self._axis_command = {}  # 清空轴命令
        self._axis_result = {}  # 清空轴结果
        self._axis_done_events = {}  # 清空轴完成事件
        self._trim_memory()  # 回收 WGC 截图管线产生的内存占用
        self._axis_same_char_next = False  # 重置连续同角色标记
        self._switch_cooldowns = {}  # 清空切换冷却
        self._last_scheduled_slot = 0  # 重置上次调度槽位
        self._axis_phase = "startup"  # 重置轴阶段
        self._axis_index = 0  # 重置轴索引

    def _trim_memory(self):
        """回收 Python 进程自身的内存缓存"""
        try:
            # 只清理 Python 自身进程的工作集, 不关闭 WGC (关闭后重建耗时 1-3 秒)
            ctypes.windll.psapi.EmptyWorkingSet(ctypes.windll.kernel32.GetCurrentProcess())
            self.log_info("已回收 Python 进程的内存缓存")
        except Exception as e:
            self.log_warning(f"内存回收失败: {e}")

    # ---- 注册/注销 Windows 全局热键 ----
    def _register_hotkey(self):  # 注册全局热键, 即使游戏在前台也能监听
        name = self.config.get("启停热键", "F7")  # 读取热键名称
        vk = _get_vk(name)  # 转为虚拟键码
        if vk == 0:
            self.log_warning(f"无法注册热键: {name}")
            return False
        self._hotkey_id = 0x1001  # 分配 ID (避开框架 DebugTab 的 1/2 和 StartCard 的 999, 防撞号)
        ok = ctypes.windll.user32.RegisterHotKey(None, self._hotkey_id, MOD_NONE, vk)
        if not ok:
            self.log_warning(f"热键 {name} 注册失败, 可能已被其他程序占用", notify=True)
            self._hotkey_id = 0
            return False
        return True

    def _unregister_hotkey(self):  # 注销全局热键
        if self._hotkey_id:
            ctypes.windll.user32.UnregisterHotKey(None, self._hotkey_id)
            self._hotkey_id = 0

    # ---- 按键捕获 ----
    def _capture_hotkey(self):  # 点击"设置热键"按钮时弹出捕获窗口
        dialog = _HotkeyCaptureDialog()
        if dialog.exec() and dialog.hotkey:
            self.config["启停热键"] = dialog.hotkey  # 保存
            self._update_hotkey_button(dialog.hotkey)  # 更新按钮文字
            self.log_info(f"热键已设置为: {dialog.hotkey}")

    def _update_hotkey_button(self, hotkey):  # 更新按钮显示当前热键
        # 更新 config_type 的 text, ConfigCard 创建按钮时读取此值
        self.config_type["启停热键"]["text"] = f"当前: {hotkey}"
        # 如果按钮已存在, 直接更新文字
        if self._hotkey_btn:
            self._hotkey_btn.setText(f"当前: {hotkey}")
            return
        for top in QApplication.topLevelWidgets():
            for btn in top.findChildren(PushButton):
                if btn.text().startswith("当前:") or btn.text() == "设置热键":
                    btn.setText(f"当前: {hotkey}")
                    self._hotkey_btn = btn
                    return

    # ---- 角色识别 ----
    def _detect_characters(self):  # 从角色库中识别当前队伍中的角色及其槽位
        """遍历角色库, 对每个角色调用 detect_hotkey 检测其所在槽位。"""
        # 检查帧捕获是否可用
        try:
            frame = self.frame  # 尝试获取帧
            if frame is None:  # 帧为空
                self.log_warning("无法获取游戏画面, 请确认游戏窗口已连接并启动")
                return
        except Exception as e:  # 获取帧时出错
            self.log_warning(f"获取游戏画面失败: {e}, 请确认游戏窗口已连接")
            return

        self._detected_characters = {}  # 清空上次识别结果
        for name, module in CHARACTER_LIBRARY.items():  # 遍历角色库中的每个角色
            char_name = module.CHARACTER_NAME  # 获取角色的 CHARACTER_NAME 常量
            char_type = module.CHAR_TYPE  # 获取角色的 CHAR_TYPE 定位
            try:
                hotkey = detect_hotkey(self, char_name)  # 检测该角色在哪个槽位
            except Exception as e:  # 检测时出错
                self.log_warning(f"检测角色 {char_name} 时出错: {e}")
                continue
            if hotkey:  # 检测成功
                slot = int(hotkey)  # 槽位编号
                self._detected_characters[slot] = name  # 记录: 槽位 → 角色名
                self.info_set(f"槽位{slot}", f"{char_name} ({char_type})")  # 在信息面板显示
        if not self._detected_characters:  # 没有识别到任何角色
            self.log_warning("未识别到任何角色, 请确认角色图片已标记")
        else:
            summary = ", ".join(f"槽位{slot}: {name}" for slot, name in sorted(self._detected_characters.items()))
            self.log_info(f"角色识别完成: {summary}")
            self._precompute_con_data()  # 预计算协奏检测数据 (环形掩膜、颜色边界等)

    def _precompute_con_data(self):  # 预计算协奏值检测所需的所有静态数据
        """
        角色识别完成后调用, 一次性计算每个槽位的颜色边界。
        战斗中 is_con_full 使用 forte_location 区域找色判断能量是否满。
        """
        self._con_data = {}  # 清空旧的预计算数据
        # con_box = self.box_of_screen_scaled(3840, 2160, 1431, 1942, 1557, 2068, name='con_full', hcenter=True)
        # min_area = 1500 / 3840 / 2160 * self.screen_width * self.screen_height  # 按分辨率缩放
        # self.next_frame()  # 获取一帧用于计算掩膜尺寸
        # cropped = con_box.crop_frame(self.frame)  # 裁剪出协奏值环区域
        # h, w = cropped.shape[:2]  # 裁剪区域尺寸
        # center = (w // 2, h // 2)  # 中心点

        # # 预计算环形掩膜 (甜甜圈形状, 只依赖图像尺寸, 战斗中不变)
        # r1 = int(Decimal(str(h * 0.35119)).quantize(Decimal('0'), rounding=ROUND_DOWN))  # 内半径
        # r2 = int(Decimal(str(h * 0.42261)).quantize(Decimal('0'), rounding=ROUND_UP))  # 外半径
        # ring_mask = np.zeros((h, w), dtype=np.uint8)  # 创建掩膜
        # cv2.circle(ring_mask, center, r2, 255, -1)  # 填充外圆
        # cv2.circle(ring_mask, center, r1, 0, -1)  # 挖空内圆

        for slot in self._detected_characters:  # 为每个已识别角色预计算
            name = self._detected_characters[slot]  # 角色名
            module = CHARACTER_LIBRARY.get(name)  # 角色模块
            color_index = int(getattr(module, "ELEMENT", 0)) if module else 0  # 颜色索引
            self._ring_indices[slot] = color_index  # 缓存颜色索引
            color_range = CON_COLORS[color_index]  # 获取颜色范围
            lower = np.array([color_range['b'][0], color_range['g'][0], color_range['r'][0]], dtype="uint8")
            upper = np.array([color_range['b'][1], color_range['g'][1], color_range['r'][1]], dtype="uint8")
            self._con_data[slot] = {
                'lower': lower,  # 颜色下界 (numpy)
                'upper': upper,  # 颜色上界 (numpy)
                'color_index': color_index,  # 颜色索引
            }
            self.log_info(f"预计算槽位{slot} ({name}) 协奏数据: 颜色索引={color_index}")

    def _edit_character(self):  # 打开角色属性编辑器
        """打开角色编辑器对话框, 可修改角色定位、属性、共鸣链等, 保存到脚本文件。"""
        dialog = CharacterEditorDialog(parent=None)
        dialog.exec()

    def _create_new_axis(self):  # 创建新轴: 先选择角色, 再打开编辑器
        """打开角色选择对话框, 选择角色后打开轴编辑器。"""
        # 打开角色选择对话框
        char_dialog = CharacterSelectionDialog(parent=None)
        if char_dialog.exec():  # 用户点击确定
            selected_chars = char_dialog.selected_characters  # 获取选中的角色
            # 打开轴编辑器, 传入选中的角色
            editor = AxisEditorDialog(selected_characters=selected_chars, axis=Axis(), parent=None)
            if editor.exec():  # 用户点击关闭
                new_axis = editor.get_axis()
                self._current_axis = new_axis
                self.log_info(f"新轴已创建: 启动{len(new_axis.startup)}个动作, 循环{len(new_axis.loop)}个动作")

    def _import_axis(self):  # 导入轴: 从文件加载
        """打开文件对话框, 加载已有的轴文件。"""
        default_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'axis')  # 默认打开 src/axis 目录
        file_path, _ = QFileDialog.getOpenFileName(None, "导入轴", default_dir, "轴文件 (*.json)")
        if file_path:
            try:
                axis = Axis.load(file_path)
                self._current_axis = axis
                self.config["轴配置"] = file_path  # 保存路径到配置
                self.log_info(f"已加载轴: {file_path}")
                self.log_info(f"启动{len(axis.startup)}个动作, 循环{len(axis.loop)}个动作")
            except Exception as e:
                self.log_error(f"加载轴文件失败: {e}")

    def _edit_axis(self):  # 编辑轴: 选择已有轴文件, 打开编辑器修改
        """打开文件对话框选择轴文件, 从轴中提取角色后打开编辑器, 可直接修改已有动作。"""
        default_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'axis')  # 默认打开 src/axis 目录
        file_path, _ = QFileDialog.getOpenFileName(None, "编辑轴", default_dir, "轴文件 (*.json)")
        if not file_path:  # 用户取消
            return
        try:
            axis = Axis.load(file_path)  # 加载轴文件
        except Exception as e:
            self.log_error(f"加载轴文件失败: {e}")
            return
        # 从轴动作中提取所有角色名 (去重, 保持顺序, 最多3个)
        char_names = []
        for action in axis.startup + axis.loop:  # 遍历启动和循环阶段的所有动作
            if action.character_name not in char_names:  # 去重
                char_names.append(action.character_name)
        if not char_names:  # 轴中没有动作
            self.log_warning("该轴文件中没有动作, 无法编辑")
            return
        char_names = char_names[:3]  # 最多3个角色
        # 打开轴编辑器, 传入已有的角色和轴数据
        editor = AxisEditorDialog(selected_characters=char_names, axis=axis, parent=None)
        if editor.exec():  # 用户点击关闭
            edited_axis = editor.get_axis()
            self._current_axis = edited_axis
            self.config["轴配置"] = file_path  # 保存路径到配置
            self.log_info(f"轴已编辑: {file_path}, 启动{len(edited_axis.startup)}个动作, 循环{len(edited_axis.loop)}个动作")

    # ---- 脚本相关 ----
    def _execute_combat(self):  # 根据识别结果启动角色脚本, 并自动检测角色切换
        if not self._detected_characters:  # 还没有识别过角色, 先自动识别
            self._detect_characters()
        if not self._detected_characters:  # 识别后仍然没有角色
            self.log_warning("未识别到角色, 请确认角色图片已标记")
            return

        # 热重载角色脚本 (debug 模式下修改 .py 文件后按 F7 立即生效)
        for slot, name in self._detected_characters.items():
            module = CHARACTER_LIBRARY.get(name)
            if module:
                try:
                    importlib.reload(module)
                    self.log_info(f"已热重载角色脚本: {name}")
                except Exception as e:
                    self.log_warning(f"热重载 {name} 失败: {e}")

        # 检查战斗模式
        mode = self.config.get("战斗模式", "自动")
        if mode == "打轴":
            self._execute_axis_mode()  # 打轴模式
        else:
            self._execute_auto_mode()  # 自动模式

    def _execute_auto_mode(self):  # 自动模式: 使用调度算法自动切换角色
        """原有的自动模式逻辑, 使用 schedule_next_character 进行调度切换。"""
        # 清理旧的角色脚本线程 (daemon 线程无需等待, _combat_active=False 后它们会自行退出)
        self._script_threads = []  # 清空列表

        for slot, name in self._detected_characters.items():  # 遍历识别到的角色
            if not self._combat_active or not self.enabled:  # 战斗已停止则跳过
                break
            module = CHARACTER_LIBRARY.get(name)  # 从角色库获取脚本模块
            if module:  # 模块存在
                self.log_info(f"启动槽位{slot} 的角色脚本: {name} ({module.CHAR_TYPE})")
                self.info_set(f"角色{slot}", "执行中...")
                t = threading.Thread(target=self._run_script, args=(module, slot), daemon=True)
                t.start()  # 立即启动, 不等它结束, 多个角色脚本并行运行
                self._script_threads.append(t)  # 保存到实例变量
            else:
                self.log_warning(f"角色库中未找到: {name}")
                self.info_set(f"角色{slot}", "库中未找到")

        self._current_character_index = 0  # 重置当前角色追踪
        self._pending_resets = {}  # 清空待处理的重置
        self._switch_cooldowns = {}  # 清空切换冷却
        self._last_scheduled_slot = 0  # 重置上次调度角色
        for e in self._char_events.values():  # 战斗开始时清空所有事件, 所有脚本先挂起
            e.clear()

        while self._combat_active and self.enabled:  # 战斗激活期间持续检测角色切换
            self._process_pending_resets()  # 处理到期的攻击计数重置
            active = self._detect_active_character()  # 检测当前在场角色

            if active != 0 and active != self._current_character_index:  # 检测到外部角色切换 (排除初始未知状态)
                old = self._current_character_index
                self.log_info(f"检测到角色切换: {old} → {active}")
                if old != 0 and old in self._char_events:  # 不是首次检测, 让旧角色睡眠
                    self._char_events[old].clear()
                if old != 0:  # 不是首次检测, 才触发重置计时
                    self._pending_resets[old] = time.time() + 1.5  # 记录原角色的 1.5 秒截止时间
                self._current_character_index = active  # 更新当前角色
                if active in self._char_events:  # 唤醒新角色脚本
                    self._char_events[active].set()
            time.sleep(0.02)  # 每 50ms 检测一次

        for e in self._char_events.values():  # 先唤醒所有阻塞的脚本线程
            e.set()
        for t in self._script_threads:  # 等待所有角色脚本线程结束
            t.join(timeout=1)  # 每个最多等 1 秒
        self._script_threads = []  # 清空线程列表
        self._current_character_index = 0  # 清理追踪状态
        self._pending_resets = {}  # 清理待处理重置
        self._switch_cooldowns = {}  # 清理切换冷却
        for e in self._char_events.values():  # 战斗结束时清空所有事件
            e.clear()

    def _execute_axis_mode(self):  # 打轴模式: 按固定轴顺序执行动作
        """打轴模式: 按轴定义的顺序执行动作, 先启动阶段, 再循环阶段。"""
        # 加载轴
        axis_path = self.config.get("轴配置", "")
        if axis_path and os.path.isfile(axis_path):
            self._current_axis = Axis.load(axis_path)
        if not self._current_axis:
            self.log_warning("打轴模式未配置轴, 请先编辑轴")
            return

        # 验证角色匹配: 检查轴中的角色是否都已检测到
        axis_characters = set()  # 收集轴中所有角色名
        for action in self._current_axis.startup:
            axis_characters.add(action.character_name)
        for action in self._current_axis.loop:
            axis_characters.add(action.character_name)
        
        detected_names = set(self._detected_characters.values())  # 已检测到的角色名
        missing_characters = axis_characters - detected_names  # 轴中有但没检测到的角色
        if missing_characters:
            self.log_error(f"角色不匹配: 轴中需要 {missing_characters}, 但未检测到")
            return

        # 清理旧的角色脚本线程 (daemon 线程无需等待, _combat_active=False 后它们会自行退出)
        self._script_threads = []  # 清空列表

        # 启动所有角色脚本线程
        for slot, name in self._detected_characters.items():
            if not self._combat_active or not self.enabled:
                break
            module = CHARACTER_LIBRARY.get(name)
            if module:
                self.log_info(f"启动槽位{slot} 的角色脚本: {name}")
                t = threading.Thread(target=self._run_script, args=(module, slot), daemon=True)
                t.start()
                self._script_threads.append(t)  # 保存到实例变量

        # 初始化事件
        for e in self._char_events.values():
            e.clear()
        self._axis_done_events = {name: threading.Event() for name in self._detected_characters.values()}  # 为每个角色创建轴完成事件

        # 初始化攻击计数重置追踪
        self._current_character_index = 0  # 当前在场角色
        self._pending_resets = {}  # 待处理的攻击计数重置 {槽位: 截止时间戳}

        # 执行轴: 按顺序执行 startup → loop → loop2 → loop3 → finish → 回到 loop
        # 可空置阶段 (loop2/loop3/finish) 为空时用 loop 替代
        self._axis_phase = "startup"
        self._axis_index = 0
        self.log_info("开始执行轴: 启动阶段")
        self._fg_collector.start_measurement(len(self._current_axis.startup))  # 开始收集启动阶段

        # 阶段顺序定义
        phase_order = ["startup", "loop", "loop2", "loop3", "finish"]
        # 可空置阶段列表 (为空时用 loop 替代)
        optional_phases = {"loop2", "loop3", "finish"}

        while self._combat_active and self.enabled:
            self._process_pending_resets()  # 处理到期的攻击计数重置

            # 获取当前阶段的动作列表
            actions = getattr(self._current_axis, self._axis_phase)
            # 可空置阶段为空时, 用 loop 替代
            if not actions and self._axis_phase in optional_phases:
                actions = self._current_axis.loop

            # 检查是否还有动作
            if self._axis_index >= len(actions):
                self._fg_collector.complete_phase()  # 保存当前阶段的实测数据
                # 进入下一个阶段
                current_idx = phase_order.index(self._axis_phase)
                next_idx = current_idx + 1
                if next_idx >= len(phase_order):
                    # finish 执行完毕, 回到 loop 循环
                    next_idx = 1  # loop 的索引
                next_phase = phase_order[next_idx]
                self._axis_phase = next_phase
                self._axis_index = 0
                next_actions = getattr(self._current_axis, next_phase)
                if not next_actions and next_phase in optional_phases:
                    next_actions = self._current_axis.loop
                self.log_info(f"进入阶段: {next_phase} ({len(next_actions)} 个动作)")
                if not next_actions:  # 所有阶段都为空
                    self.log_warning("轴无可用动作, 执行结束")
                    break
                self._fg_collector.start_measurement(len(next_actions))
                continue

            # 执行当前动作
            action = actions[self._axis_index]
            self._execute_axis_action(action)
            self._axis_index += 1

        # 清理
        for e in self._char_events.values():  # 先唤醒所有阻塞的脚本线程
            e.set()
        for t in self._script_threads:
            t.join(timeout=1)
        self._script_threads = []  # 清空线程列表
        for e in self._char_events.values():
            e.clear()
        for e in self._axis_done_events.values():
            e.clear()
        self._axis_done_events = {}
        self._current_character_index = 0
        self._pending_resets = {}

    def _execute_axis_action(self, action):  # 执行轴中的单个动作
        """
        执行轴中的一个动作:
        1. 找到动作对应的角色槽位
        2. 如果下个动作角色不同, 切换角色事件
        3. 发送轴命令让角色执行指定动作
        4. 等待角色执行完成并获取结果
        """
        from src.character import set_axis_command, get_axis_result  # 导入轴命令函数

        char_name = action.character_name
        action_name = action.action_name

        # 找到角色对应的槽位
        target_slot = None
        for slot, name in self._detected_characters.items():
            if name == char_name:
                target_slot = slot
                break

        if target_slot is None:
            self.log_warning(f"轴动作 {char_name}.{action_name} 的角色未识别")
            return

        # 预览下一个动作, 判断是否同一角色连续执行
        actions = self._current_axis.startup if self._axis_phase == "startup" else self._current_axis.loop
        next_index = self._axis_index + 1
        same_char_next = (next_index < len(actions) and actions[next_index].character_name == char_name)
        self._axis_same_char_next = same_char_next  # 通知角色脚本是否需要跳过 wait_for_my_turn

        # 先清除角色事件, 确保角色会等待新命令 (threading.Event 不会自动重置)
        if target_slot in self._char_events:
            self._char_events[target_slot].clear()

        # 发送轴命令 (在唤醒角色之前, 避免竞态)
        set_axis_command(self, char_name, action_name)

        # 唤醒角色执行命令 (无论是否同一角色, 都通过事件同步)
        if target_slot in self._char_events:
            if not same_char_next or self._current_character_index != target_slot:
                # 角色切换: 让当前角色睡眠, 唤醒目标角色
                self.log_info(f"轴: 切换到 {char_name} 执行 {action_name}")
                old_slot = self._current_character_index
                if old_slot > 0 and old_slot in self._char_events:
                    self._pending_resets[old_slot] = time.time() + 1.0
                self._pending_resets.pop(target_slot, None)
                self._char_events[target_slot].set()  # 唤醒目标角色
                self._current_character_index = target_slot
            else:
                # 同一角色连续执行: 设置事件让角色继续
                self.log_info(f"轴: {char_name} 连续执行 {action_name}")
                self._char_events[target_slot].set()  # 唤醒角色执行新命令

        # 等待角色执行完成 (事件通知, 无需轮询)
        # TODO: 后续可添加超时机制, 但需要保证动作队列同步 (超时后等待角色完成再继续)
        done_event = self._axis_done_events.get(char_name)  # 获取该角色的完成事件
        result = None
        action_start_time = time.time()  # 记录动作开始时间, 用于实测 fg_time
        if done_event:  # 事件存在
            done_event.clear()  # 清除旧信号, 避免误唤醒
            done_event.wait()  # 无限等待, 直到角色脚本完成后 set()
            result = get_axis_result(self, char_name)  # 获取结果 (success, branch_id)

        actual_fg = time.time() - action_start_time  # 实测前台时间 (从发命令到收到完成信号)
        # 解析结果: result 现在是 (success, branch_id) 元组
        branch_id = "default"
        success = False
        if result is not None:
            if isinstance(result, tuple):
                success, branch_id = result
            else:
                success = result
        self._fg_collector.record_measurement(char_name, action_name, actual_fg, branch_id)  # 记录到收集器 (含分支标识)

        if result is not None:
            if success:
                self.log_info(f"轴动作 {char_name}.{action_name}[{branch_id}] 执行成功, 实测fg={actual_fg:.2f}s")
            else:
                self.log_error(f"轴动作 {char_name}.{action_name}[{branch_id}] 执行失败 (条件不满足)")

    def _detect_active_character(self):  # 检测当前在场角色编号, 返回 0 表示未检测到
        for i in range(1, 4):  # 依次检查角色 1/2/3
            if self._char_data[i]['switchable']:  # 检查该角色的 switchable 标记
                return i  # 返回当前在场角色编号
        return 0  # 没有角色标记为可切换

    def _process_pending_resets(self):  # 检查到期的重置, 直接重置攻击计数
        expired = [idx for idx, deadline in self._pending_resets.items() if time.time() >= deadline]  # 找出已到期的
        for old_idx in expired:  # 遍历每个到期的重置
            del self._pending_resets[old_idx]  # 先移除
            self._char_data[old_idx]['attack_counts'] = [0, 0, 0, 0]  # 重置攻击计数
            self.log_info(f"角色{old_idx} 动作结束后 1 秒未切回, 攻击计数已重置")

    def schedule_next_character(self, force=False):  # 角色调度算法: 决定下一个上场角色
        """
        调度规则:
        1. 被切换离场的角色有 1 秒冷却, 冷却期间不可再上场 (force=True 时忽略)
        2. 不可将同一角色的两个动作连续安排, 除非无人可切
        3. 按 SwitchPriority 优先级排序, 高优先级先被切换
        :param force: 是否为强制切换 (特殊技能触发), True 时忽略冷却
        返回下一个应上场的槽位编号 (1/2/3), 无可用角色返回 0
        """
        now = time.time()  # 获取当前时间
        available_slots = list(self._detected_characters.keys())  # 所有已识别角色的槽位
        if len(available_slots) <= 1:  # 只有一个或没有角色
            return available_slots[0] if available_slots else 0  # 唯一角色直接上场

        candidates = list(available_slots)  # 从全部角色开始筛选

        # 第一轮过滤: 排除冷却中的角色 (force=True 时跳过此轮)
        if not force:  # 非强制切换才检查冷却
            non_cooldown = [s for s in candidates if now >= self._switch_cooldowns.get(s, 0)]
            candidates = non_cooldown if non_cooldown else candidates  # 全员冷却中则忽略冷却

        # 第二轮过滤: 排除上一个被调度的角色 (避免连续安排同一角色)
        non_repeat = [s for s in candidates if s != self._last_scheduled_slot]
        if non_repeat:  # 有不重复的候选
            candidates = non_repeat  # 使用不重复的候选
        # 否则全员都是上一个人, 允许连续

        # 按 SwitchPriority 降序排序, 取最高优先级
        best_slot = 0  # 最佳槽位
        best_priority = -1  # 最佳优先级
        for slot in candidates:  # 遍历候选槽位
            name = self._detected_characters.get(slot)  # 获取角色名
            module = CHARACTER_LIBRARY.get(name)  # 获取角色模块
            if module:  # 模块存在
                priority = getattr(module, "SWITCH_PRIORITY", 0)  # 读取切换优先级
                if priority > best_priority:  # 找到更高优先级
                    best_priority = priority  # 更新最佳优先级
                    best_slot = slot  # 更新最佳槽位

        if best_slot > 0:  # 找到了下一个上场角色
            if not force:  # 非强制切换才设置冷却
                self._switch_cooldowns[best_slot] = now + 1.0  # 设置 1 秒切换冷却
            self._last_scheduled_slot = best_slot  # 记录上次调度的角色
            mode = "强制" if force else "普通"  # 调度模式
            target_name = self._detected_characters.get(best_slot)  # 目标角色名
            self.log_info(f"{mode}调度: 槽位{best_slot} ({target_name}) 上场, 优先级={best_priority}")

        return best_slot  # 返回下一个上场的槽位

    def reset_all_characters(self):  # 循环完成: 重置所有角色的优先级和状态
        """
        由角色脚本调用, 当一轮循环完成时重置所有角色的状态。
        重置内容包括: 切换优先级、技能就绪标记、攻击计数、切换冷却、动作结束时间等。
        """
        for name, module in CHARACTER_LIBRARY.items():  # 遍历角色库中的每个角色
            module.SWITCH_PRIORITY = getattr(module, "_default_switch_priority", SwitchPriority.NORMAL)  # 恢复默认优先级
        for slot in self._detected_characters:  # 遍历所有已识别角色的槽位
            self._switch_cooldowns.pop(slot, None)  # 清除切换冷却
            self._char_data[slot]['switchable'] = False  # 重置可切换标记
            self._char_data[slot]['skill_ready'] = False  # 重置技能就绪标记
            self._char_data[slot]['attack_counts'] = [0, 0, 0, 0]  # 重置攻击计数
            self._char_data[slot]['states'] = {}  # 清空自定义状态
        self._last_scheduled_slot = 0  # 重置上次调度角色
        self._character_jumping = False  # 重置跳跃状态
        self.log_info("循环完成, 所有角色状态已重置")

    # ---- 协奏值检测 ----
    def _count_rings(self, cropped, slot):  # 使用预计算数据计算环面积和状态 (用于校准)
        """
        使用预计算的掩膜和颜色边界计算环面积和状态。
        仅在首次校准时调用, 战斗中不需要。
        :param cropped: 裁剪后的协奏值区域图像
        :param slot: 角色槽位编号
        :return: (检测到的区域面积, 是否为完整环)
        """
        data = self._con_data.get(slot)  # 获取预计算数据
        if not data:  # 无预计算数据
            return 0, False
        masked_image = cv2.bitwise_and(cropped, cropped, mask=data['mask'])  # 应用预计算的环形掩膜
        raw_mask = cv2.inRange(masked_image, data['lower'], data['upper'])  # 颜色过滤
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))  # 3x3 矩形核
        closed_mask = cv2.morphologyEx(raw_mask, cv2.MORPH_CLOSE, kernel)  # 闭运算填充小间隙
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(closed_mask, connectivity=8)  # 连通域分析

        def is_full_ring(component_mask):  # 判断连通域是否形成完整环
            contours, _ = cv2.findContours(component_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)  # 找轮廓
            if len(contours) != 1:  # 不是单个轮廓
                return False
            contour = contours[0]  # 取唯一轮廓
            epsilon = 0.05 * cv2.arcLength(contour, True)  # 近似精度
            approx = cv2.approxPolyDP(contour, epsilon, True)  # 多边形近似
            if not cv2.isContourConvex(approx) or len(approx) < 4:  # 非凸或顶点太少
                return False
            return True  # 满足条件, 是完整环

        ring_count = 0  # 环计数
        is_full = False  # 是否完整环
        the_area = 0  # 检测到的面积
        for label in range(1, num_labels):  # 遍历每个连通域
            x, y, width, height, area = stats[label, :5]  # 获取统计信息
            bounding_box_area = width * height  # 外接矩形面积
            component_mask = (labels == label).astype(np.uint8) * 255  # 创建该连通域的掩膜
            if bounding_box_area >= data['min_area']:  # 面积足够大
                if is_full_ring(component_mask):  # 是完整环
                    is_full = True  # 标记为完整
                the_area = area  # 记录面积
                ring_count += 1  # 环计数加一
        if ring_count > 1:  # 检测到多个环 (异常)
            is_full = False  # 重置完整标记
            the_area = 0  # 重置面积
            self.log_warning(f"协奏值检测到多个环: {ring_count}")
        return the_area, is_full

    def get_current_con(self, slot):  # 获取指定槽位角色的协奏值百分比 (0.0~1.0)
        """
        获取指定槽位角色的协奏值百分比。使用预计算数据, 只需截帧+裁剪+找色。
        :param slot: 角色槽位编号 (1/2/3)
        :return: 协奏值百分比 (0.0 到 1.0)
        """
        data = self._con_data.get(slot)  # 获取预计算数据
        if not data:  # 无预计算数据
            return 0
        self.next_frame()  # 获取新帧
        cropped = data['box'].crop_frame(self.frame)  # 裁剪出协奏值环区域
        color_index = data['color_index']  # 预计算的颜色索引
        area, is_full = self._count_rings(cropped, slot)  # 使用预计算数据计算面积和状态
        percent = 0  # 百分比
        if is_full:  # 检测到完整环
            percent = 1  # 百分比为 1
            self._con_full_size[str(color_index)] = area  # 记录充满时的大小
        elif self._con_full_size[str(color_index)] > 0:  # 未充满但有参考值
            percent = area / self._con_full_size[str(color_index)]  # 按比例计算
            if percent >= 1:  # 未充满但比例 >= 1 (异常)
                percent = 0.99  # 修正为 0.99
        return min(percent, 1.0)  # 限制最大值为 1.0

    def is_con_full(self, slot):  # 检查指定槽位角色的协奏值是否已满
        """
        在 forte_location 区域找色, 颜色占比 >= 99% 认为能量已满。
        :param slot: 角色槽位编号 (1/2/3)
        :return: True 如果协奏值已满, 否则 False
        """
        # ---- suisui 特殊检查: 队伍中有 suisui 时, 非 suisui 的副C/治疗通过 suisui 区域找色判断 ----
        suisui_slot = None  # suisui 所在槽位
        for s, n in self._detected_characters.items():  # 遍历已识别角色
            if n == "suisui":  # 找到 suisui
                suisui_slot = s  # 记录槽位
                break
        suisui_check = True  # 默认通过, 不影响原有逻辑
        if suisui_slot is not None and slot != suisui_slot:  # 队伍有 suisui 且检查的不是 suisui 自己
            char_name = self._detected_characters[slot]  # 当前槽位角色名
            module = CHARACTER_LIBRARY.get(char_name)  # 获取角色模块
            char_type = getattr(module, "CHAR_TYPE", None)  # 获取角色定位
            if char_type in (CharType.SUB_DPS, CharType.HEALER):  # 副C 或 治疗
                location_box = get_location_box(self, f"suisui_buff_location")  # 获取 suisui 槽位区域
                if location_box:  # 区域存在
                    suisui_check = not check_skill_available_binary(self,"suisui_buff",threshold=180, white_threshold=0.5)
                else:
                    suisui_check = False  # 区域不存在, 检查不通过

        # ---- forte_location 找色判断能量是否满 ----
        data = self._con_data.get(slot)  # 获取预计算数据
        if not data:  # 无预计算数据
            return False
        forte_box = get_location_box(self, "forte_location")  # 获取能量条区域
        if not forte_box:  # 区域不存在
            self.log_warning(f"forte_location 区域不存在, 无法检测协奏值")
            return False
        self.next_frame()  # 获取新帧
        cropped = forte_box.crop_frame(self.frame)  # 裁剪出能量条区域
        color_mask = cv2.inRange(cropped, data['lower'], data['upper'])  # 按角色属性颜色过滤
        total_pixels = cropped.shape[0] * cropped.shape[1]  # 区域总像素数
        color_pixels = cv2.countNonZero(color_mask)  # 匹配颜色的像素数
        pct = color_pixels / total_pixels if total_pixels > 0 else 0  # 颜色占比
        is_full = pct >= 0.99  # 99% 以上认为能量已满
        return suisui_check and is_full  # 与上 suisui 检查结果

    def _run_script(self, module, slot):  # 执行角色库中的脚本模块
        try:
            module.run(self)  # 调用模块的 run 函数, 传入 task
        except Exception as e:
            self.log_error(f"槽位{slot} 角色脚本出错: {e}")

    # ---- 任务主逻辑 ----
    def run(self):  # 任务启用后执行
        self._unregister_hotkey()  # 确保旧热键已注销 (防止重启时残留)
        if not self._register_hotkey():  # 注册热键
            return  # 注册失败就退出

        hotkey_name = self.config.get("启停热键", "F7")
        lib_count = len(CHARACTER_LIBRARY)  # 角色库中的角色数量
        self._combat_active = False  # 初始为停止状态
        self.log_info(f"启动成功, 按 {hotkey_name} 开始战斗 (角色库: {lib_count} 个角色)", notify=True)
        self.info_set("状态", f"已停止 (按 {hotkey_name} 开始)")
        self.info_set("启停热键", hotkey_name)
        self.info_set("角色库", f"{lib_count} 个角色")
        self._update_hotkey_button(hotkey_name)  # 更新按钮文字 (通过 config_type 支持懒加载)

        self._detect_characters()  # 预先识别角色 (不等 F7, 节省战斗启动时间)

        msg = ctypes.wintypes.MSG()  # Windows 消息结构体
        combat_thread = None  # 战斗脚本的子线程, 初始为空

        while self.enabled and not self._run_stopped:  # 主循环, 任务被禁用或销毁时退出
            # 检查是否有热键消息 (PeekMessageW 非阻塞, PM_REMOVE=1)
            while ctypes.windll.user32.PeekMessageW(ctypes.byref(msg), None, WM_HOTKEY, WM_HOTKEY, 1):
                msg_vk = (msg.lParam >> 16) & 0xFFFF  # lParam 高位字 = 触发的虚拟键码
                msg_mod = msg.lParam & 0xFFFF  # lParam 低位字 = 修饰键标志 (MOD_ALT/CTRL/SHIFT)
                self.log_info(f"[热键] 收到 WM_HOTKEY: 消息id={msg.wParam} 本任务id={self._hotkey_id} vk=0x{msg_vk:02X} mod=0x{msg_mod:02X} 战斗状态={self._combat_active}")  # 诊断: 记录每条热键消息, 用于排查幽灵触发
                if msg.wParam != self._hotkey_id:  # 不是本任务注册的热键 → 忽略 (防御队列混入其他组件的热键消息)
                    self.log_warning(f"[热键] 忽略非本任务的热键消息: 消息id={msg.wParam} vk=0x{msg_vk:02X}")
                    continue
                if self._combat_active:  # 正在战斗 → 彻底停止并重置
                    self._combat_active = False  # 先置标记, 子线程中的脚本会检测到此变化并退出循环
                    if combat_thread and combat_thread.is_alive():  # 如果子线程还在运行
                        combat_thread.join(timeout=2)  # 等待子线程结束, 最多等 2 秒
                    self._reset_combat_state()  # 重置所有战斗状态到初始
                    self.log_info("战斗已停止, 状态已重置", notify=True)
                    self.info_set("状态", f"已停止 (按 {hotkey_name} 开始)")
                else:  # 已停止 → 开始战斗
                    self._combat_active = True  # 设置标记
                    self.log_info("战斗开始!", notify=True)
                    self.info_set("状态", "战斗中")
                    # 在子线程中执行战斗脚本, 主线程继续监听热键
                    combat_thread = threading.Thread(target=self._execute_combat, daemon=True)
                    combat_thread.start()

            time.sleep(0.02)  # 避免 CPU 占用过高 (用 time.sleep 而非 self.sleep, 防止框架暂停时卡住)

        self._unregister_hotkey()  # 退出时注销热键
        self._combat_active = False
        self.log_info("任务已退出")

    def on_destroy(self):  # 任务销毁时清理
        self._run_stopped = True  # 通知 run() 循环退出
        self._combat_active = False  # 停止战斗 (角色脚本检测到此标记后退出)
        self._unregister_hotkey()  # 注销热键
        # 唤醒所有阻塞在 event.wait() 的角色脚本线程
        for e in self._char_events.values():
            e.set()
        # 等待角色脚本线程结束 (避免进程挂起)
        for t in self._script_threads:
            if t.is_alive():
                t.join(timeout=1)
        self._script_threads = []
        # 任务销毁时关闭 WGC, 释放 GPU 资源 (下次启用任务时会重建)
        try:
            method = getattr(self.executor, 'method', None)
            if method and hasattr(method, 'close'):
                method.close()
                self.log_info("任务销毁, 已关闭 WGC 捕获会话")
        except Exception as e:
            self.log_warning(f"关闭 WGC 失败: {e}")
        self._trim_memory()  # 回收 Python 进程内存缓存
