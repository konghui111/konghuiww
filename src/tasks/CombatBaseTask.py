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
from src.character import CHARACTER_LIBRARY, detect_hotkey, ACTION_REGISTRY, CharType, get_location_box, calculate_binary_percentage, check_skill_available_binary  # 导入角色库和角色检测函数

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


# ==== 战斗基类 (共享逻辑) ====
class CombatBaseTask(MyBaseTask):
    """
    战斗任务基类, 包含所有战斗模式共享的逻辑:
    - 热键注册/监听/F7 启停
    - 角色检测 + 协奏数据预计算
    - 角色脚本线程管理
    - 战斗状态重置 + 内存回收
    - 协奏值检测 (is_con_full)
    子类只需实现 _execute_combat() 方法即可。
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.icon = FluentIcon.PLAY

        # ---- 默认配置 (子类可追加) ----
        self.default_config.update({
            "启停热键": "F7",  # 控制战斗开始/停止的按键
        })
        self.config_description.update({
            "启停热键": "点击按钮后按下要设置的键, 按此键开始/停止战斗。",
        })
        self.config_type.update({
            "启停热键": {
                "type": "button",
                "text": "当前: F7",  # 默认值, run() 执行后更新为实际保存的值
                "callback": self._capture_hotkey,
            },
        })

        # ---- 状态变量 ----
        self._combat_active = False  # 战斗是否激活 (热键切换)
        self._hotkey_btn = None  # 缓存按钮引用
        self._hotkey_id = 0  # Windows 热键 ID, 0=未注册
        self._run_stopped = False  # run() 循环退出标志 (on_destroy 设置)
        self._detected_characters = {}  # 识别到的角色 {槽位编号: 角色名}
        self._script_threads = []  # 角色脚本线程列表

        # ---- 角色协同变量 ----
        self._char_data = {  # 按槽位组织的角色协同数据
            1: {'switchable': False, 'skill_ready': False, 'attack_counts': [0, 0, 0, 0], 'states': {}},
            2: {'switchable': False, 'skill_ready': False, 'attack_counts': [0, 0, 0, 0], 'states': {}},
            3: {'switchable': False, 'skill_ready': False, 'attack_counts': [0, 0, 0, 0], 'states': {}},
        }
        self._character_jumping = False  # 角色跳跃状态
        self._current_character_index = 0  # 当前检测到的在场角色编号
        self._pending_resets = {}  # 待处理的攻击计数重置
        self._char_events = {1: threading.Event(), 2: threading.Event(), 3: threading.Event()}  # 每个角色的唤醒事件

        # ---- 协奏值相关 ----
        self._con_full_size = {str(i): 0 for i in range(len(CON_COLORS))}  # 各属性协奏值环充满时的大小记录
        self._ring_indices = {}  # 各槽位角色的协奏值环颜色索引
        self._con_data = {}  # 预计算的协奏检测数据

    # ---- 子类必须实现 ----
    def _execute_combat(self):
        """子类实现具体的战斗逻辑 (自动模式/打轴模式)"""
        raise NotImplementedError("子类必须实现 _execute_combat()")

    # ---- 重置战斗状态 ----
    def _reset_combat_state(self):
        """将所有战斗运行时状态恢复到初始值, 角色识别和预计算数据保留"""
        self._combat_active = False  # 战斗未激活
        # 释放可能残留的鼠标和按键状态
        try:
            self.mouse_up(key="left")
            self.mouse_up(key="right")
            for k in ("e", "r", "q", "space"):
                self.send_key_up(k)
        except Exception:
            pass
        self._char_data = {
            1: {'switchable': False, 'skill_ready': False, 'attack_counts': [0, 0, 0, 0], 'states': {}},
            2: {'switchable': False, 'skill_ready': False, 'attack_counts': [0, 0, 0, 0], 'states': {}},
            3: {'switchable': False, 'skill_ready': False, 'attack_counts': [0, 0, 0, 0], 'states': {}},
        }
        self._character_jumping = False
        self._current_character_index = 0
        self._pending_resets = {}
        for e in self._char_events.values():
            e.clear()
        self._trim_memory()

    def _trim_memory(self):
        """回收 Python 进程自身的内存缓存"""
        try:
            ctypes.windll.psapi.EmptyWorkingSet(ctypes.windll.kernel32.GetCurrentProcess())
            self.log_info("已回收 Python 进程的内存缓存")
        except Exception as e:
            self.log_warning(f"内存回收失败: {e}")

    # ---- 热键管理 ----
    def _register_hotkey(self):
        """注册全局热键"""
        name = self.config.get("启停热键", "F7")
        vk = _get_vk(name)
        if vk == 0:
            self.log_warning(f"无法注册热键: {name}")
            return False
        self._hotkey_id = 0x1001
        ok = ctypes.windll.user32.RegisterHotKey(None, self._hotkey_id, MOD_NONE, vk)
        if not ok:
            self.log_warning(f"热键 {name} 注册失败, 可能已被其他程序占用", notify=True)
            self._hotkey_id = 0
            return False
        return True

    def _unregister_hotkey(self):
        """注销全局热键"""
        if self._hotkey_id:
            ctypes.windll.user32.UnregisterHotKey(None, self._hotkey_id)
            self._hotkey_id = 0

    def _capture_hotkey(self):
        """点击设置热键按钮时弹出捕获窗口"""
        dialog = _HotkeyCaptureDialog()
        if dialog.exec() and dialog.hotkey:
            self.config["启停热键"] = dialog.hotkey
            self._update_hotkey_button(dialog.hotkey)
            self.log_info(f"热键已设置为: {dialog.hotkey}")

    def _update_hotkey_button(self, hotkey):
        """更新按钮显示当前热键"""
        self.config_type["启停热键"]["text"] = f"当前: {hotkey}"
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
    def _detect_characters(self):
        """从角色库中识别当前队伍中的角色及其槽位"""
        try:
            frame = self.frame
            if frame is None:
                self.log_warning("无法获取游戏画面, 请确认游戏窗口已连接并启动")
                return
        except Exception as e:
            self.log_warning(f"获取游戏画面失败: {e}, 请确认游戏窗口已连接")
            return

        self._detected_characters = {}
        for name, module in CHARACTER_LIBRARY.items():
            char_name = module.CHARACTER_NAME
            char_type = module.CHAR_TYPE
            try:
                hotkey = detect_hotkey(self, char_name)
            except Exception as e:
                self.log_warning(f"检测角色 {char_name} 时出错: {e}")
                continue
            if hotkey:
                slot = int(hotkey)
                self._detected_characters[slot] = name
                self.info_set(f"槽位{slot}", f"{char_name} ({char_type})")
        if not self._detected_characters:
            self.log_warning("未识别到任何角色, 请确认角色图片已标记")
        else:
            summary = ", ".join(f"槽位{slot}: {name}" for slot, name in sorted(self._detected_characters.items()))
            self.log_info(f"角色识别完成: {summary}")
            self._precompute_con_data()

    def _precompute_con_data(self):
        """角色识别完成后调用, 预计算每个槽位的颜色边界"""
        self._con_data = {}
        for slot in self._detected_characters:
            name = self._detected_characters[slot]
            module = CHARACTER_LIBRARY.get(name)
            color_index = int(getattr(module, "ELEMENT", 0)) if module else 0
            self._ring_indices[slot] = color_index
            color_range = CON_COLORS[color_index]
            lower = np.array([color_range['b'][0], color_range['g'][0], color_range['r'][0]], dtype="uint8")
            upper = np.array([color_range['b'][1], color_range['g'][1], color_range['r'][1]], dtype="uint8")
            self._con_data[slot] = {
                'lower': lower,
                'upper': upper,
                'color_index': color_index,
            }
            self.log_info(f"预计算槽位{slot} ({name}) 协奏数据: 颜色索引={color_index}")

    # ---- 脚本执行 ----
    def _run_script(self, module, slot):
        """执行角色库中的脚本模块"""
        try:
            module.run(self)
        except Exception as e:
            self.log_error(f"槽位{slot} 角色脚本出错: {e}")

    def schedule_next_character(self, force=False):
        """角色调度 (基类空实现, 打轴模式不需要; 自动模式子类重写)"""
        pass

    def _prepare_combat(self):
        """战斗前的准备工作: 识别角色 + 热重载脚本, 返回是否准备好"""
        if not self._detected_characters:
            self._detect_characters()
        if not self._detected_characters:
            self.log_warning("未识别到角色, 请确认角色图片已标记")
            return False
        # 热重载角色脚本
        for slot, name in self._detected_characters.items():
            module = CHARACTER_LIBRARY.get(name)
            if module:
                try:
                    importlib.reload(module)
                    self.log_info(f"已热重载角色脚本: {name}")
                except Exception as e:
                    self.log_warning(f"热重载 {name} 失败: {e}")
        return True

    def _start_script_threads(self):
        """启动所有角色脚本线程"""
        self._script_threads = []
        for slot, name in self._detected_characters.items():
            if not self._combat_active or not self.enabled:
                break
            module = CHARACTER_LIBRARY.get(name)
            if module:
                self.log_info(f"启动槽位{slot} 的角色脚本: {name}")
                t = threading.Thread(target=self._run_script, args=(module, slot), daemon=True)
                t.start()
                self._script_threads.append(t)

    def _cleanup_script_threads(self):
        """清理角色脚本线程"""
        for e in self._char_events.values():
            e.set()
        for t in self._script_threads:
            if t.is_alive():
                t.join(timeout=1)
        self._script_threads = []
        for e in self._char_events.values():
            e.clear()

    def _process_pending_resets(self):
        """检查到期的重置, 直接重置攻击计数"""
        expired = [idx for idx, deadline in self._pending_resets.items() if time.time() >= deadline]
        for old_idx in expired:
            del self._pending_resets[old_idx]
            self._char_data[old_idx]['attack_counts'] = [0, 0, 0, 0]
            self.log_info(f"角色{old_idx} 动作结束后 1 秒未切回, 攻击计数已重置")

    # ---- 协奏值检测 ----
    def is_con_full(self, slot):
        """检查指定槽位角色的协奏值是否已满 (forte_location 找色 >= 99%)"""
        # suisui 特殊检查
        suisui_slot = None
        for s, n in self._detected_characters.items():
            if n == "suisui":
                suisui_slot = s
                break
        suisui_check = True
        if suisui_slot is not None and slot != suisui_slot:
            char_name = self._detected_characters[slot]
            module = CHARACTER_LIBRARY.get(char_name)
            char_type = getattr(module, "CHAR_TYPE", None)
            if char_type in (CharType.SUB_DPS, CharType.HEALER):
                location_box = get_location_box(self, "suisui_buff_location")
                if location_box:
                    suisui_check = not check_skill_available_binary(self, "suisui_buff", threshold=180, white_threshold=0.5)
                else:
                    suisui_check = False

        # forte_location 找色
        data = self._con_data.get(slot)
        if not data:
            return False
        forte_box = get_location_box(self, "forte_location")
        if not forte_box:
            self.log_warning("forte_location 区域不存在, 无法检测协奏值")
            return False
        self.next_frame()
        cropped = forte_box.crop_frame(self.frame)
        color_mask = cv2.inRange(cropped, data['lower'], data['upper'])
        total_pixels = cropped.shape[0] * cropped.shape[1]
        color_pixels = cv2.countNonZero(color_mask)
        pct = color_pixels / total_pixels if total_pixels > 0 else 0
        is_full = pct >= 0.99
        return suisui_check and is_full

    # ---- 任务主逻辑 ----
    def run(self):
        """任务启用后执行: 注册热键 → 识别角色 → 等待 F7 → 启动战斗"""
        self._unregister_hotkey()
        if not self._register_hotkey():
            return

        hotkey_name = self.config.get("启停热键", "F7")
        lib_count = len(CHARACTER_LIBRARY)
        self._combat_active = False
        self.log_info(f"启动成功, 按 {hotkey_name} 开始战斗 (角色库: {lib_count} 个角色)", notify=True)
        self.info_set("状态", f"已停止 (按 {hotkey_name} 开始)")
        self.info_set("启停热键", hotkey_name)
        self.info_set("角色库", f"{lib_count} 个角色")
        self._update_hotkey_button(hotkey_name)

        self._detect_characters()  # 预先识别角色

        msg = ctypes.wintypes.MSG()
        combat_thread = None

        while self.enabled and not self._run_stopped:
            while ctypes.windll.user32.PeekMessageW(ctypes.byref(msg), None, WM_HOTKEY, WM_HOTKEY, 1):
                msg_vk = (msg.lParam >> 16) & 0xFFFF
                msg_mod = msg.lParam & 0xFFFF
                self.log_info(f"[热键] 收到 WM_HOTKEY: 消息id={msg.wParam} 本任务id={self._hotkey_id} vk=0x{msg_vk:02X} mod=0x{msg_mod:02X} 战斗状态={self._combat_active}")
                if msg.wParam != self._hotkey_id:
                    self.log_warning(f"[热键] 忽略非本任务的热键消息: 消息id={msg.wParam} vk=0x{msg_vk:02X}")
                    continue
                if self._combat_active:
                    self._combat_active = False
                    if combat_thread and combat_thread.is_alive():
                        combat_thread.join(timeout=2)
                    self._reset_combat_state()
                    self.log_info("战斗已停止, 状态已重置", notify=True)
                    self.info_set("状态", f"已停止 (按 {hotkey_name} 开始)")
                else:
                    self._combat_active = True
                    self.log_info("战斗开始!", notify=True)
                    self.info_set("状态", "战斗中")
                    combat_thread = threading.Thread(target=self._execute_combat, daemon=True)
                    combat_thread.start()

            time.sleep(0.02)

        self._unregister_hotkey()
        self._combat_active = False
        self.log_info("任务已退出")

    def on_destroy(self):
        """任务销毁时清理"""
        self._run_stopped = True
        self._combat_active = False
        self._unregister_hotkey()
        for e in self._char_events.values():
            e.set()
        for t in self._script_threads:
            if t.is_alive():
                t.join(timeout=1)
        self._script_threads = []
        # 任务销毁时关闭 WGC
        try:
            method = getattr(self.executor, 'method', None)
            if method and hasattr(method, 'close'):
                method.close()
                self.log_info("任务销毁, 已关闭 WGC 捕获会话")
        except Exception as e:
            self.log_warning(f"关闭 WGC 失败: {e}")
        self._trim_memory()
