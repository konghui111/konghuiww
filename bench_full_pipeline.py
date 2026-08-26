# ============================================================
# 完整流程耗时测试: 截图 → 识别 → 返回
# ============================================================
# 用途: 测量飞雪动作函数中一次完整检测循环的真实耗时。
#
# 复现目标 — src/character/__init__.py 的 check_skill_available(),
# 它在 feixue.py 中被高频调用 (如 feixue_x() 的循环里每 10~50ms 一次):
#   步骤1  get_location_box(area)        获取 _location 特征的预定义区域
#   步骤2  task.next_frame()             截图 (框架源码确认: 同步调用截图方法,
#                                         无后台缓存线程, 耗时=截图方法本身)
#   步骤3  calculate_color_percentage()  找色 (白色占比)
#   步骤4  find_one(skill_image)         找图 (阈值 0.7, limit=1 轻量路径)
#   步骤5  返回 1/0
#
# 截图部分使用 ok 框架真实的截图类:
#   - WindowsGraphicsCaptureMethod (WGC)  — 项目首选截图方式
#   - capture_by_bitblt (RenderFull)      — 项目备选截图方式
#   注意: WGC 每次调用会等待一个新帧送达 (上限 60fps), 所以单次耗时
#         包含帧送达间隔, 这是 WGC 的固有特性而非性能缺陷。
#
# 窗口选择:
#   优先查找鸣潮游戏进程 (数据最真实); 游戏未运行时自动选择屏幕上
#   最大的可见窗口做替代 (截图耗时主要取决于分辨率和截图方式,
#   替代窗口可给出近似参考, 结果中会标注实际使用的窗口)。
#
# 使用方法:
#   1. (可选) 启动鸣潮游戏, 数据更真实
#   2. 运行: python bench_full_pipeline.py
# ============================================================

import os  # 路径处理
import threading  # WGC 需要的退出事件
import time  # 计时

import cv2  # OpenCV
import numpy as np  # 数组运算
import win32api  # 进程句柄
import win32con  # Windows 常量
import win32gui  # 窗口枚举
import win32process  # 窗口→进程

# ==================== 配置区 ====================

# 鸣潮游戏进程名 (小写比较), 找到则直接对游戏截图
GAME_EXE_NAMES = ["client-win64-shipping.exe", "鸣潮.exe"]

# 项目的 COCO 标注文件 (识别部分加载特征用)
COCO_JSON = r"e:\konghuiww\konghuiww\assets\coco_annotations.json"

# 重复测试次数
CAPTURE_REPEAT = 10  # 截图测试次数 (WGC 每次约 16ms+, 不宜太多)
DETECT_REPEAT = 20  # 识别测试次数

# 复现的检测场景 (与 feixue.py 中的真实调用一一对应):
# (场景名, area 区域名, 找色阈值, 找图特征名) — 找图特征名为空则只做找色
SCENARIOS = [
    ("check_skill_available(task, 'e') 纯找色", "e", 0.02, ""),
    ("check_skill_available(task, 'r', 'feixue_r1') 找色+找图", "r", 0.01, "feixue_r1"),
    ("check_skill_available(task, 'feixue_a', 'feixue_x') feixue_x高频循环", "feixue_a", 0, "feixue_x"),
]

# 找色用的白色范围 (与 check_skill_available 内部一致)
WHITE = {'b': (255, 255), 'g': (255, 255), 'r': (255, 255)}

# ==================== 配置区结束 ====================


