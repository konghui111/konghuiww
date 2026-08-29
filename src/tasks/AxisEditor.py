"""
轴编辑器模块: 提供轴数据结构、GUI 编辑界面和头像加载功能。
"""
import os  # 导入操作系统模块, 用于文件路径操作
import json as json_module  # 导入 json, 用于轴文件的保存和加载

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,  # 导入 GUI 组件
                               QListWidget, QListWidgetItem, QScrollArea, QWidget,
                               QFileDialog, QMessageBox, QCheckBox, QListView, QFrame, QGridLayout)
from PySide6.QtCore import Qt, QMimeData, QSize  # 导入 Qt 核心
from PySide6.QtGui import QDrag, QPixmap  # 导入绘图相关

from src.character import CHARACTER_LIBRARY, ACTION_REGISTRY  # 导入角色库和动作注册表

# 深色主题样式 (与 ok 框架深色模式一致)
BG_PRIMARY = "#202020"  # 主背景 (qfluentwidgets dark background)
BG_CARD = "#2D2D2D"  # 卡片/面板背景
TEXT_PRIMARY = "#FFFFFF"  # 主文字颜色
TEXT_SECONDARY = "#AAAAAA"  # 次要文字颜色
BORDER_COLOR = "#404040"  # 边框颜色


def get_character_avatar_path(character_name):  # 获取角色头像图片路径
    """
    从 coco_annotations.json 中获取角色头像的裁剪图片路径。
    角色头像模板名为 "character_<name>"。
    返回 (图片文件路径, bbox) 或 None。
    """
    # 固定使用 assets 目录
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    coco_path = os.path.join(project_root, "assets", "coco_annotations.json")

    if not os.path.isfile(coco_path):
        return None

    try:
        with open(coco_path, "r", encoding="utf-8") as f:
            coco_data = json_module.load(f)
    except Exception:
        return None

    # 查找 category 名称为 "character_<name>" 的 category_id
    target_name = f"character_{character_name}"
    category_id = None
    for cat in coco_data.get("categories", []):
        if cat.get("name") == target_name:
            category_id = cat.get("id")
            break

    if category_id is None:
        return None

    # 查找对应的 annotation
    for ann in coco_data.get("annotations", []):
        if ann.get("category_id") == category_id:
            image_id = ann.get("image_id")
            bbox = ann.get("bbox")  # [x, y, width, height]
            # 查找对应的图片
            for img in coco_data.get("images", []):
                if img.get("id") == image_id:
                    file_name = img.get("file_name")
                    # 图片在 assets/images/ 目录下
                    img_path = os.path.join(project_root, "assets", file_name)
                    if os.path.isfile(img_path):
                        return img_path, bbox
    return None


def create_avatar_pixmap(character_name, size=40):  # 创建角色头像 QPixmap
    """
    创建角色头像的 QPixmap, 从 coco_annotations 中裁剪。
    返回 QPixmap, 如果找不到返回空 QPixmap。
    """
    result = get_character_avatar_path(character_name)
    if result is None:
        return QPixmap()
    img_path, bbox = result
    if not os.path.isfile(img_path):
        return QPixmap()
    try:
        source = QPixmap(img_path)
        if source.isNull():
            return QPixmap()
        x, y, w, h = bbox
        cropped = source.copy(x, y, w, h)
        return cropped.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    except Exception:
        return QPixmap()


# ==== 轴数据结构 ====
class AxisAction:  # 轴中的单个动作
    """
    表示轴时间线中的一个动作块。
    包含角色名、动作名。
    """
    def __init__(self, character_name, action_name):  # 初始化动作
        self.character_name = character_name  # 角色名 (如 "qianxiao")
        self.action_name = action_name  # 动作名 (如 "ea23")

    def to_dict(self):  # 转换为字典 (用于 JSON 序列化)
        return {"character": self.character_name, "action": self.action_name}

    @staticmethod
    def from_dict(data):  # 从字典创建 (用于 JSON 反序列化)
        return AxisAction(data["character"], data["action"])


