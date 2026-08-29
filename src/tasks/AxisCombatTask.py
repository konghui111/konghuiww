import os  # 导入操作系统模块
import threading  # 导入线程模块
import time  # 导入时间模块

from PySide6.QtWidgets import QFileDialog  # 导入文件对话框
from qfluentwidgets import FluentIcon  # 导入图标

from src.tasks.CombatBaseTask import CombatBaseTask, CON_COLORS  # 导入基类
from src.character import CHARACTER_LIBRARY  # 导入角色库
from src.tasks.AxisEditor import Axis  # 导入轴数据结构
from src.character.fg_time_collector import FgTimeCollector  # 导入 fg_time 收集器


# ==== 打轴战斗任务 ====
class AxisCombatTask(CombatBaseTask):
    """打轴模式: 按固定轴顺序执行动作, 先启动阶段, 再循环阶段。"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "打轴战斗"
        self.description = "按轴定义的顺序执行角色动作, 支持启动/循环/结束阶段。"

        # ---- 追加配置 ----
        self.default_config.update({
            "导入轴": "导入轴",
        })
        self.config_description.update({
            "导入轴": "从文件加载已有的轴配置。",
        })
        self.config_type.update({
            "导入轴": {
                "type": "button",
                "text": "导入轴",
                "callback": self._import_axis,
            },
        })

        # ---- 轴命令机制 ----
        self._axis_command = {}  # 轴命令 {角色名: 动作名}
        self._axis_result = {}  # 轴结果 {角色名: 是否成功}
        self._axis_done_events = {}  # 轴完成事件 {角色名: Event}
        self._axis_same_char_next = False  # 下个轴动作是否同一角色

        # ---- 打轴模式相关 ----
        self._current_axis = None  # 当前加载的轴对象
        self._axis_phase = "startup"  # 当前轴阶段
        self._axis_index = 0  # 当前轴动作索引

        # ---- fg_time 收集器 ----
        self._fg_collector = FgTimeCollector()

    # ---- 重置时追加轴相关状态 ----
    def _reset_combat_state(self):
        super()._reset_combat_state()
        self._axis_command = {}
        self._axis_result = {}
        self._axis_done_events = {}
        self._axis_same_char_next = False
        self._axis_phase = "startup"
        self._axis_index = 0

    # ---- 轴管理 UI ----
    def _import_axis(self):
        """导入轴: 从文件加载"""
        default_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'axis')
        file_path, _ = QFileDialog.getOpenFileName(None, "导入轴", default_dir, "轴文件 (*.json)")
        if file_path:
            try:
                axis = Axis.load(file_path)
                self._current_axis = axis
                self.config["轴配置"] = file_path
                self.log_info(f"已加载轴: {file_path}")
                self.log_info(f"启动{len(axis.startup)}个动作, 循环{len(axis.loop)}个动作")
            except Exception as e:
                self.log_error(f"加载轴文件失败: {e}")

    # ---- 打轴模式核心逻辑 ----
    def _execute_combat(self):
        """打轴模式入口: 识别角色 → 加载轴 → 执行轴动作"""
        if not self._prepare_combat():
            return

        # 加载轴
        axis_path = self.config.get("轴配置", "")
        if axis_path and os.path.isfile(axis_path):
            self._current_axis = Axis.load(axis_path)
        if not self._current_axis:
            self.log_warning("打轴模式未配置轴, 请先编辑轴")
            return

        # 验证角色匹配
        axis_characters = set()
        for action in self._current_axis.startup:
            axis_characters.add(action.character_name)
        for action in self._current_axis.loop:
            axis_characters.add(action.character_name)
        detected_names = set(self._detected_characters.values())
        missing_characters = axis_characters - detected_names
        if missing_characters:
            self.log_error(f"角色不匹配: 轴中需要 {missing_characters}, 但未检测到")
            return

        # 启动角色脚本线程
        self._start_script_threads()

        # 初始化事件
        for e in self._char_events.values():
            e.clear()
        self._axis_done_events = {name: threading.Event() for name in self._detected_characters.values()}
        self._current_character_index = 0
        self._pending_resets = {}

        # 执行轴
        self._axis_phase = "startup"
        self._axis_index = 0
        self.log_info("开始执行轴: 启动阶段")
        self._fg_collector.start_measurement(len(self._current_axis.startup))

        phase_order = ["startup", "loop", "loop2", "loop3", "finish"]
        optional_phases = {"loop2", "loop3", "finish"}

        while self._combat_active and self.enabled:
            self._process_pending_resets()

            # 获取当前阶段的动作列表
            actions = getattr(self._current_axis, self._axis_phase)
            if not actions and self._axis_phase in optional_phases:
                actions = self._current_axis.loop

            # 检查是否还有动作
            if self._axis_index >= len(actions):
                self._fg_collector.complete_phase()
                current_idx = phase_order.index(self._axis_phase)
                next_idx = current_idx + 1
                if next_idx >= len(phase_order):
                    next_idx = 1  # 回到 loop
                next_phase = phase_order[next_idx]
                self._axis_phase = next_phase
                self._axis_index = 0
                next_actions = getattr(self._current_axis, next_phase)
                if not next_actions and next_phase in optional_phases:
                    next_actions = self._current_axis.loop
                self.log_info(f"进入阶段: {next_phase} ({len(next_actions)} 个动作)")
                if not next_actions:
                    self.log_warning("轴无可用动作, 执行结束")
                    break
                self._fg_collector.start_measurement(len(next_actions))
                continue

            # 执行当前动作
            action = actions[self._axis_index]
            self._execute_axis_action(action)
            self._axis_index += 1

        # 清理
        self._cleanup_script_threads()
        for e in self._axis_done_events.values():
            e.clear()
        self._axis_done_events = {}
        self._current_character_index = 0
        self._pending_resets = {}

    def _execute_axis_action(self, action):
        """执行轴中的单个动作"""
        from src.character import set_axis_command, get_axis_result

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
        actions = getattr(self._current_axis, self._axis_phase)
        if not actions:
            actions = self._current_axis.loop
        next_index = self._axis_index + 1
        same_char_next = (next_index < len(actions) and actions[next_index].character_name == char_name)
        self._axis_same_char_next = same_char_next

        # 清除角色事件
        if target_slot in self._char_events:
            self._char_events[target_slot].clear()

        # 发送轴命令
        set_axis_command(self, char_name, action_name)

        # 唤醒角色
        if target_slot in self._char_events:
            if not same_char_next or self._current_character_index != target_slot:
                self.log_info(f"轴: 切换到 {char_name} 执行 {action_name}")
                old_slot = self._current_character_index
                if old_slot > 0 and old_slot in self._char_events:
                    self._pending_resets[old_slot] = time.time() + 1.0
                self._pending_resets.pop(target_slot, None)
                self._char_events[target_slot].set()
                self._current_character_index = target_slot
            else:
                self.log_info(f"轴: {char_name} 连续执行 {action_name}")
                self._char_events[target_slot].set()

        # 等待完成
        done_event = self._axis_done_events.get(char_name)
        result = None
        action_start_time = time.time()
        if done_event:
            done_event.clear()
            done_event.wait()
            result = get_axis_result(self, char_name)

        actual_fg = time.time() - action_start_time
        branch_id = "default"
        success = False
        if result is not None:
            if isinstance(result, tuple):
                success, branch_id = result
            else:
                success = result
        self._fg_collector.record_measurement(char_name, action_name, actual_fg, branch_id)

        if result is not None:
            if success:
                self.log_info(f"轴动作 {char_name}.{action_name}[{branch_id}] 执行成功, 实测fg={actual_fg:.2f}s")
            else:
                self.log_error(f"轴动作 {char_name}.{action_name}[{branch_id}] 执行失败")
