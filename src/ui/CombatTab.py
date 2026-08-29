from qfluentwidgets import FluentIcon
from ok.gui.widget.CustomTab import CustomTab
from ok.gui.tasks.TaskCard import TaskCard
from ok.gui.tasks.ConfigCard import ConfigCard


class CombatTab(CustomTab):
    """自定义战斗配置 Tab, 展示战斗和编辑相关的任务卡片"""

    def __init__(self):
        super().__init__()
        self.icon = FluentIcon.GAME

    @property
    def name(self):
        return "战斗配置"

    @property
    def add_after_default_tabs(self):
        return False  # 放在默认 Tab 前面

    def showEvent(self, event):
        super().showEvent(event)
        # 延迟初始化: 第一次显示时才创建控件, 确保 executor 已就绪
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._build_ui()

    def _build_ui(self):
        from src.tasks.AxisCombatTask import AxisCombatTask
        from src.tasks.AutoCombatTask import AutoCombatTask
        from src.tasks.AxisEditorTask import AxisEditorTask

        # 打轴战斗卡片 (含 Start/Stop 按钮)
        axis_task = self.get_task(AxisCombatTask)
        if axis_task:
            axis_card = TaskCard(task=axis_task, onetime=True)
            self.add_widget(axis_card)
            axis_card.setExpand(True)
            axis_card.card.expandButton.hide()
        else:
            self.logger.warning("CombatTab: 未找到 AxisCombatTask")

        # 自动战斗卡片 (含 Start/Stop 按钮)
        auto_task = self.get_task(AutoCombatTask)
        if auto_task:
            auto_card = TaskCard(task=auto_task, onetime=True)
            self.add_widget(auto_card)
            auto_card.setExpand(True)
            auto_card.card.expandButton.hide()
        else:
            self.logger.warning("CombatTab: 未找到 AutoCombatTask")

        # 轴编辑器卡片 (只有配置按钮, 无 Start/Stop)
        editor_task = self.get_task(AxisEditorTask)
        if editor_task:
            editor_card = ConfigCard(
                task=editor_task,
                name=editor_task.name,
                config=editor_task.config,
                description=editor_task.description,
                default_config=editor_task.default_config,
                config_description=editor_task.config_description,
                config_type=editor_task.config_type,
                config_icon=editor_task.icon or FluentIcon.EDIT,
            )
            self.add_widget(editor_card)
            editor_card.setExpand(True)
            editor_card.card.expandButton.hide()
        else:
            self.logger.warning("CombatTab: 未找到 AxisEditorTask")