class Axis:  # 轴: 描述按时间线执行动作的战斗过程
    """
    轴包含五个阶段:
    - startup: 启动阶段, 战斗开始时执行一次
    - loop: 循环阶段, 启动后循环执行 (必需)
    - loop2: 循环2, 可空置, 空时用 loop 替代
    - loop3: 循环3, 可空置, 空时用 loop 替代
    - finish: 收尾阶段, 可空置, 空时用 loop 替代
    """
    def __init__(self):  # 初始化空轴
        self.startup = []  # 启动阶段动作列表
        self.loop = []  # 循环阶段动作列表
        self.loop2 = []  # 循环2 (可空置)
        self.loop3 = []  # 循环3 (可空置)
        self.finish = []  # 收尾阶段 (可空置)

    def to_dict(self):  # 转换为字典 (用于 JSON 序列化)
        return {
            "startup": [action.to_dict() for action in self.startup],
            "loop": [action.to_dict() for action in self.loop],
            "loop2": [action.to_dict() for action in self.loop2],
            "loop3": [action.to_dict() for action in self.loop3],
            "finish": [action.to_dict() for action in self.finish],
        }

    @staticmethod
    def from_dict(data):  # 从字典创建 (用于 JSON 反序列化)
        axis = Axis()
        axis.startup = [AxisAction.from_dict(d) for d in data.get("startup", [])]
        axis.loop = [AxisAction.from_dict(d) for d in data.get("loop", [])]
        axis.loop2 = [AxisAction.from_dict(d) for d in data.get("loop2", [])]
        axis.loop3 = [AxisAction.from_dict(d) for d in data.get("loop3", [])]
        axis.finish = [AxisAction.from_dict(d) for d in data.get("finish", [])]
        return axis

    def save(self, file_path):  # 保存轴到文件
        with open(file_path, "w", encoding="utf-8") as f:  # 打开文件
            json_module.dump(self.to_dict(), f, ensure_ascii=False, indent=2)  # 写入 JSON

    @staticmethod
    def load(file_path):  # 从文件加载轴
        with open(file_path, "r", encoding="utf-8") as f:  # 打开文件
            data = json_module.load(f)  # 读取 JSON
        return Axis.from_dict(data)


# 动作名中文映射
ACTION_NAME_CN = {
    "skill_coordination": "变奏",
    "skill_coordination_z": "变奏Z",
}

def _cn_action_name(action_name):  # 获取动作的中文显示名
    """将动作名转为中文显示, 未映射的返回原名"""
    return ACTION_NAME_CN.get(action_name, action_name)


