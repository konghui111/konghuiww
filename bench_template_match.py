# ============================================================
# 模板匹配耗时基准测试工具
# ============================================================
# 用途: 测量不同"搜索区域大小 + 分辨率"组合下 cv2.matchTemplate 的耗时,
#       为处决按键 (f_break) 等大范围找图任务选择参数提供数据支撑。
#
# 背景:
#   处决的 F 按键提示不像技能按键那样固定在 UI 上, 而是跟随怪物移动,
#   因此需要在一块较大的屏幕区域内找图。搜索区域越大耗时越高,
#   本脚本用于实测各方案的耗时, 找到"够大的覆盖范围 + 可接受的速度"的平衡点。
#
# 与 ok 框架 find_one 参数的对应关系:
#   - 脚本中的"中央区域裁剪"  对应  find_one(name, box=task.box_of_screen(0.2, 0.2, 0.75, 0.8))
#   - 脚本中的"降采样到 720p" 对应  find_one(name, target_height=720)
#   - 两者叠加即 OK-WW 项目 check_f_break() 采用的方案 (实测约 11ms/次)
#
# 测试分两部分:
#   第一部分 (场景 A~F): 直接调用 cv2.matchTemplate, 复现框架内部匹配路径
#     依据: ok/feature/FeatureSet.py 的 find_one_feature() 默认路径就是
#           "按 box 裁剪搜索区域 → 按 target_height 缩放 → 执行一次 matchTemplate"
#   第二部分 (场景 G~I): 直接调用 ok 框架的 FeatureSet.find_one_feature() 真实接口
#     用于对照验证: 框架调用层的额外开销 (特征查找/坐标计算等) 相对匹配本身可忽略
#
# 使用方法:
#   1. 修改下方配置区的参数 (截图路径/模板裁剪位置/区域比例等)
#   2. 运行: python bench_template_match.py
#   3. 查看各场景的中位数耗时, 选择满足实时性要求的方案
# ============================================================

import time  # 计时用
import cv2  # OpenCV, 提供模板匹配和缩放功能

# ==================== 配置区 (按需修改) ====================

# 源截图路径: 从项目的 COCO 标注源截图中选一张包含待匹配目标的图
IMAGE_PATH = r"e:\konghuiww\konghuiww\assets\images\0.png"

# 模板裁剪区域 (在源截图中的像素坐标): 换成你要测试的真实目标
# 格式: [y起点, y终点, x起点, x终点], 这里裁的是 24x29 的小块,
# 与处决按键在 1440p 下的实际尺寸接近 (OK-WW 的 f_break 模板为 4K 下 36x43)
TEMPLATE_CROP = (700, 729, 1200, 1224)

# 大模板尺寸参考: 用于观察模板变大对耗时的影响 (结论: 影响很小, 耗时主要由搜索区域决定)
TEMPLATE_CROP_BIG = (650, 750, 1150, 1250)

# 中央搜索区域 (相对屏幕的比例, 与 OK-WW check_f_break 一致):
# 0.2, 0.2, 0.75, 0.8 表示 x 从 20% 到 75%, y 从 20% 到 80%
# 2560x1440 下即 (512,288) 到 (1920,1152), 约 1408x864 像素
REGION = (0.2, 0.2, 0.75, 0.8)

# 降采样目标高度: 对应 find_one 的 target_height 参数
# 框架会把搜索区域和模板同时缩放到此高度再匹配, 找到后坐标自动换算回原尺度
TARGET_HEIGHT = 720

# 每个场景重复测试的次数, 取中位数避免波动
REPEAT = 20

# ---- ok 框架真实调用对照测试的配置 ----
# 是否运行框架对照测试 (需要已安装 ok 包); 设为 False 可跳过
USE_OK_FRAMEWORK = True
# 项目的 COCO 标注文件, 框架用它加载特征模板
COCO_JSON = r"e:\konghuiww\konghuiww\assets\coco_annotations.json"
# 用于测试的特征名 (标注文件中已存在的任意特征均可)
FEATURE_NAME = "character1"