def find_game_hwnd():  # 查找鸣潮游戏窗口句柄
    found = []  # 找到的窗口句柄列表

    def callback(hwnd, _):  # EnumWindows 回调
        if not win32gui.IsWindowVisible(hwnd):  # 跳过不可见窗口
            return True
        try:  # 获取窗口所属进程的可执行文件名
            _, pid = win32process.GetWindowThreadProcessId(hwnd)  # 窗口→进程ID
            proc = win32api.OpenProcess(  # 打开进程读取文件名
                win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ, False, pid)
            exe = os.path.basename(win32process.GetModuleFileNameEx(proc, 0)).lower()  # 进程名小写
            win32api.CloseHandle(proc)  # 关闭进程句柄
            if exe in GAME_EXE_NAMES:  # 是鸣潮进程
                found.append(hwnd)  # 记录句柄
        except Exception:  # 权限不足等异常, 跳过
            pass
        return True

    win32gui.EnumWindows(callback, None)  # 枚举所有顶层窗口
    return found[0] if found else 0  # 返回第一个找到的, 没有返回 0


def find_largest_window():  # 查找最大的普通应用窗口 (游戏未运行时的替代目标)
    best = [0, 0, ""]  # [面积, 句柄, 标题]
    # 排除的窗口类名: 桌面/任务栏等系统层 (桌面可能跨多屏, 尺寸不具代表性)
    skip_classes = {"progman", "shell_traywnd", "workerw", "shell_secondarytraywnd"}

    def callback(hwnd, _):  # EnumWindows 回调
        if not win32gui.IsWindowVisible(hwnd) or win32gui.IsIconic(hwnd):  # 跳过不可见/最小化
            return True
        if win32gui.GetClassName(hwnd).lower() in skip_classes:  # 跳过系统层窗口
            return True
        if not win32gui.GetWindowText(hwnd):  # 跳过无标题窗口
            return True
        rect = win32gui.GetWindowRect(hwnd)  # 窗口矩形
        w, h = rect[2] - rect[0], rect[3] - rect[1]  # 窗口宽高
        if w < 800 or h < 600:  # 跳过太小的窗口
            return True
        area = w * h  # 计算面积
        if area > best[0]:  # 比当前记录更大
            best[0], best[1], best[2] = area, hwnd, win32gui.GetWindowText(hwnd)  # 更新记录
        return True

    win32gui.EnumWindows(callback, None)  # 枚举所有顶层窗口
    return best[1], best[2]  # 返回句柄和标题


class FakeHwndWindow:  # 模拟 ok 框架 HwndWindow 的最小接口 (供截图类使用)
    """
    WGC 截图类只用到这几个属性, 用鸭子类型模拟, 避免构造完整框架对象。
    依据: ok/device/capture_methods/windows_graphics.py 的属性访问。
    """

    def __init__(self, hwnd, width, height):  # 构造函数
        self.app_exit_event = threading.Event()  # 退出事件 (未设置=正常运行)
        self.exists = True  # 窗口存在标志
        self.hwnd = hwnd  # 窗口句柄
        self.capture_target_signature = hwnd  # 截图目标签名 (变化时重启截图)
        self.width = width  # 客户区宽度 (WGC 裁剪边框用)
        self.height = height  # 客户区高度
        self.hwnds = [hwnd]  # 子窗口列表, 只有 1 个时合成步骤自动跳过