# ==== 轴编辑器 GUI 组件 ====
class ActionBlockWidget(QWidget):  # 动作方块组件: 显示动作信息
    """
    显示一个动作的方块, 布局:
    ┌─────────────────────────┐
    │      角色名 - 动作名      │  ← 顶部: 全宽
    ├──────────┬──────────────┤
    │  头像     │  fg/total 时间 │  ← 底部: 左头像, 右时间
    └──────────┴──────────────┘
    支持拖拽到时间线。
    """
    def __init__(self, character_name, action_name, parent=None):  # 初始化动作方块
        super().__init__(parent)
        self.character_name = character_name  # 角色名
        self.action_name = action_name  # 动作名
        # 从 fg_time_data.json 获取实测前台时间
        self.fg_time = 0  # 默认值
        self.total_time = 0  # 总时间 (暂未使用)
        try:
            from src.character.fg_time_collector import FgTimeCollector
            collector = FgTimeCollector()  # 加载 fg_time_data.json
            avg = collector.get_avg_fg_time(character_name, action_name)
            if avg is not None:
                self.fg_time = avg
        except Exception:
            pass
        self._init_ui()  # 初始化界面

    def _init_ui(self):  # 初始化界面
        main_layout = QVBoxLayout(self)  # 主垂直布局
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(2)

        # 顶部: 动作名 (中文), 宽度与底部一致 (110 - 8 = 102)
        name_label = QLabel()
        cn_name = _cn_action_name(self.action_name)
        name_label.setText(f"<b>{cn_name}</b>")
        name_label.setTextFormat(Qt.RichText)
        name_label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 13px;")
        name_label.setFixedWidth(102)  # 与底部宽度一致
        name_label.setFixedHeight(24)
        name_label.setAlignment(Qt.AlignLeft)
        main_layout.addWidget(name_label)

        # 底部: 头像 + 时间信息 (固定宽度 102, 与顶部一致)
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(4)
        # 左侧: 角色头像 (放大到 44px)
        avatar_label = QLabel()
        pixmap = create_avatar_pixmap(self.character_name, size=44)
        if not pixmap.isNull():
            avatar_label.setPixmap(pixmap)
        else:
            avatar_label.setText("?")
            avatar_label.setStyleSheet(f"background-color: {BG_CARD}; border-radius: 4px; font-size: 18px; color: {TEXT_PRIMARY};")
            avatar_label.setFixedSize(44, 44)
            avatar_label.setAlignment(Qt.AlignCenter)
        bottom_layout.addWidget(avatar_label)
        # 右侧: 时间信息 (两行: fg / total, 颜色与名称一致)
        time_layout = QVBoxLayout()
        time_layout.setContentsMargins(0, 0, 0, 0)
        time_layout.setSpacing(0)
        fg_label = QLabel()
        fg_label.setText(f"fg:{self.fg_time:.2f}s")
        fg_label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 12px;")
        time_layout.addWidget(fg_label)
        total_label = QLabel()
        total_label.setText(f"t:{self.total_time:.1f}s")
        total_label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 12px;")
        time_layout.addWidget(total_label)
        bottom_layout.addLayout(time_layout)
        bottom_layout.addStretch()
        main_layout.addLayout(bottom_layout)

        # 设置固定大小和样式 (所有方块统一尺寸, 放大到 110x70)
        self.setFixedSize(110, 70)
        self.setStyleSheet(f"background-color: {BG_CARD}; border: 1px solid {BORDER_COLOR}; border-radius: 4px;")

    def mousePressEvent(self, event):  # 鼠标按下时开始拖拽
        if event.button() == Qt.LeftButton:  # 左键拖拽
            self._drag_start_pos = event.pos()  # 记录起始位置

    def mouseMoveEvent(self, event):  # 鼠标移动时执行拖拽
        if not (event.buttons() & Qt.LeftButton):  # 不是左键
            return
        if (event.pos() - self._drag_start_pos).manhattanLength() < 10:  # 移动距离太短
            return
        drag = QDrag(self)  # 创建拖拽对象
        mime_data = QMimeData()  # 创建 MIME 数据
        mime_data.setText(f"{self.character_name}:{self.action_name}")  # 设置数据
        drag.setMimeData(mime_data)
        drag.exec(Qt.CopyAction)  # 执行拖拽


