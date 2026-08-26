# ok-script 分辨率自适应机制

> 来源: ok-wuthering-waves-master 项目 + ok-script 框架源码
> 调研日期: 2026-08-20

## 核心设计原则

**任务代码中应使用相对坐标 (0.0~1.0) 或参考分辨率绝对坐标，永远不要使用原始像素值。** 框架自动处理所有缩放。

## 架构总览

| 层 | 机制 | 位置 |
|----|------|------|
| 配置层 | 声明 `ratio: '16:9'`, `resize_to` 列表, `min_size` | `config.py` |
| 启动层 | 验证分辨率，不匹配时自动调整窗口大小 | `StartController.py`, `hwnd_window.py` |
| 运行时检测 | `out_of_ratio()` 检查实际比例是否偏离 16:9 | `task.py` |
| 坐标转换 | `box_of_screen()` 将 0.0~1.0 分数转为绝对像素 | `task.py` |
| 非标准比例 | `box_of_screen_scaled()` + `adjust_coordinates()` 从理想 16:9 空间映射到实际空间 | `task.py`, `FeatureSet.py` |
| 模板匹配 | 分辨率变化时重新加载特征; `target_height` 归一化匹配到参考分辨率 | `FeatureSet.py` |

## 配置方式

```python
# config.py
'supported_resolution': {
    'ratio': '16:9',
    'resize_to': [(2560, 1440), (1920, 1080), (1600, 900), (1280, 720)],
    'min_size': (1280, 720)
},
```

- 只支持 16:9 宽高比
- 窗口不是 16:9 时，框架自动调整到列表中能放进显示器的最大分辨率
- 最小支持 1280x720

## 关键 API

### box_of_screen — 相对坐标 (最常用)

```python
# 参数是屏幕的分数 (0.0~1.0)
self.box_of_screen(0.1, 0.10, 0.9, 0.9, name="area")
# → 覆盖屏幕 10%~90% 宽度和 10%~90% 高度的区域
```

内部调用 `Box.relative_box(frame_width, frame_height, x, y, w, h)`:
```python
Box(round(x * frame_width), round(y * frame_height),
    round(width * frame_width), round(height * frame_height))
```

### box_of_screen_scaled — 参考分辨率坐标

```python
# 以 4K (3840x2160) 为参考分辨率定义坐标, 自动缩放到实际分辨率
self.box_of_screen_scaled(3840, 2160, 1820, 266, 2100, 340, name="countdown", hcenter=True)
```

用于 COCO 标注基于特定分辨率 (如 2560x1440) 的特征区域。

### 其他辅助

```python
self.screen_width          # 当前屏幕像素宽度
self.screen_height         # 当前屏幕像素高度
self.width_of_screen(0.5)  # 屏幕宽度的 50%
self.click_relative(0.5, 0.5)  # 点击屏幕中心
```

## 核心缩放函数 adjust_coordinates

```python
def adjust_coordinates(x, y, w, h, screen_width, screen_height,
                       image_width, image_height, hcenter=False, vcenter=False):
    scale_x = screen_width / image_width
    scale_y = screen_height / image_height
    scale = min(scale_x, scale_y)  # 均匀缩放, 保持宽高比
    w, h = round(w * scale), round(h * scale)
    x = scale_by_anchor(x, image_width, screen_width, scale, center=hcenter)
    y = scale_by_anchor(y, image_height, screen_height, scale, center=vcenter)
    return x, y, w, h, scale
```

- 使用 `min(scale_x, scale_y)` 均匀缩放
- `scale_by_anchor()` 根据元素位置决定锚点: 靠近中心的以中心为锚, 靠近边缘的以最近边缘为锚

## 非 16:9 比例处理

当 `out_of_ratio()` 返回 True 时 (实际比例偏离 16:9 超过 1%):

1. `box_of_screen()` 自动切换到 `box_of_screen_scaled()` 模式
2. 计算理想 16:9 宽度: `should_width = supported_ratio * height`
3. 用 `adjust_coordinates()` 从理想空间映射到实际空间

## 模板匹配的分辨率适配

1. **分辨率变化时** (`FeatureSet.check_size()`): 清除所有缓存特征, 重新加载
2. **特征加载时**: 用 `adjust_coordinates()` 将 COCO 标注坐标从原始图片尺寸缩放到当前屏幕, **模板图片本身也会 `cv2.resize()` 到缩放后的尺寸** — 低分辨率运行时模板自动缩小, 高分辨率运行时自动放大 (源码确认 2026-08-22, `FeatureSet.py` load_features)
3. **target_height 参数**: 当指定 `target_height` 且当前分辨率显著更大时, 同时缩小搜索区域和模板, 归一化到参考分辨率进行匹配, 匹配结果坐标再换算回原尺度

**找色** (`calculate_color_percentage`): 不涉及模板缩放, 直接裁剪当前帧区域用 `cv2.inRange` 计算目标颜色像素占比, 比例值天然与分辨率无关 (仅极端低分辨率下抗锯齿可能轻微影响占比)

## 宽屏 UI 缩放

```python
# 项目中的处理方式
WIDE_MODE_UI_SCALE = 0.75
wide_template = cv2.resize(check_feature.mat, (0, 0), fx=0.75, fy=0.75)
```

当游戏在超宽屏下 UI 元素缩小时, 项目手动缩放模板以匹配。

## blur_area 回调模式

```python
# config.py 中的回调, 接收实际屏幕尺寸, 返回绝对像素 Box
def blur_area(width, height):
    blur_width = int(0.12 * width)
    blur_height = int(0.024 * height)
    return Box(width * 0.879, height * 0.976, blur_width * 0.973, blur_height * 0.994)
```

另一种分辨率自适应模式: 回调函数接收实际尺寸, 内部用相对坐标计算。

## 对 konghuiww 项目的启示

当前项目 (`e:\konghuiww\konghuiww`) 的 COCO 标注基于 2560x1440:
- `box_of_screen_scaled(3840, 2160, ...)` 用于 4K 参考坐标
- `box_of_screen(x, y, to_x, to_y)` 用于相对坐标
- `get_location_box()` 通过 `get_feature_by_name()` 获取预定义位置 (已含缩放)
- 框架自动处理分辨率缩放, 任务代码无需关心实际分辨率
