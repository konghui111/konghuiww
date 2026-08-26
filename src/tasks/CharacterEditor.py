import os  # 导入操作系统模块
import re  # 导入正则模块
import importlib  # 导入动态导入模块

from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QGridLayout, QScrollArea, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from qfluentwidgets import FluentIcon, PushButton, ComboBox

from src.character import CHARACTER_LIBRARY
from src.tasks.AxisEditor import create_avatar_pixmap  # 复用头像创建函数

# 深色主题样式 (与 ok 框架深色模式一致)
BG_PRIMARY = "#202020"  # 主背景 (qfluentwidgets dark background)
BG_CARD = "#2D2D2D"  # 卡片/面板背景
BG_CARD_HOVER = "#383838"  # 卡片悬停背景
TEXT_PRIMARY = "#FFFFFF"  # 主文字颜色
TEXT_SECONDARY = "#AAAAAA"  # 次要文字颜色
BORDER_COLOR = "#404040"  # 边框颜色

# 属性中文映射
CHAR_TYPE_OPTIONS = {
    "MainDps": "主输出",
    "SubDps": "副输出",
    "Healer": "治疗者",
}

SWITCH_PRIORITY_OPTIONS = {
    "0": "不切换",
    "100": "低",
    "200": "普通",
    "300": "高",
    "400": "必须切换",
}

ELEMENT_OPTIONS = {
    "0": "衍射",
    "1": "导电",
    "2": "热熔",
    "3": "冰属性",
    "4": "气动",
    "5": "湮灭",
}

RESONANCE_CHAIN_OPTIONS = {str(i): f"{i}链" for i in range(7)}  # 0链~6链

# 可编辑属性列表 (CHARACTER_NAME 不可编辑)
EDITABLE_PROPERTIES = [
    {"key": "CHAR_TYPE", "label": "角色定位", "options": CHAR_TYPE_OPTIONS, "enum_class": "CharType",
     "enum_map": {"MainDps": "MAIN_DPS", "SubDps": "SUB_DPS", "Healer": "HEALER"}},
    {"key": "SWITCH_PRIORITY", "label": "切换优先级", "options": SWITCH_PRIORITY_OPTIONS, "enum_class": "SwitchPriority",
     "enum_map": {"0": "NO", "100": "LOW", "200": "NORMAL", "300": "HIGH", "400": "MUST"}},
    {"key": "ELEMENT", "label": "角色属性", "options": ELEMENT_OPTIONS, "enum_class": "Elements",
     "enum_map": {"0": "SPECTRO", "1": "ELECTRIC", "2": "FIRE", "3": "ICE", "4": "WIND", "5": "HAVOC"}},
    {"key": "RESONANCE_CHAIN", "label": "共鸣链等级", "options": RESONANCE_CHAIN_OPTIONS, "enum_class": None,
     "enum_map": None},
]


