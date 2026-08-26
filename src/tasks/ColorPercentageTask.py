from ok import Box  # 导入 Box 类, 用于构造位置区域
from qfluentwidgets import FluentIcon  # 导入图标库
import cv2  # 导入 OpenCV, 用于二值化处理
import numpy as np  # 导入 numpy, 用于图像数组拼接

from src.tasks.MyBaseTask import MyBaseTask  # 导入项目自定义基类
from src.character import binarize_image  # 导入二值化函数

# 常用颜色参考值 (选色时对照):
# a (255, 255, 255)
# dark r (230,73,166)
# (245, 248, 213) 5
# 穗穗buff (232,254,183) 3
# 右上角血条 (213,213,213) 1


class ColorPercentageTask(MyBaseTask):  # 颜色百分比检测任务

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "颜色百分比检测"  # 任务名称
        self.description = "在指定的 _location 位置检测颜色占比。参数在任务设置里修改, 保存后立即生效, 无需重启。"  # 任务描述
        self.icon = FluentIcon.PENCIL_INK  # 任务图标
        # 参数改为任务配置: 在 GUI 任务设置卡片中直接修改, 自动持久化到 configs/,
        # 方法调用时实时读取, 不需要重启框架 (原模块级常量方案需要重启才能改参数)
        self.default_config.update({  # 参数默认值
            "位置特征": "feixue_r1_location",  # _location 特征名 (仅使用位置, 不做模板匹配)
            "目标颜色R": 170,  # 目标颜色红色通道
            "目标颜色G": 249,  # 目标颜色绿色通道
            "目标颜色B": 255,  # 目标颜色蓝色通道
            "颜色容差": 0,  # 颜色容差, 匹配 目标颜色 ± 容差 范围内的像素
            "二值化阈值": 244,  # 二值化亮度阈值 (0-255), 仅保留亮度高于此值的像素
        })
        self.config_description.update({  # 参数帮助文字 (GUI 中显示)
            "位置特征": "_location 特征名, 仅使用其位置, 不做模板匹配",
            "颜色容差": "匹配 目标颜色 ± 容差 范围内的像素",
            "二值化阈值": "二值化时仅保留亮度高于此值的像素 (0-255)",
        })

    def _get_location_box(self, location_name):  # 获取 _location 特征的预定义位置, 返回 Box
        feature = self.get_feature_by_name(location_name)  # 获取 Feature 对象 (仅取位置, 不做模板匹配)
        if not feature:  # 特征不存在
            return None
        return Box(feature.x, feature.y, feature.width, feature.height,  # 用 Feature 的位置构造 Box
                   name=location_name)

    def _get_params(self):  # 从任务配置读取全部参数 (GUI 修改后下次调用立即生效)
        location = self.config.get("位置特征", "feixue_r1_location")  # 位置特征名
        rgb = (int(self.config.get("目标颜色R", 170)),  # 红色通道
               int(self.config.get("目标颜色G", 249)),  # 绿色通道
               int(self.config.get("目标颜色B", 255)))  # 蓝色通道
        tolerance = int(self.config.get("颜色容差", 0))  # 颜色容差
        binary_threshold = int(self.config.get("二值化阈值", 244))  # 二值化亮度阈值
        return location, rgb, tolerance, binary_threshold  # 返回参数元组

    def validate_config(self, key, value):  # 配置校验: 颜色通道/容差/阈值必须在 0-255
        if key in ("目标颜色R", "目标颜色G", "目标颜色B", "颜色容差", "二值化阈值"):  # 数值类配置
            try:  # 转换为整数
                v = int(value)
            except (TypeError, ValueError):  # 不是数字
                return "请输入整数"  # 返回错误提示, 拒绝保存
            if not (0 <= v <= 255):  # 超出范围
                return "请输入 0-255 之间的整数"  # 返回错误提示, 拒绝保存

    def run(self):
        percentage = self.get_color_percentage()  # 调用检测方法
        if percentage is not None:  # 检测成功
            self.info_set("颜色百分比", f"{percentage:.2%}")  # 在任务信息面板显示结果

    def get_color_percentage(self):  # 无参数包装方法, 可在开发工具 Tab 中直接调用
        location, rgb, tolerance, _ = self._get_params()  # 读取当前参数
        self.log_info(f"截图开始")
        self.next_frame()  # 强制刷新帧, 确保使用最新的截图 (切换图片后不会用缓存的旧帧)
        self.log_info(f"截图结束")
        r, g, b = rgb  # 解包 RGB 值
        color = {  # 构造颜色范围字典, RGB 转 BGR, 上下限由容差决定
            'b': (max(0, b - tolerance), min(255, b + tolerance)),  # 蓝色通道范围
            'g': (max(0, g - tolerance), min(255, g + tolerance)),  # 绿色通道范围
            'r': (max(0, r - tolerance), min(255, r + tolerance)),  # 红色通道范围
        }

        box = self._get_location_box(location)  # 获取 _location 的预定义位置区域
        if not box:  # 位置不存在时退出
            self.log_warning(f"位置特征 '{location}' 不存在")
            return None
        self.log_info(f"找色开始")
        percentage = self.calculate_color_percentage(color, box)  # 计算该区域内目标颜色的百分比
        self.log_info(f"找色结束")
        self.log_info(f"颜色 {rgb}±{tolerance} 百分比: {percentage:.2%}")  # 输出结果
        return percentage  # 返回百分比值, 开发工具 Tab 会显示返回值

    def get_binary_percentage(self):  # 二值化找色调试方法, 可在开发工具 Tab 中直接调用
        """
        对指定区域做灰度二值化, 计算白色像素占比。
        同时保存 "原图 | 二值化图 | 找色结果图" 三联对比截图, 打开图片即可目视检查二值化效果。

        对比截图保存位置 (框架 screenshot() 的行为, 已核实源码):
        - 目录: <程序运行目录>\\screenshots\\  (由 src/config.py 的 'screenshots_folder' 配置决定)
        - 文件名: {时-分-秒.毫秒}_binary_comparison_original.png, 如 14-30-05.123_binary_comparison_original.png
        注意:
        - debug=True 时每次启动应用会清空该目录; 否则自动删除 7 天前的文件 (超 300MB 整体清空)
        - config 中配置的 'screenshot_processor' (本项目为右下角涂黑遮挡 UID) 也会作用在对比图上,
          涂黑区域在图片右下角, 不影响观察中间的三联内容
        :return: 白色像素占比 (0.0~1.0)
        """
        location, rgb, tolerance, binary_threshold = self._get_params()  # 读取当前参数
        self.next_frame()  # 强制刷新帧
        box = self._get_location_box(location)  # 获取检测区域
        if not box:
            self.log_warning(f"位置特征 '{location}' 不存在")
            return None

        cropped = box.crop_frame(self.frame)  # 裁剪出目标区域
        binary = binarize_image(cropped, binary_threshold)  # 灰度二值化
        white_pct = cv2.countNonZero(binary) / binary.size if binary.size > 0 else 0  # 白色占比

        # 构造对比图: 原图 | 二值化图 | 找色结果图
        r, g, b = rgb  # 解包目标颜色
        color_mask = cv2.inRange(cropped,  # 普通找色结果 (BGR 颜色范围)
            np.array([max(0, b - tolerance),  # B 下限
                       max(0, g - tolerance),  # G 下限
                       max(0, r - tolerance)], dtype="uint8"),  # R 下限
            np.array([min(255, b + tolerance),  # B 上限
                       min(255, g + tolerance),  # G 上限
                       min(255, r + tolerance)], dtype="uint8"))  # R 上限
        color_result = cv2.cvtColor(color_mask, cv2.COLOR_GRAY2BGR)  # 灰度转 BGR
        binary_bgr = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)  # 二值化图转 BGR
        comparison = np.hstack([cropped, binary_bgr, color_result])  # 水平拼接三张图

        self.screenshot("binary_comparison", frame=comparison, show_box=False)  # 保存对比截图
        self.log_info(f"二值化阈值={binary_threshold}, 白色占比={white_pct:.2%}")
        self.log_info(f"普通找色 容差={tolerance}, 颜色占比={cv2.countNonZero(color_mask) / color_mask.size:.2%}")
        return white_pct

    def get_binary_image(self):  # 返回指定区域的二值化图并保存放大版供查看, 可在开发工具 Tab 中直接调用
        """
        对指定区域做灰度二值化, 返回二值化图 (numpy 数组, 0/255)。
        同时保存放大 4 倍的版本到 screenshots 目录, 便于目视检查
        (区域通常很小, 如 31x9, 不放大几乎无法观察; 最近邻插值不改变二值黑白边缘)。

        保存位置 (框架 screenshot() 行为):
        - 目录: <程序运行目录>\\screenshots\\
        - 文件名: {时-分-秒.毫秒}_binary_view_original.png
        :return: 单通道二值化图 (numpy ndarray, 0 或 255), 区域不存在返回 None
        """
        location, _, _, binary_threshold = self._get_params()  # 读取当前参数 (只用位置特征和二值化阈值)
        self.next_frame()  # 强制刷新帧
        box = self._get_location_box(location)  # 获取检测区域
        if not box:
            self.log_warning(f"位置特征 '{location}' 不存在")
            return None

        cropped = box.crop_frame(self.frame)  # 裁剪出目标区域
        binary = binarize_image(cropped, binary_threshold)  # 灰度二值化
        white_pct = cv2.countNonZero(binary) / binary.size if binary.size > 0 else 0  # 白色占比

        # 放大 4 倍保存便于查看 (INTER_NEAREST 保持黑白边缘锐利, 不产生灰阶)
        zoomed = cv2.resize(binary, None, fx=4, fy=4, interpolation=cv2.INTER_NEAREST)
        zoomed_bgr = cv2.cvtColor(zoomed, cv2.COLOR_GRAY2BGR)  # 单通道转 BGR (screenshot 保存需要)
        self.screenshot("binary_view", frame=zoomed_bgr, show_box=False)  # 保存放大版截图

        self.log_info(f"区域 {location} ({cropped.shape[1]}x{cropped.shape[0]}) 二值化阈值={binary_threshold}, 白色占比={white_pct:.2%}")
        return binary  # 返回原始尺寸的二值化图
