import os
import time
import hmac
import hashlib
import base64
import urllib.parse
import requests


class DingTalkClient:
    """钉钉消息推送客户端"""
    
    def __init__(self, webhook=None, secret=None):
        self.webhook = webhook or os.getenv("DINGTALK_WEBHOOK")
        self.secret = secret or os.getenv("DINGTALK_SECRET")
    
    def get_sign(self):
        """生成钉钉签名"""
        timestamp = str(round(time.time() * 1000))
        secret_enc = self.secret.encode('utf-8')
        string_to_sign = '{}\n{}'.format(timestamp, self.secret)
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        return timestamp, sign
    
    def send(self, content, title="通知", at_all=True):
        """发送钉钉消息"""
        if not self.webhook or not self.secret:
            print("错误: 未配置 DINGTALK_WEBHOOK 或 DINGTALK_SECRET")
            return False
        
        timestamp, sign = self.get_sign()
        url = f"{self.webhook}&timestamp={timestamp}&sign={sign}"
        
        headers = {'Content-Type': 'application/json'}
        # 改为 Markdown 格式
        data = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": content
            },
            "at": {
                "isAtAll": at_all
            }
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            if response.status_code == 200:
                print("✅ 钉钉消息发送成功")
                return True
            else:
                print(f"❌ 钉钉发送失败: {response.text}")
                return False
        except Exception as e:
            print(f"❌ 发送异常: {e}")
            return False
