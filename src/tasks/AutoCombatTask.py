import time  # 导入时间模块

from qfluentwidgets import FluentIcon  # 导入图标

from src.tasks.CombatBaseTask import CombatBaseTask  # 导入基类
from src.character import CHARACTER_LIBRARY  # 导入角色库


# ==== 自动战斗任务 (骨架, 后续开发) ====
class AutoCombatTask(CombatBaseTask):
    """
    自动模式: 使用调度算法自动切换角色。
    目前为骨架, 后续开发调度逻辑。
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "自动战斗"
        self.description = "自动检测在场角色并调度切换 (开发中)。"

        # ---- 覆盖默认热键为 F8 ----
        self.default_config["启停热键"] = "F8"
        self.config_type["启停热键"]["text"] = "当前: F8"

        # ---- 追加配置 (自动模式独有) ----
        # 后续可添加: 调度策略、优先级覆盖等

        # ---- 自动模式状态 ----
        self._switch_cooldowns = {}  # 各槽位的切换冷却结束时间
        self._last_scheduled_slot = 0  # 上次被调度上场的槽位编号

    def _reset_combat_state(self):
        super()._reset_combat_state()
        self._switch_cooldowns = {}
        self._last_scheduled_slot = 0

    def _execute_combat(self):
        """自动模式入口: 识别角色 → 启动脚本 → 调度切换"""
        if not self._prepare_combat():
            return

        self.log_warning("自动模式开发中, 请使用打轴模式")
        # TODO: 实现自动模式调度逻辑
        # 1. 启动所有角色脚本线程
        # 2. 循环检测在场角色切换
        # 3. 根据优先级/冷却/协奏等调度下一个角色
        # 4. 通过 event.set() 唤醒对应角色脚本

        # 临时: 启动脚本后等待战斗结束
        self._start_script_threads()
        for e in self._char_events.values():
            e.clear()
        # 唤醒所有角色 (让它们进入等待状态)
        for e in self._char_events.values():
            e.set()
        # 等待战斗停止
        while self._combat_active and self.enabled:
            time.sleep(0.1)
        self._cleanup_script_threads()