# ==================== 配置区结束 ====================


def bench(name, area, tpl, n=REPEAT):
    """
    对一个 (搜索区域, 模板) 组合重复执行 matchTemplate 并统计耗时。
    :param name: 场景名称 (打印用)
    :param area: 搜索区域图像 (BGR numpy 数组)
    :param tpl: 模板图像 (BGR numpy 数组)
    :param n: 重复次数
    """
    ts = []  # 每次匹配的耗时列表 (毫秒)
    for _ in range(n):  # 重复 n 次
        t0 = time.perf_counter()  # 记录开始时间 (高精度)
        cv2.matchTemplate(area, tpl, cv2.TM_CCOEFF_NORMED)  # 执行一次模板匹配
        ts.append((time.perf_counter() - t0) * 1000)  # 记录本次耗时 (毫秒)
    ts.sort()  # 排序, 用于取中位数和最大值
    print(f"{name:<42} 中位数 {ts[n // 2]:7.2f} ms   最大 {ts[-1]:7.2f} ms")


def bench_ok_framework(img, center, cx1, cy1, cw, ch):
    """
    用 ok 框架的真实接口 FeatureSet.find_one_feature() 做对照测试。
    与第一部分的纯 cv2 场景一一对应, 差值即框架调用层的额外开销。
    :param img: 全屏截图
    :param center: 中央区域裁剪图 (本函数内不使用, 框架自己按 box 裁剪)
    :param cx1, cy1: 中央区域左上角坐标
    :param cw, ch: 中央区域宽高
    """
    try:  # 导入框架模块, 未安装 ok 时跳过
        from ok.feature.FeatureSet import FeatureSet  # 特征集 (模板加载+匹配)
        from ok import Box  # 区域类
    except ImportError as e:  # ok 未安装
        print(f"跳过框架对照测试 (导入失败: {e})")
        return

    h, w = img.shape[:2]  # 截图尺寸
    # 构造特征集: 参数与项目 src/config.py 的 template_matching 配置一致
    fs = FeatureSet(False, COCO_JSON, 0.2, 0.2, default_threshold=0.8)

    # 三个场景的区域定义 (与第一部分对应)
    full_box = Box(0, 0, w, h, name="full")  # 全屏区域
    center_box = Box(cx1, cy1, cw, ch, name="center")  # 中央区域

    # 预热: 首次调用会触发特征加载 (读 COCO/裁模板), 不计入统计
    fs.find_one_feature(mat=img, category_name=FEATURE_NAME, box=full_box)

    def bench_fs(name, box, target_height=0):  # 框架版基准测试
        ts = []  # 耗时记录
        for _ in range(REPEAT):  # 重复测试
            t0 = time.perf_counter()  # 开始计时
            fs.find_one_feature(mat=img, category_name=FEATURE_NAME,
                                box=box, target_height=target_height)  # 框架真实匹配
            ts.append((time.perf_counter() - t0) * 1000)  # 记录毫秒
        ts.sort()  # 排序
        print(f"{name:<42} 中位数 {ts[REPEAT // 2]:7.2f} ms   最大 {ts[-1]:7.2f} ms")

    bench_fs("G [框架] 全屏 (对照场景A)", full_box)  # 全屏, 不降采样
    bench_fs("H [框架] 中央区域 (对照场景B)", center_box)  # 中央区域
    bench_fs("I [框架] 中央区域+720p (对照场景D)", center_box, target_height=720)  # 区域+降采样