class TimelineWidget(QListWidget):  # 时间线组件: 接收拖拽的动作方块 (横向排列)
    """
    时间线组件, 可以接收拖拽的动作方块。
    横向排列, 从左到右代表执行顺序。
    右键点击动作方块可删除, 也可通过清空按钮移除全部动作。
    """
    def __init__(self, title, parent=None):  # 初始化时间线
        super().__init__(parent)
        self.title = title  # 时间线标题
        self.setAcceptDrops(True)  # 接受拖拽
        self.setDragDropMode(QListWidget.InternalMove)  # 允许内部移动
        self.setDefaultDropAction(Qt.CopyAction)  # 默认复制动作
        self.setIconSize(QSize(110, 70))  # 设置图标大小, 匹配 ActionBlockWidget (110x70)
        self.setFlow(QListView.LeftToRight)  # 横向排列
        self.setWrapping(False)  # 不自动换行
        self.setSpacing(4)  # 设置间距
        self.setStyleSheet("QListWidget { border: none; }")  # 边框由外部容器提供

    def contextMenuEvent(self, event):  # 右键菜单
        item = self.itemAt(event.pos())  # 获取右键点击位置的项
        if item:  # 点击到了有效项
            from PySide6.QtWidgets import QMenu  # 导入菜单组件
            menu = QMenu(self)  # 创建右键菜单
            delete_action = menu.addAction("删除")  # 添加删除选项
            action = menu.exec(event.globalPos())  # 显示菜单并等待用户选择
            if action == delete_action:  # 用户选择了删除
                row = self.row(item)  # 获取项的行号
                self.takeItem(row)  # 移除该项

    def dragEnterEvent(self, event):  # 拖拽进入时
        if event.mimeData().hasText():  # 有文本数据
            event.accept()  # 接受拖拽
        else:
            event.ignore()  # 忽略拖拽

    def dragMoveEvent(self, event):  # 拖拽移动时
        if event.mimeData().hasText():  # 有文本数据
            event.accept()  # 接受拖拽
        else:
            event.ignore()  # 忽略拖拽

    def dropEvent(self, event):  # 放下时
        if event.mimeData().hasText():  # 有文本数据
            text = event.mimeData().text()  # 获取文本
            if ":" in text:  # 格式正确
                char_name, action_name = text.split(":", 1)  # 分割角色名和动作名
                # 计算放置位置: 根据鼠标位置找到插入点
                drop_index = self.count()  # 默认插入到末尾
                for i in range(self.count()):
                    item = self.item(i)
                    item_rect = self.visualItemRect(item)
                    # 横向排列: 鼠标在 item 左半部分则插入到此位置
                    if event.pos().x() < item_rect.center().x():
                        drop_index = i
                        break
                self.insert_action(drop_index, char_name, action_name)  # 在指定位置插入动作
                event.accept()  # 接受放下
            else:
                event.ignore()  # 忽略放下
        else:
            event.ignore()  # 忽略放下

    def add_action(self, character_name, action_name):  # 添加动作到时间线末尾
        self.insert_action(self.count(), character_name, action_name)

    def insert_action(self, index, character_name, action_name):  # 在指定位置插入动作
        item = QListWidgetItem()  # 创建列表项
        block = ActionBlockWidget(character_name, action_name)  # 创建动作方块
        item.setSizeHint(block.size())  # 设置大小
        self.insertItem(index, item)  # 在指定位置插入列表项
        self.setItemWidget(item, block)  # 设置组件

    def get_actions(self):  # 获取时间线中的所有动作
        actions = []  # 动作列表
        for i in range(self.count()):  # 遍历所有项
            item = self.item(i)  # 获取列表项
            block = self.itemWidget(item)  # 获取组件
            if block:  # 组件存在
                actions.append(AxisAction(block.character_name, block.action_name))  # 创建动作
        return actions


