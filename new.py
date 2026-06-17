#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PiggyCell 自动游戏机器人
支持自动玩游戏、获取游戏代码、记录分数
"""

import json
import os
import sys
import time
import logging
import requests
import schedule
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import random
import colorlog
from fake_useragent import UserAgent
import warnings
import urllib3

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

class PiggyGameBot:
    def __init__(self, config_path: str = "config/config.json"):
        """初始化游戏机器人"""
        self.config_path = config_path
        self.config = self.load_config()
        self.accounts = self.load_accounts()
        self.proxies = self.load_proxies()
        self.user_agent = UserAgent()
        self.setup_logging()
        
    def load_config(self) -> Dict:
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.error(f"Config not found: {self.config_path}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            self.logger.error(f"配置文件格式错误: {e}")
            sys.exit(1)
    
    def load_accounts(self) -> List[Dict[str, str]]:
        """加载Akun信息"""
        json_accounts_path = "config/checkin-acc.json"
        
        try:
            with open(json_accounts_path, 'r', encoding='utf-8') as f:
                accounts_data = json.load(f)
                accounts = []
                for account in accounts_data.get('accounts', []):
                    if account.get('enabled', True):
                        accounts.append({
                            'name': account['name'],
                            'session_token': account['session_token'],
                            'cookies': account.get('cookies', ''),
                            'description': account.get('description', '')
                        })
                return accounts
        except FileNotFoundError:
            print("Kesalahan: Konfigurasi Akun tidak ditemukan, harap buat satu.config/checkin-acc.json文件")
            return []
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Peringatan: Format file konfigurasi akun JSON tidak tepat.: {e}")
            return []
    
    def load_proxies(self) -> List[str]:
        """Memuat informasi proxy"""
        proxies = []
        try:
            with open("proxy.txt", 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        proxies.append(line)
        except FileNotFoundError:
            print("Peringatan: File proxy.txt tidak ada.")
        
        return proxies
    
    def setup_logging(self):
        """设置日志"""
        log_level = getattr(logging, self.config.get('log_level', 'INFO'))
        
        # Buat Logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(log_level)
        
        # Hapus penangan yang ada
        self.logger.handlers.clear()
        
        # Proses berkas (tanpa warna)
        file_handler = logging.FileHandler('piggy_game_bot.log', encoding='utf-8')
        file_handler.setLevel(log_level)
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        
        # Prosesor konsol (dengan warna)
        console_handler = colorlog.StreamHandler()
        console_handler.setLevel(log_level)
        console_formatter = colorlog.ColoredFormatter(
            '%(log_color)s%(asctime)s - %(levelname)s - %(message)s%(reset)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )
        console_handler.setFormatter(console_formatter)
        
        # Tambahkan penangan
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def get_random_proxy(self) -> Optional[Dict[str, str]]:
        """获取随机代理"""
        if not self.proxies:
            return None
        
        proxy_url = random.choice(self.proxies)
        return {
            'http': proxy_url,
            'https': proxy_url
        }
    
    def get_random_user_agent(self) -> str:
        """Mengambil User-Agent dari full list user_agents.txt"""
        try:
            # Jika file user agent belum dimuat, load dulu
            if not hasattr(self, 'full_user_agents'):
                ua_path = "user_agents.txt"
                if os.path.exists(ua_path):
                    with open(ua_path, "r", encoding="utf-8") as f:
                        self.full_user_agents = [line.strip() for line in f if line.strip()]
                else:
                    # Jika file tidak ada, fallback ke fake_useragent
                    return self.user_agent.random
            
            # Jika list ada dan tidak kosong, pilih random
            if self.full_user_agents:
                return random.choice(self.full_user_agents)
            
            # fallback terakhir
            return self.user_agent.random

        except Exception:
            return self.user_agent.random

    
    def get_game_id(self, account: Dict[str, str]) -> Optional[str]:
        """ID game"""
        try:
            # Hasilkan ID game acak
            import uuid
            import time
            
            # Hasilkan ID game berdasarkan stempel waktu dan angka acak.
            timestamp = int(time.time() * 1000)  # waktu milidetik
            random_part = str(uuid.uuid4()).replace('-', '')[:8]  # string acak 8 digit
            game_id = f"{timestamp}_{random_part}"
            
            self.logger.info(f"Akun {account['name']} ID game: {game_id}")
            return game_id
                
        except Exception as e:
            self.logger.error(f"Akun {account['name']} ID game失败: {e}")
            return None
    
    def get_game_code(self, account: Dict[str, str]) -> Optional[str]:
        """Dapatkan kode game"""
        try:
            # Generate a game ID as game code
            game_id = self.get_game_id(account)
            if not game_id:
                self.logger.warning(f"Akun {account['name']} 无法ID game")
                return None
            
            # Use the generated game ID directly as the game code.
            self.logger.info(f"Akun {account['name']} 使用生成的游戏ID作为游戏代码: {game_id}")
            return game_id
                
        except Exception as e:
            self.logger.error(f"Akun {account['name']} 获取游戏代码失败: {e}")
            return None
    
    def check_game_code(self, account: Dict[str, str], game_code: str) -> bool:
        """检查游戏代码"""
        try:
            headers = {
                'accept': '*/*',
                'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7,ja;q=0.6,fr;q=0.5,ru;q=0.4,und;q=0.3',
                'content-type': 'application/json',
                'origin': 'https://app.piggycell.io',
                'referer': 'https://app.piggycell.io/en/game/piggy-game?mode=regular',
                'user-agent': self.get_random_user_agent(),
                'sec-ch-ua': '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"macOS"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'trpc-accept': 'application/jsonl',
                'x-trpc-source': 'nextjs-react'
            }
            
            cookies = f"__Secure-authjs.session-token={account['session_token']}"
            if account['cookies']:
                cookies += f"; {account['cookies']}"
            headers['cookie'] = cookies
            
            data = {"0": {"json": {"gameCode": game_code}}}
            
            proxy = self.get_random_proxy()
            session = requests.Session()
            session.verify = False
            
            response = session.post(
                "https://app.piggycell.io/api/trpc/piggyGame.checkGameCode?batch=1",
                headers=headers,
                json=data,
                proxies=proxy,
                timeout=30
            )
            
            if response.status_code == 200:
                self.logger.info(f"Akun {account['name']} 游戏代码 {game_code} 验证成功")
                return True
            else:
                self.logger.error(f"Akun {account['name']} 游戏代码验证失败，状态码: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Akun {account['name']} 游戏代码验证失败: {e}")
            return False
    
    def record_game_score(self, account: Dict[str, str], score: int) -> bool:
        """记录游戏分数"""
        try:
            headers = {
                'accept': '*/*',
                'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7,ja;q=0.6,fr;q=0.5,ru;q=0.4,und;q=0.3',
                'content-type': 'application/json',
                'origin': 'https://app.piggycell.io',
                'referer': 'https://app.piggycell.io/en/game/piggy-game?mode=regular',
                'user-agent': self.get_random_user_agent(),
                'sec-ch-ua': '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"macOS"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'trpc-accept': 'application/jsonl',
                'x-trpc-source': 'nextjs-react'
            }
            
            cookies = f"__Secure-authjs.session-token={account['session_token']}"
            if account['cookies']:
                cookies += f"; {account['cookies']}"
            headers['cookie'] = cookies
            
            data = {"0": {"json": {"score": score}}}
            
            proxy = self.get_random_proxy()
            session = requests.Session()
            session.verify = False
            
            response = session.post(
                "https://app.piggycell.io/api/trpc/piggyGame.recordGameScore?batch=1",
                headers=headers,
                json=data,
                proxies=proxy,
                timeout=30
            )
            
            if response.status_code == 200:
                self.logger.info(f"Akun {account['name']} 记录分数 {score} 成功")
                return True
            else:
                self.logger.error(f"Akun {account['name']} 记录分数失败，状态码: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Akun {account['name']} 记录分数失败: {e}")
            return False
    
    def play_single_game(self, account: Dict[str, str], game_round: int) -> bool:
        """执行单次游戏"""
        try:
            account_desc = f" ({account.get('description', '')})" if account.get('description') else ""
            self.logger.info(f"Akun {account['name']}{account_desc} 开始第{game_round}次游戏")
            
            # 1. 获取游戏代码
            game_code = self.get_game_code(account)
            if not game_code:
                self.logger.error(f"Akun {account['name']} 第{game_round}次游戏获取代码失败")
                return False
            
            # 如果游戏代码为None，说明没有游戏次数，跳过
            if game_code is None:
                return False
            
            # 2. 验证游戏代码
            if not self.check_game_code(account, game_code):
                self.logger.error(f"Akun {account['name']} 第{game_round}次游戏代码验证失败")
                return False
            
            # 3. 模拟游戏过程（这里可以添加实际的游戏逻辑）
            # 使用配置文件中的分数范围
            min_score = self.config.get('game_settings', {}).get('min_score', 55)
            max_score = self.config.get('game_settings', {}).get('max_score', 65)
            score = random.randint(min_score, max_score)
            self.logger.info(f"Akun {account['name']} 第{game_round}次游戏完成，得分: {score}")
            
            # 4. 记录分数
            if self.record_game_score(account, score):
                self.logger.info(f"Akun {account['name']} 第{game_round}次游戏完成")
                return True
            else:
                self.logger.error(f"Akun {account['name']} 第{game_round}次游戏记录分数失败")
                return False
                
        except Exception as e:
            self.logger.error(f"Akun {account['name']} 第{game_round}次游戏失败: {e}")
            return False
    
    def play_game(self, account: Dict[str, str]) -> bool:
        """执行多次游戏"""
        try:
            account_desc = f" ({account.get('description', '')})" if account.get('description') else ""
            games_count = self.config.get('game_settings', {}).get('games_per_session', 3)
            self.logger.info(f"Akun {account['name']}{account_desc} 开始执行{games_count}次游戏")
            
            success_count = 0
            for i in range(1, games_count + 1):
                result = self.play_single_game(account, i)
                if result is False:  # 如果返回False，说明没有游戏次数，跳出循环
                    self.logger.info(f"Akun {account['name']} 没有游戏次数，停止游戏")
                    break
                elif result:  # 如果返回True，说明游戏成功
                    success_count += 1
                
                # 游戏间延迟
                if i < games_count:  # 最后一次不需要延迟
                    delay = self.config.get('game_settings', {}).get('game_delay', 2)
                    self.logger.info(f"Akun {account['name']} 等待{delay}秒后进行下一次游戏...")
                    time.sleep(delay)
            
            self.logger.info(f"Akun {account['name']} 完成{games_count}次游戏，成功: {success_count}/{games_count}")
            return success_count > 0  # 只要有一次成功就认为成功
            
        except Exception as e:
            self.logger.error(f"Akun {account['name']} 游戏失败: {e}")
            return False
    
    def play_all_accounts(self):
        """为所有Akun执行游戏"""
        if not self.accounts:
            self.logger.warning("没有找到Akun信息")
            return
        
        self.logger.info(f"开始为 {len(self.accounts)} 个Akun执行游戏")
        
        success_count = 0
        for account in self.accounts:
            if self.play_game(account):
                success_count += 1
            
            # Akun间延迟
            time.sleep(random.uniform(1, 2))
        
        self.logger.info(f"游戏完成，成功: {success_count}/{len(self.accounts)}")
    
    def run_scheduler(self):
        """运行定时任务"""
        # 启动时先执行一次游戏
        self.logger.info("程序启动，立即执行一次游戏...")
        self.play_all_accounts()
        
        # 设置定时任务 - 使用配置文件中的间隔时间
        interval = self.config.get('game_settings', {}).get('session_interval', 2)
        schedule.every(interval).seconds.do(self.play_all_accounts)
        
        self.logger.info(f"定时游戏已设置，每{interval}秒执行一次")
        self.logger.info("按 Ctrl+C 停止程序")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(2)  # 每分钟检查一次
        except KeyboardInterrupt:
            self.logger.info("程序已停止")
    
    def run_once(self):
        """立即执行一次游戏"""
        self.play_all_accounts()

def main():
    """主函数"""
    if len(sys.argv) > 1 and sys.argv[1] == '--once':
        # 立即执行一次游戏
        bot = PiggyGameBot()
        bot.run_once()
    else:
        # 运行定时任务
        bot = PiggyGameBot()
        bot.run_scheduler()

if __name__ == "__main__":
    main()