class CharacterEditorDialog(QDialog):
    """角色属性编辑对话框: 选择角色, 编辑属性, 保存到脚本文件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("编辑角色")
        self.resize(700, 550)
        self._selected_char = None  # 当前选中的角色模块名
        self._char_buttons = {}  # 角色选择按钮 {模块名: QPushButton}
        self._combos = {}  # 属性下拉框 {属性key: ComboBox}
        self._init_ui()

    def _init_ui(self):
        """初始化界面"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        self.setStyleSheet(f"QDialog {{ background-color: {BG_PRIMARY}; color: {TEXT_PRIMARY}; }} QLabel {{ color: {TEXT_PRIMARY}; }}")

        # ---- 角色选择区域 ----
        main_layout.addWidget(QLabel("选择角色:"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(160)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; }}")
        scroll_widget = QWidget()
        char_layout = QGridLayout(scroll_widget)
        char_layout.setSpacing(8)

        col = 0
        row = 0
        for name in CHARACTER_LIBRARY:
            card = self._create_char_card(name)
            char_layout.addWidget(card, row, col)
            col += 1
            if col >= 5:
                col = 0
                row += 1

        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)

        # ---- 属性编辑区域 ----
        self._editor_title = QLabel("编辑属性:")
        main_layout.addWidget(self._editor_title)

        self._editor_widget = QWidget()
        editor_layout = QVBoxLayout(self._editor_widget)
        editor_layout.setContentsMargins(0, 0, 0, 0)

        for prop in EDITABLE_PROPERTIES:
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 2, 0, 2)

            label = QLabel(prop["label"])
            label.setFixedWidth(100)
            row_layout.addWidget(label)

            combo = ComboBox()
            for val, display in prop["options"].items():
                combo.addItem(display)
            combo.setFixedWidth(180)
            row_layout.addWidget(combo)
            row_layout.addStretch()

            self._combos[prop["key"]] = combo
            editor_layout.addWidget(row_widget)

        editor_layout.addStretch()
        self._editor_widget.setVisible(False)
        self._editor_title.setVisible(False)
        main_layout.addWidget(self._editor_widget)

        # ---- 底部按钮 ----
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._save_btn = PushButton("保存到脚本")
        self._save_btn.setIcon(FluentIcon.SAVE)
        self._save_btn.setFixedWidth(140)
        self._save_btn.clicked.connect(self._save_to_file)
        self._save_btn.setVisible(False)
        btn_layout.addWidget(self._save_btn)

        close_btn = PushButton("关闭")
        close_btn.setFixedWidth(100)
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)

        main_layout.addLayout(btn_layout)

    def _create_char_card(self, char_name):
        """创建角色选择卡片"""
        card = QWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(6, 6, 6, 6)
        card_layout.setAlignment(Qt.AlignCenter)

        avatar = QLabel()
        pixmap = create_avatar_pixmap(char_name, size=50)
        if not pixmap.isNull():
            avatar.setPixmap(pixmap)
        else:
            avatar.setText("?")
            avatar.setStyleSheet(f"background-color: {BG_CARD}; border-radius: 8px; font-size: 20px; color: {TEXT_SECONDARY};")
            avatar.setFixedSize(50, 50)
            avatar.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(avatar, alignment=Qt.AlignCenter)

        name_label = QLabel(char_name)
        name_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(name_label)

        btn = QPushButton("选择")
        btn.setFixedWidth(70)
        btn.setCheckable(True)
        btn.clicked.connect(lambda checked, n=char_name: self._select_char(n))
        card_layout.addWidget(btn, alignment=Qt.AlignCenter)
        self._char_buttons[char_name] = btn

        card.setStyleSheet(f"background-color: {BG_CARD}; border: 1px solid {BORDER_COLOR}; border-radius: 8px; color: {TEXT_PRIMARY};")
        card.setFixedWidth(110)
        return card

    def _select_char(self, char_name):
        """选中一个角色"""
        for name, btn in self._char_buttons.items():
            if name != char_name:
                btn.setChecked(False)
                btn.setText("选择")

        btn = self._char_buttons[char_name]
        if btn.isChecked():
            btn.setText("已选")
            self._selected_char = char_name
            self._load_properties(char_name)
            self._editor_widget.setVisible(True)
            self._editor_title.setVisible(True)
            self._save_btn.setVisible(True)
        else:
            btn.setText("选择")
            self._selected_char = None
            self._editor_widget.setVisible(False)
            self._editor_title.setVisible(False)
            self._save_btn.setVisible(False)

    def _load_properties(self, char_name):
        """加载角色属性到下拉框"""
        module = CHARACTER_LIBRARY.get(char_name)
        if not module:
            return

        for prop in EDITABLE_PROPERTIES:
            combo = self._combos[prop["key"]]
            current_val = str(getattr(module, prop["key"], ""))
            options = list(prop["options"].keys())
            try:
                combo.setCurrentIndex(options.index(current_val))
            except ValueError:
                combo.setCurrentIndex(0)

    def _save_to_file(self):
        """保存编辑结果到角色脚本文件"""
        if not self._selected_char:
            return

        module = CHARACTER_LIBRARY.get(self._selected_char)
        if not module:
            return

        file_path = module.__file__
        if not file_path or not os.path.isfile(file_path):
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            return

        for prop in EDITABLE_PROPERTIES:
            combo = self._combos[prop["key"]]
            new_val = list(prop["options"].keys())[combo.currentIndex()]
            content = self._replace_property(content, prop["key"], new_val, prop)

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            importlib.reload(module)
            self.close()
        except Exception:
            pass

    @staticmethod
    def _replace_property(content, key, value, prop):
        """替换脚本文件中的属性值"""
        pattern = rf'^({key}\s*=\s*).*$'
        match = re.search(pattern, content, re.MULTILINE)
        if not match:
            return content

        if prop["enum_class"]:
            enum_name = prop["enum_map"].get(value, value)
            new_value = f"{prop['enum_class']}.{enum_name}"
        else:
            new_value = value

        old_line = match.group(0)
        comment = ""
        if "#" in old_line:
            comment = "  " + old_line[old_line.index("#"):]

        return re.sub(pattern, f"{key} = {new_value}{comment}", content, count=1, flags=re.MULTILINE)