class AxisEditorDialog(QDialog):  # 轴编辑器对话框
    """
    轴编辑器主界面:
    - 上方显示选中角色的所有动作方块 (3个槽位, 显示头像)
    - 下方显示启动和循环两条横向时间线
    - 支持拖拽动作方块到时间线
    - 深色主题背景
    """
    def __init__(self, selected_characters=None, axis=None, parent=None):  # 初始化编辑器
        super().__init__(parent)
        self.setWindowTitle("轴编辑器")
        self.resize(900, 900)  # 窗口尺寸 (纵向排列需要更高)
        self.selected_characters = selected_characters or []  # 选中的角色列表 (最多3个)
        self.axis = axis or Axis()  # 当前编辑的轴

        self._init_ui()  # 初始化界面
        self._load_axis()  # 加载轴数据

    def _init_ui(self):  # 初始化界面
        layout = QVBoxLayout(self)  # 主布局

        # 角色动作区域 (整体一个大边框, 行之间用分隔线)
        layout.addWidget(QLabel("角色动作 (拖拽到下方时间线):"))
        self.char_slots_widget = QWidget()  # 角色槽位容器
        self.char_slots_widget.setStyleSheet(f"background-color: {BG_CARD}; border: 1px solid {BORDER_COLOR}; border-radius: 8px;")
        self.char_slots_layout = QVBoxLayout(self.char_slots_widget)  # 垂直布局 (三行)
        self.char_slots_layout.setSpacing(0)  # 无间距
        # 为每个选中的角色创建一个槽位
        for i in range(3):  # 固定3个槽位
            slot_widget = QWidget()  # 槽位容器
            slot_widget.setStyleSheet(f"background-color: {BG_CARD};")  # 无独立边框, 由父容器提供
            slot_layout = QHBoxLayout(slot_widget)  # 水平布局: 左侧头像+名字, 右侧动作列表
            slot_layout.setContentsMargins(4, 4, 4, 4)  # 减小边距
            slot_layout.setSpacing(4)  # 减小间距
            if i < len(self.selected_characters):  # 有选中的角色
                char_name = self.selected_characters[i]  # 角色名
                # 左侧: 角色头像 + 角色名 (固定宽度)
                avatar_widget = QWidget()
                avatar_layout = QVBoxLayout(avatar_widget)
                avatar_layout.setContentsMargins(0, 0, 0, 0)
                avatar_layout.setSpacing(4)
                avatar_label = QLabel()
                pixmap = create_avatar_pixmap(char_name, size=50)
                if not pixmap.isNull():
                    avatar_label.setPixmap(pixmap)
                else:
                    avatar_label.setText("?")
                    avatar_label.setFixedSize(50, 50)
                    avatar_label.setAlignment(Qt.AlignCenter)
                avatar_layout.addWidget(avatar_label, alignment=Qt.AlignCenter)
                name_label = QLabel(f"<b>{char_name}</b>")
                name_label.setAlignment(Qt.AlignCenter)
                name_label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 11px;")
                avatar_layout.addWidget(name_label)
                avatar_layout.addStretch()
                avatar_widget.setFixedWidth(70)
                slot_layout.addWidget(avatar_widget)
                # 右侧: 显示该角色的所有动作 (横向排列, 可滚动)
                actions = ACTION_REGISTRY.get(char_name, {})
                scroll = QScrollArea()  # 滚动区域
                scroll.setWidgetResizable(True)
                scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
                scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                scroll.setMaximumHeight(100)  # 单行高度 (放大动作块后)
                scroll.setStyleSheet("""
                    QScrollArea {
                        border: none;
                        background: transparent;
                    }
                    QScrollBar:horizontal {
                        border: none;
                        background: transparent;
                        height: 6px;
                    }
                    QScrollBar::handle:horizontal {
                        background: #666;
                        border-radius: 3px;
                        min-width: 20px;
                    }
                """)  # 完全去掉滚动区域边框和背景
                actions_container = QWidget()
                actions_layout = QHBoxLayout(actions_container)  # 横向排列
                actions_layout.setSpacing(4)
                for action_name in actions:
                    block = ActionBlockWidget(char_name, action_name)
                    actions_layout.addWidget(block)
                actions_layout.addStretch()
                scroll.setWidget(actions_container)
                slot_layout.addWidget(scroll)
            else:  # 空槽位
                empty_label = QLabel("<i>空槽位</i>")
                empty_label.setAlignment(Qt.AlignCenter)
                slot_layout.addWidget(empty_label)
            self.char_slots_layout.addWidget(slot_widget)
            # 行之间加分隔线 (最后一行不加)
            if i < 2:
                separator = QFrame()
                separator.setFrameShape(QFrame.HLine)
                separator.setStyleSheet(f"background-color: {BORDER_COLOR}; max-height: 1px;")
                separator.setContentsMargins(8, 0, 8, 0)
                self.char_slots_layout.addWidget(separator)
        layout.addWidget(self.char_slots_widget)

        # 时间线区域 (横向)
        # 启动阶段 (标签+按钮在框体左侧)
        self.startup_timeline = TimelineWidget("启动")
        self.startup_timeline.setMinimumHeight(80)
        self.startup_timeline.setMaximumHeight(100)
        startup_container = self._make_timeline_row("启动阶段:", self.startup_timeline)
        layout.addWidget(startup_container)

        # 循环阶段 (必需)
        self.loop_timeline = TimelineWidget("循环")
        self.loop_timeline.setMinimumHeight(80)
        self.loop_timeline.setMaximumHeight(100)
        loop_container = self._make_timeline_row("循环:", self.loop_timeline)
        layout.addWidget(loop_container)

        # 循环2 (可空置)
        self.loop2_timeline = TimelineWidget("循环2")
        self.loop2_timeline.setMinimumHeight(80)
        self.loop2_timeline.setMaximumHeight(100)
        loop2_container = self._make_timeline_row("循环2 (可空置):", self.loop2_timeline)
        layout.addWidget(loop2_container)

        # 循环3 (可空置)
        self.loop3_timeline = TimelineWidget("循环3")
        self.loop3_timeline.setMinimumHeight(80)
        self.loop3_timeline.setMaximumHeight(100)
        loop3_container = self._make_timeline_row("循环3 (可空置):", self.loop3_timeline)
        layout.addWidget(loop3_container)

        # 收尾阶段 (可空置)
        self.finish_timeline = TimelineWidget("收尾")
        self.finish_timeline.setMinimumHeight(80)
        self.finish_timeline.setMaximumHeight(100)
        finish_container = self._make_timeline_row("收尾 (可空置):", self.finish_timeline)
        layout.addWidget(finish_container)

        # 按钮区域
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self._save_axis)
        btn_layout.addWidget(save_btn)
        btn_layout.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        # 整体样式
        self.setStyleSheet(f"QDialog {{ background-color: {BG_PRIMARY}; color: {TEXT_PRIMARY}; }} QLabel {{ color: {TEXT_PRIMARY}; }}")

    def _make_timeline_row(self, label_text, timeline):  # 创建时间线行 (模仿角色动作栏: 左侧放轴名+清空按钮, 右侧放动作列表)
        """将阶段标签、清空按钮和时间线包装在一个带边框的容器中"""
        container = QWidget()
        container.setStyleSheet(f"background-color: {BG_CARD}; border: 1px solid {BORDER_COLOR}; border-radius: 4px;")
        row_layout = QHBoxLayout(container)
        row_layout.setContentsMargins(6, 4, 6, 4)
        row_layout.setSpacing(6)
        # 左侧: 轴名称 + 清空按钮 (上下排列)
        label_widget = QWidget()
        label_widget.setFixedWidth(70)
        label_layout = QVBoxLayout(label_widget)
        label_layout.setContentsMargins(0, 0, 0, 0)
        label_layout.setSpacing(4)
        name_label = QLabel(label_text)
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 11px; font-weight: bold;")
        label_layout.addWidget(name_label, alignment=Qt.AlignCenter)
        # 清空按钮
        clear_btn = QPushButton("清空")
        clear_btn.setFixedWidth(60)
        clear_btn.clicked.connect(timeline.clear)
        label_layout.addWidget(clear_btn, alignment=Qt.AlignCenter)
        label_layout.addStretch()
        row_layout.addWidget(label_widget)
        # 时间线 (占满剩余空间)
        row_layout.addWidget(timeline)
        return container

    def _load_axis(self):  # 加载轴数据到界面
        # 清空所有时间线
        self.startup_timeline.clear()
        self.loop_timeline.clear()
        self.loop2_timeline.clear()
        self.loop3_timeline.clear()
        self.finish_timeline.clear()
        # 加载各阶段
        for action in self.axis.startup:
            self.startup_timeline.add_action(action.character_name, action.action_name)
        for action in self.axis.loop:
            self.loop_timeline.add_action(action.character_name, action.action_name)
        for action in self.axis.loop2:
            self.loop2_timeline.add_action(action.character_name, action.action_name)
        for action in self.axis.loop3:
            self.loop3_timeline.add_action(action.character_name, action.action_name)
        for action in self.axis.finish:
            self.finish_timeline.add_action(action.character_name, action.action_name)

    def _save_axis(self):  # 保存轴到文件
        default_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'axis')  # 默认保存到 src/axis 目录
        file_path, _ = QFileDialog.getSaveFileName(self, "保存轴", default_dir, "轴文件 (*.json)")
        if file_path:
            # 从时间线获取动作
            self.axis.startup = self.startup_timeline.get_actions()
            self.axis.loop = self.loop_timeline.get_actions()
            self.axis.loop2 = self.loop2_timeline.get_actions()
            self.axis.loop3 = self.loop3_timeline.get_actions()
            self.axis.finish = self.finish_timeline.get_actions()
            self.axis.save(file_path)
            QMessageBox.information(self, "成功", f"轴已保存到:\n{file_path}")

    def get_axis(self):  # 获取编辑后的轴
        self.axis.startup = self.startup_timeline.get_actions()
        self.axis.loop = self.loop_timeline.get_actions()
        self.axis.loop2 = self.loop2_timeline.get_actions()
        self.axis.loop3 = self.loop3_timeline.get_actions()
        self.axis.finish = self.finish_timeline.get_actions()
        return self.axis


