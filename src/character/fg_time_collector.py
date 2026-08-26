"""
fg_time 自动收集器
在打轴模式执行完整的启动/循环阶段后, 保存每个动作的实际前台时间
仅收集已完整完成的阶段, 中途停止的战斗不保存, 避免错误数据
每个动作只保留耗时最短的 3 次记录, 用于自动模式调度优化
"""
import json
import os
import time

KEEP_COUNT = 3  # 每个动作保留的最短记录数


class FgTimeCollector:
    """
    fg_time 自动收集器
    在打轴模式中测量每个动作的实际前台时间, 仅在完整阶段完成后保存
    每个动作只保留耗时最短的 KEEP_COUNT 次记录, 代表最佳表现
    收集到的数据可供自动模式的评分函数使用
    """

    def __init__(self, save_path=None):
        self._save_path = save_path or os.path.join(
            os.path.dirname(__file__), "fg_time_data.json"
        )
        self._measurements = {}   # 当前阶段的测量缓冲 {动作key: [fg_time列表]}
        self._completed = {}      # 已完成的测量数据 {动作key: [fg_time列表, 最多KEEP_COUNT个, 最短的优先]}
        self._action_count = 0    # 当前阶段已测量的动作总数
        self._expected_count = 0  # 当前阶段预期的动作总数 (用于验证完整性)
        self._load()              # 加载历史数据

    # ---- 内部方法 ----

    @staticmethod
    def _make_key(character_name, action_name, branch_id="default"):  # 构造动作唯一标识
        return f"{character_name}.{action_name}.{branch_id}"

    def _load(self):  # 从文件加载历史数据
        if os.path.isfile(self._save_path):
            try:
                with open(self._save_path, "r", encoding="utf-8") as f:
                    self._completed = json.load(f)
            except Exception:
                self._completed = {}

    # ---- 测量接口 (由 CharacterAutoTask 在打轴流程中调用) ----

    def start_measurement(self, expected_count):
        """
        开始新阶段的测量, 在阶段第一个动作执行前调用
        :param expected_count: 该阶段预期的动作总数, 用于完成时验证完整性
        """
        self._measurements = {}
        self._action_count = 0
        self._expected_count = expected_count

    def record_measurement(self, character_name, action_name, fg_time, branch_id="default"):
        """
        记录一个动作的实测前台时间, 在每个动作执行完成后调用
        :param character_name: 角色名
        :param action_name: 动作名
        :param fg_time: 实测前台时间 (秒), 由 开始等待→收到完成信号 的时间差计算
        :param branch_id: 分支标识 (可选), 用于区分同一动作的不同执行路径
        """
        if fg_time <= 0 or fg_time > 60:  # 异常值过滤: 负数或超过 60 秒的跳过
            return
        key = self._make_key(character_name, action_name, branch_id)
        if key not in self._measurements:
            self._measurements[key] = []
        self._measurements[key].append(fg_time)
        self._action_count += 1

    def complete_phase(self):
        """
        标记当前阶段已完成, 将缓冲区数据合并到已完成数据中
        仅当实际动作数 == 预期动作数时才保存, 确保阶段是完整执行的
        合并后每个动作只保留耗时最短的 KEEP_COUNT 次记录
        调用后清空缓冲区, 准备接受下一阶段
        """
        if self._action_count != self._expected_count:
            # 动作数不匹配, 阶段不完整, 丢弃缓冲区
            self._measurements = {}
            self._action_count = 0
            self._expected_count = 0
            return
        # 阶段完整, 合并数据 (只保留最短的 KEEP_COUNT 次)
        for key, times in self._measurements.items():
            if key not in self._completed:
                self._completed[key] = []
            self._completed[key].extend(times)
            self._completed[key].sort()  # 升序排序, 最短的在前
            self._completed[key] = self._completed[key][:KEEP_COUNT]  # 只保留最短的 N 个
        # 清空缓冲区
        self._measurements = {}
        self._action_count = 0
        self._expected_count = 0
        # 持久化
        self._save()

    def _save(self):  # 将已完成数据保存到 JSON 文件
        try:
            os.makedirs(os.path.dirname(self._save_path), exist_ok=True)
            with open(self._save_path, "w", encoding="utf-8") as f:
                json.dump(self._completed, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ---- 查询接口 (供自动模式评分函数使用) ----

    def get_avg_fg_time(self, character_name, action_name, branch_id="default"):
        """
        获取指定动作的最优前台时间 (已保留的最短记录的平均值)
        :param character_name: 角色名
        :param action_name: 动作名
        :param branch_id: 分支标识 (可选), 查询特定分支的时间
        :return: 平均最优前台时间 (秒), 无数据返回 None
        """
        key = self._make_key(character_name, action_name, branch_id)
        data = self._completed.get(key, [])
        if not data:
            return None
        return sum(data) / len(data)

    def get_character_data(self, character_name):
        """
        获取指定角色的所有动作的实测数据
        :param character_name: 角色名
        :return: {动作名: {"avg": 最优平均fg, "best": 最快fg, "samples": 样本数}}
        """
        prefix = f"{character_name}."
        result = {}
        for key, data in self._completed.items():
            if key.startswith(prefix) and data:
                suffix = key[len(prefix):]  # 包含分支标识
                result[suffix] = {
                    "avg": sum(data) / len(data),
                    "best": data[0],  # 已排序, 第一个是最短的
                    "samples": len(data),
                }
        return result

    def clear(self):  # 清空所有已收集的数据 (含磁盘文件)
        self._completed = {}
        self._measurements = {}
        self._action_count = 0
        self._expected_count = 0
        if os.path.isfile(self._save_path):
            os.remove(self._save_path)
