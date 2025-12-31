import os
import json
import time
from abc import ABC, abstractmethod
from pathlib import Path


class BaseRadar(ABC):
    """KOL监控基类"""

    def __init__(self, state_file_name, dingtalk_client, log_prefix):
        self.base_dir = Path(__file__).parent
        self.state_file = self.base_dir / state_file_name
        self.dingtalk = dingtalk_client
        self.log_prefix = log_prefix  # 日志前缀，用于区分不同监控
    
    def load_state(self):
        """加载监控状态"""
        if not self.state_file.exists():
            return self.get_initial_state()
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return self.get_initial_state()
    
    def save_state(self, state):
        """保存监控状态"""
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    
    @abstractmethod
    def get_initial_state(self):
        """获取初始状态（子类实现）"""
        pass
    
    @abstractmethod
    def fetch_data(self):
        """获取数据（子类实现）"""
        pass
    
    @abstractmethod
    def process_new_items(self, state):
        """处理新数据项（子类实现）
        
        返回: (has_new, new_state)
        """
        pass
    
    @abstractmethod
    def get_api_url(self):
        """获取API URL（子类实现）"""
        pass
    
    def monitor(self):
        """主监控循环"""
        api_url = self.get_api_url()
        if not api_url:
            print(f"{self.log_prefix} ❌ 错误: 未找到 API URL 环境变量")
            return

        print(f"{self.log_prefix} 🚀 开始监控")

        while True:
            try:
                state = self.load_state()



                # 子类实现具体的数据处理
                has_new, new_state = self.process_new_items(state)

                if not has_new:
                    print(f"{self.log_prefix} 💤 暂无新消息")

                # 保存状态
                self.save_state(new_state)

                time.sleep(60)

            except KeyboardInterrupt:
                print(f"{self.log_prefix} 🛑 停止监控")
                break
            except Exception as e:
                print(f"{self.log_prefix} ❌ 监控异常: {e}")
                time.sleep(60)
