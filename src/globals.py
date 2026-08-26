from PySide6.QtCore import QObject

from ok import Logger

logger = Logger.get_logger(__name__)


class Globals(QObject):

    def __init__(self, exit_event):
        super().__init__()

    def on_show_main_window(self, main_window):
        """窗口创建后、显示前调用。debug=False 时移除所有默认 Tab, 只保留 StartTab 和自定义 Tab。"""
        if self._is_debug(main_window):
            logger.info("debug 模式, 保留全部默认 Tab")
            return

        logger.info("非 debug 模式, 移除默认 Tab")
        self._remove_tab(main_window, 'start_tab')
        self._remove_tab(main_window, 'onetime_tab')
        self._remove_tab(main_window, 'trigger_tab')
        self._remove_tab(main_window, 'about_tab')
        self._remove_tab(main_window, 'setting_tab')
        self._remove_tab(main_window, 'schedule_tab')
        self._remove_tab(main_window, 'edit_task_tab')
        self._remove_tab(main_window, 'template_tab')

        # 移除分组任务 Tab
        for tab in getattr(main_window, 'grouped_task_tabs', []):
            self._remove_widget(main_window, tab)

        # 移除全局配置 Tab
        for tab in getattr(main_window, 'global_config_tabs', []):
            self._remove_widget(main_window, tab)

        # 移除导入脚本 Tab
        for tab in list(getattr(main_window, 'imported_tabs', {}).values()):
            self._remove_widget(main_window, tab)
        if hasattr(main_window, 'imported_tabs'):
            main_window.imported_tabs.clear()

        # 隐藏整个导航侧边栏 (只剩一个 Tab, 不需要导航)
        main_window.navigationInterface.hide()

        # 隐藏标题栏的 ok 图标
        try:
            main_window.titleBar.iconLabel.hide()
        except Exception as e:
            logger.warning(f"隐藏标题栏图标失败: {e}")

    @staticmethod
    def _is_debug(main_window):
        return main_window.config.get('debug', False)

    @staticmethod
    def _remove_tab(main_window, attr_name):
        """按属性名移除 Tab (属性可能不存在)"""
        tab = getattr(main_window, attr_name, None)
        if tab is not None:
            Globals._remove_widget(main_window, tab)

    @staticmethod
    def _remove_widget(main_window, widget):
        """从导航栏和堆叠窗口中移除一个 widget"""
        try:
            main_window.navigationInterface.removeWidget(widget.objectName())
            main_window.stackedWidget.removeWidget(widget)
            widget.deleteLater()
            logger.info(f"已移除 Tab: {widget.objectName()}")
        except Exception as e:
            logger.warning(f"移除 Tab 失败: {e}")

