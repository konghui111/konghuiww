import os  # 导入操作系统模块

from PySide6.QtWidgets import QFileDialog  # 导入文件对话框
from qfluentwidgets import FluentIcon  # 导入图标

from src.tasks.MyBaseTask import MyBaseTask  # 导入基类
from src.tasks.AxisEditor import Axis, AxisEditorDialog, CharacterSelectionDialog  # 导入轴编辑器
from src.tasks.CharacterEditor import CharacterEditorDialog  # 导入角色编辑器


# ==== 轴编辑工具任务 ====
class AxisEditorTask(MyBaseTask):
    """轴编辑工具: 新建轴、编辑轴、编辑角色。一次性任务, 点击按钮打开对应编辑器。"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "轴编辑器"
        self.description = "新建/编辑轴, 编辑角色属性。点击按钮打开对应编辑器。"
        self.icon = FluentIcon.EDIT

        # ---- 默认配置 ----
        self.default_config.update({
            "新建轴": "新建轴",
            "编辑轴": "编辑轴",
            "编辑角色": "编辑角色",
        })
        self.config_description.update({
            "新建轴": "创建新的轴: 先选择角色, 再编辑动作时间线。",
            "编辑轴": "选择已有的轴文件, 打开编辑器修改后保存。",
            "编辑角色": "打开角色属性编辑器, 修改角色定位、属性、共鸣链等。",
        })
        self.config_type.update({
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
            "编辑角色": {
                "type": "button",
                "text": "编辑角色",
                "callback": self._edit_character,
            },
        })

    def _create_new_axis(self):
        """创建新轴: 先选择角色, 再打开编辑器"""
        char_dialog = CharacterSelectionDialog(parent=None)
        if char_dialog.exec():
            selected_chars = char_dialog.selected_characters
            editor = AxisEditorDialog(selected_characters=selected_chars, axis=Axis(), parent=None)
            if editor.exec():
                new_axis = editor.get_axis()
                self.log_info(f"新轴已创建: 启动{len(new_axis.startup)}个动作, 循环{len(new_axis.loop)}个动作")

    def _edit_axis(self):
        """编辑轴: 选择已有轴文件, 打开编辑器修改"""
        default_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'axis')
        file_path, _ = QFileDialog.getOpenFileName(None, "编辑轴", default_dir, "轴文件 (*.json)")
        if not file_path:
            return
        try:
            axis = Axis.load(file_path)
        except Exception as e:
            self.log_error(f"加载轴文件失败: {e}")
            return
        char_names = []
        for action in axis.startup + axis.loop:
            if action.character_name not in char_names:
                char_names.append(action.character_name)
        if not char_names:
            self.log_warning("该轴文件中没有动作, 无法编辑")
            return
        char_names = char_names[:3]
        editor = AxisEditorDialog(selected_characters=char_names, axis=axis, parent=None)
        if editor.exec():
            self.log_info(f"轴已编辑: {file_path}")

    def _edit_character(self):
        """打开角色属性编辑器"""
        dialog = CharacterEditorDialog(parent=None)
        dialog.exec()

    def run(self):
        """一次性任务: 不需要持续运行, 按钮回调已处理所有逻辑"""
        self.log_info("轴编辑器已就绪, 点击上方按钮打开编辑器")