class CharacterSelectionDialog(QDialog):  # 角色选择对话框
    """
    让用户从角色库中选择最多3个角色。
    显示角色头像而不是名字。
    """
    def __init__(self, parent=None):  # 初始化对话框
        super().__init__(parent)
        self.setWindowTitle("选择角色")
        self.resize(500, 300)
        self.selected_characters = []  # 选中的角色列表

        self._init_ui()  # 初始化界面

    def _init_ui(self):  # 初始化界面
        layout = QVBoxLayout(self)  # 主布局

        layout.addWidget(QLabel("选择最多3个角色:"))

        # 属性名称映射
        ELEMENT_NAMES = {0: "衍射", 1: "导电", 2: "热熔", 3: "冰属性", 4: "气动", 5: "湮灭"}

        # 按属性分组角色
        groups = {}  # {属性索引: [角色名列表]}
        for name in CHARACTER_LIBRARY:
            module = CHARACTER_LIBRARY[name]
            elem = int(getattr(module, "ELEMENT", 0))
            if elem not in groups:
                groups[elem] = []
            groups[elem].append(name)

        # 角色选择区域 (按属性分行)
        char_layout = QGridLayout()
        char_layout.setSpacing(8)
        self.char_labels = {}
        row = 0

        for elem_idx in sorted(groups.keys()):  # 按属性索引排序
            # 属性标签行
            elem_label = QLabel(ELEMENT_NAMES.get(elem_idx, f"属性{elem_idx}"))
            elem_label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-weight: bold; font-size: 13px;")
            char_layout.addWidget(elem_label, row, 0, 1, 8)  # 跨所有列
            row += 1

            # 角色卡片行
            col = 0
            for name in groups[elem_idx]:
                # 创建角色卡片 (头像 + 选择框)
                card_widget = QWidget()
                card_layout = QVBoxLayout(card_widget)
                card_layout.setContentsMargins(8, 8, 8, 8)
                card_layout.setAlignment(Qt.AlignCenter)
                # 头像
                avatar_label = QLabel()
                pixmap = create_avatar_pixmap(name, size=50)
                if not pixmap.isNull():
                    avatar_label.setPixmap(pixmap)
                else:
                    avatar_label.setText("?")
                    avatar_label.setStyleSheet(f"background-color: {BG_CARD}; border-radius: 8px; font-size: 20px;")
                    avatar_label.setFixedSize(50, 50)
                    avatar_label.setAlignment(Qt.AlignCenter)
                card_layout.addWidget(avatar_label, alignment=Qt.AlignCenter)
                # 角色选择 (使用 QLabel 显示黑色对号)
                select_label = QLabel("✓" if name in self.selected_characters else "")
                select_label.setFixedSize(24, 24)
                select_label.setAlignment(Qt.AlignCenter)
                select_label.setStyleSheet("font-size: 18px; font-weight: bold; color: black; background-color: white; border: 1px solid #999; border-radius: 4px;")
                select_label.mousePressEvent = lambda event, n=name, lbl=select_label: self._toggle_character(n, lbl)
                card_layout.addWidget(select_label, alignment=Qt.AlignCenter)
                # 名称标签
                name_label = QLabel(name)
                name_label.setAlignment(Qt.AlignCenter)
                card_layout.addWidget(name_label, alignment=Qt.AlignCenter)
                # 存储标签 + 卡片样式 + 添加到布局
                self.char_labels[name] = select_label
                card_widget.setStyleSheet(f"background-color: {BG_CARD}; border: 1px solid {BORDER_COLOR}; border-radius: 8px;")
                card_widget.setFixedWidth(120)
                char_layout.addWidget(card_widget, row, col)
                col += 1
            row += 1  # 下一属性换行

        layout.addLayout(char_layout)

        # 按钮区域
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self._on_ok)
        btn_layout.addWidget(ok_btn)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        # 整体样式
        self.setStyleSheet(f"QDialog {{ background-color: {BG_PRIMARY}; color: {TEXT_PRIMARY}; }} QLabel {{ color: {TEXT_PRIMARY}; }}")

    def _toggle_character(self, name, label):  # 切换角色选择状态
        """点击标签时切换角色的选中状态。"""
        if name in self.selected_characters:
            self.selected_characters.remove(name)
            label.setText("")
        else:
            if len(self.selected_characters) >= 3:
                QMessageBox.warning(self, "警告", "最多只能选择3个角色")
                return
            self.selected_characters.append(name)
            label.setText("✓")

    def _on_ok(self):  # 点击确定时
        if not self.selected_characters:
            QMessageBox.warning(self, "警告", "请至少选择一个角色")
            return
        self.accept()  # 关闭对话框