def main():  # 主函数
    img = cv2.imread(IMAGE_PATH)  # 读取源截图
    if img is None:  # 读取失败
        print(f"错误: 无法读取截图 {IMAGE_PATH}")  # 提示路径错误
        return
    h, w = img.shape[:2]  # 截图的高和宽
    print(f"截图尺寸: {w}x{h}")
    print(f"模板裁剪: {TEMPLATE_CROP} (小) / {TEMPLATE_CROP_BIG} (大)")
    print("-" * 80)

    # ---- 准备模板 ----
    ty1, ty2, tx1, tx2 = TEMPLATE_CROP  # 解包小模板裁剪坐标
    tpl_small = img[ty1:ty2, tx1:tx2]  # 裁剪小模板 (约 24x29, 模拟处决按键)
    by1, by2, bx1, bx2 = TEMPLATE_CROP_BIG  # 解包大模板裁剪坐标
    tpl_big = img[by1:by2, bx1:bx2]  # 裁剪大模板 (100x100, 对比用)

    # ---- 准备中央搜索区域 (对应 box_of_screen(*REGION)) ----
    rx1, ry1, rx2, ry2 = REGION  # 解包区域比例
    cx1, cy1 = round(rx1 * w), round(ry1 * h)  # 区域左上角像素坐标
    cx2, cy2 = round(rx2 * w), round(ry2 * h)  # 区域右下角像素坐标
    center = img[cy1:cy2, cx1:cx2]  # 裁剪出中央区域
    ch, cw = center.shape[:2]  # 中央区域的尺寸
    print(f"中央区域: ({cx1},{cy1}) -> ({cx2},{cy2}), 尺寸 {cw}x{ch}")
    print("-" * 80)

    # ---- 准备 720p 降采样版本 (对应 target_height=720) ----
    scale = TARGET_HEIGHT / h  # 缩放比例 (1440 -> 720 即 0.5)
    img_low = cv2.resize(img, (round(w * scale), TARGET_HEIGHT))  # 全屏降采样
    center_low = cv2.resize(center, (round(cw * scale), round(ch * scale)))  # 中央区域降采样
    tpl_small_low = cv2.resize(tpl_small,  # 小模板同步降采样
                               (max(1, round(tpl_small.shape[1] * scale)),
                                max(1, round(tpl_small.shape[0] * scale))))
    tpl_big_low = cv2.resize(tpl_big,  # 大模板同步降采样
                             (max(1, round(tpl_big.shape[1] * scale)),
                              max(1, round(tpl_big.shape[0] * scale))))

    # ---- 场景测试 ----
    # 场景 A: 最坏情况 — 全屏 + 原分辨率, 不做任何优化
    bench("A 全屏 1440p + 小模板", img, tpl_small)
    # 场景 B: 只限定中央区域 (对应 find_one 的 box 参数)
    bench("B 中央区域(55%宽60%高) + 小模板", center, tpl_small)
    # 场景 C: 只降采样 (对应 find_one 的 target_height 参数)
    bench("C 全屏缩到720p + 小模板缩放", img_low, tpl_small_low)
    # 场景 D: 区域限定 + 降采样 (OK-WW check_f_break 的方案, 推荐)
    bench("D 中央区域缩到720p + 小模板缩放 [推荐]", center_low, tpl_small_low)
    # 场景 E/F: 大模板对比, 验证"耗时主要由搜索区域决定, 与模板大小关系不大"
    bench("E 全屏 1440p + 大模板100x100", img, tpl_big)
    bench("F 中央区域 + 大模板100x100", center, tpl_big)

    print("-" * 80)

    # ---- ok 框架真实调用对照 ----
    if USE_OK_FRAMEWORK:  # 配置开启时运行框架对照测试
        bench_ok_framework(img, center, cx1, cy1, cw, ch)
        print("-" * 80)

    print("结论: 耗时与搜索区域像素数近似成正比; 区域限定+降采样可叠加生效。")
    print("      对比场景 A 和 D 即可看出 OK-WW 方案的优化幅度。")
    print("      G/H/I 与 A/B/D 的差值即框架调用层的额外开销 (预期为毫秒以内)。")


if __name__ == "__main__":  # 直接运行本文件时执行
    main()
