from qfluentwidgets import FluentIcon
from ok.gui.widget.CustomTab import CustomTab
from ok.gui.tasks.TaskCard import TaskCard


class CombatTab(CustomTab):
    """自定义战斗配置 Tab, 仅展示 CharacterAutoTask 的任务卡片 (含 Start/Pause/Stop 按钮)"""

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
        from src.tasks.CharacterAutoTask import CharacterAutoTask
        task = self.get_task(CharacterAutoTask)  # 获取框架中的 CharacterAutoTask 实例
        if task is None:
            self.logger.warning("CombatTab: 未找到 CharacterAutoTask 实例")
            return

        # 用 TaskCard 渲染 (含 Start/Pause/Stop 按钮 + 全部配置控件)
        self._card = TaskCard(task=task, onetime=True)
        self.add_widget(self._card)

        # 自动展开卡片, 隐藏展开按钮
        self._card.setExpand(True)
        self._card.card.expandButton.hide()