def bench_wgc(hwnd, client_w, client_h):  # WGC 截图耗时测试
    try:  # 导入并构造 WGC 截图对象
        from ok.device.capture_methods import WindowsGraphicsCaptureMethod  # WGC 截图类
        cap = WindowsGraphicsCaptureMethod(FakeHwndWindow(hwnd, client_w, client_h))  # 构造
    except Exception as e:  # 构造失败 (如系统不支持)
        print(f"  WGC 初始化失败, 跳过: {e}")
        return None

    for i in range(3):  # 预热: 会话刚启动时首帧较慢, 不计入统计
        t0 = time.perf_counter()  # 开始计时
        warm_frame = cap.get_frame()  # 取帧
        if warm_frame is None and (time.perf_counter() - t0) > 2:  # 预热就超时=静态窗口不送帧
            print("  WGC 对静态窗口不送达新帧, 跳过 (游戏中画面持续变化, 无此问题)")
            cap.close()  # 释放截图资源
            return None

    ts = []  # 耗时记录
    frames_ok = 0  # 成功拿到帧的次数
    for i in range(CAPTURE_REPEAT):  # 重复测试
        t0 = time.perf_counter()  # 开始计时
        frame = cap.get_frame()  # 获取一帧 (内部等待新帧送达)
        elapsed = (time.perf_counter() - t0) * 1000  # 本次耗时
        ts.append(elapsed)  # 记录毫秒
        if frame is not None:  # 成功
            frames_ok += 1
        # 快速失败: 首次测量就超时(内部4秒)说明该窗口内容静态不送帧, 不再继续
        if i == 0 and (frame is None or elapsed > 2000):  # 第一次就超时或无帧
            print("  WGC 对静态窗口不送达新帧, 跳过 (游戏中画面持续变化, 无此问题)")
            cap.close()  # 释放截图资源
            return None

    ts.sort()  # 排序
    if frames_ok == 0:  # 一帧都没拿到
        print("  WGC 未送达任何帧, 跳过")
        cap.close()  # 释放截图资源
        return None
    print(f"  WGC 截图: 中位数 {ts[CAPTURE_REPEAT // 2]:7.2f} ms   最大 {ts[-1]:7.2f} ms   ({frames_ok}/{CAPTURE_REPEAT} 次成功)")
    return cap  # 返回截图对象, 后续取帧用


def bench_bitblt(hwnd):  # BitBlt (RenderFull) 截图耗时测试
    from ok.device.capture_methods import capture_by_bitblt, BitBltCtxDummy  # 框架 BitBlt 工具
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)  # 窗口矩形
    w, h = right - left, bottom - top  # 窗口尺寸
    ctx = BitBltCtxDummy()  # BitBlt 上下文 (缓存 DC/位图)

    capture_by_bitblt(ctx, hwnd, w, h, 0, 0, True)  # 预热: 首次调用会创建 DC, 不计入

    ts = []  # 耗时记录
    frame = None  # 最后一帧
    for _ in range(DETECT_REPEAT):  # 重复测试
        t0 = time.perf_counter()  # 开始计时
        frame = capture_by_bitblt(ctx, hwnd, w, h, 0, 0, True)  # 截图 (含 PrintWindow)
        ts.append((time.perf_counter() - t0) * 1000)  # 记录毫秒
    ts.sort()  # 排序
    print(f"  BitBlt RenderFull 截图: 中位数 {ts[DETECT_REPEAT // 2]:7.2f} ms   最大 {ts[-1]:7.2f} ms")
    return frame[:, :, :3] if frame is not None else None  # BGRA→BGR 返回


def bench_detect(frame):  # 识别耗时测试 (复现 check_skill_available 的各场景)
    from ok.feature.FeatureSet import FeatureSet  # 特征集
    from ok import Box  # 区域类
    from ok.util.color import calculate_color_percentage  # 框架找色函数

    if frame is None:  # 没有可用帧
        print("  无可用截图, 跳过识别测试")
        return

    h, w = frame.shape[:2]  # 帧尺寸
    # 构造特征集: 偏移/阈值与项目 src/config.py 一致
    fs = FeatureSet(False, COCO_JSON, 0.002, 0.002, default_threshold=0.8)
    fs.check_size(frame)  # 先按帧尺寸初始化, 保证特征按正确比例缩放加载

    def get_box(area):  # 复现 get_location_box: 获取 _location 特征的区域
        fs.ensure_feature(f"{area}_location")  # 确保特征已加载
        f = fs.feature_dict.get(f"{area}_location")  # 取特征
        if f is None:  # 特征不存在
            return None
        return Box(f.x, f.y, f.width, f.height, name=f"{area}_location")  # 构造 Box

    print(f"  (识别测试在 {w}x{h} 帧上进行, 特征自动缩放到此分辨率)")
    for name, area, color_th, image_name in SCENARIOS:  # 遍历每个场景
        box = get_box(area)  # 获取区域
        if box is None:  # 区域特征不存在
            print(f"  {name}: 特征 {area}_location 不存在, 跳过")
            continue

        # ---- 分阶段计时: 找色 ----
        color_ts = []  # 找色耗时记录
        for _ in range(DETECT_REPEAT):  # 重复测试
            t0 = time.perf_counter()  # 开始计时
            pct = calculate_color_percentage(frame, WHITE, box)  # 找色
            color_ts.append((time.perf_counter() - t0) * 1000)  # 记录毫秒
        color_ms = sorted(color_ts)[DETECT_REPEAT // 2]  # 中位数

        # ---- 分阶段计时: 找图 (如有) ----
        image_ms = 0.0  # 找图耗时
        if image_name:  # 场景包含找图
            fs.find_one_feature(mat=frame, category_name=image_name,
                                box=box, threshold=0.7, limit=1)  # 预热 (加载模板)
            image_ts = []  # 找图耗时记录
            for _ in range(DETECT_REPEAT):  # 重复测试
                t0 = time.perf_counter()  # 开始计时
                fs.find_one_feature(mat=frame, category_name=image_name,
                                    box=box, threshold=0.7, limit=1)  # 找图 (与 find_one 参数一致)
                image_ts.append((time.perf_counter() - t0) * 1000)  # 记录毫秒
            image_ms = sorted(image_ts)[DETECT_REPEAT // 2]  # 中位数

        print(f"  {name}")
        print(f"      找色 {color_ms:6.2f} ms (白色占比 {pct:.4f})" +
              (f"   + 找图 {image_ms:6.2f} ms" if image_name else "") +
              f"   → 识别合计 {color_ms + image_ms:6.2f} ms")


def main():  # 主函数
    # 设置 DPI 感知, 保证窗口坐标准确 (失败不影响运行)
    try:
        import ctypes  # 系统调用
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-Monitor DPI 感知
    except Exception:
        pass

    hwnd = find_game_hwnd()  # 优先查找鸣潮窗口
    if hwnd:  # 找到游戏
        title = win32gui.GetWindowText(hwnd)  # 窗口标题
        print(f"目标窗口: 鸣潮游戏 ({title})")
    else:  # 游戏未运行
        hwnd, title = find_largest_window()  # 用最大可见窗口替代
        if not hwnd:  # 连替代窗口都没有
            print("错误: 未找到任何可见窗口")
            return
        print(f"目标窗口: 替代窗口 (游戏未运行) — \"{title}\"")
        print("注意: 截图耗时主要取决于分辨率和方式, 替代窗口数据仅供参考;")
        print("      识别区域基于 2560x1440 游戏 UI, 在非游戏窗口上不保证能匹配到目标。")

    # 客户区尺寸 (WGC 裁剪边框用)
    _, _, cw, ch = win32gui.GetClientRect(hwnd)  # 客户区矩形

    print("-" * 70)
    print("【阶段1: 截图耗时】(对应 task.next_frame())")
    cap = bench_wgc(hwnd, cw, ch)  # WGC 测试
    bitblt_frame = bench_bitblt(hwnd)  # BitBlt 测试

    print("-" * 70)
    print("【阶段2: 识别耗时】(对应 找色+找图, 在已截取的帧上进行)")
    # 取一帧用于识别测试: 优先 WGC 帧, 其次 BitBlt 帧
    frame = None
    if cap is not None:  # WGC 可用
        frame = cap.get_frame()  # 取一帧
    if frame is None:  # WGC 不可用或取帧失败
        frame = bitblt_frame  # 用 BitBlt 帧
    bench_detect(frame)  # 识别测试

    print("-" * 70)
    print("说明: 完整一次'截图→识别→返回' = 阶段1截图耗时 + 阶段2识别合计。")
    print("      WGC 单次耗时含等待新帧送达的间隔 (60fps 上限), 连续调用时")
    print("      这个间隔无法省略; BitBlt 为纯同步拷贝, 无此限制。")
    if cap is not None:  # 清理 WGC 资源
        cap.close()


if __name__ == "__main__":  # 直接运行本文件时执行
    main()
