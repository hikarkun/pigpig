#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PiggyCell Auto Check-in Bot
Supports multi-account, scheduled check-in, proxy configuration
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
import base64

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

class PiggyCellBot:
    def __init__(self, config_path: str = "config/config.json"):
        """Initialize bot"""
        self.config_path = config_path
        self.config = self.load_config()
        self.accounts = self.load_accounts()
        self.proxies = self.load_proxies()
        self.user_agent = UserAgent()
        self.setup_logging()
        
    def load_config(self) -> Dict:
        """Load config file"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.error(f"Config file does not exist: {self.config_path}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            self.logger.error(f"Config file format error: {e}")
            sys.exit(1)
    
    def load_accounts(self) -> List[Dict[str, str]]:
        """Load account information"""
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
            print("Error: Account config file does not exist, please create config/checkin-acc.json")
            return []

        except (json.JSONDecodeError, KeyError) as e:
            print(f"Warning: JSON account config file format error: {e}")
            return []
    
    def load_proxies(self) -> List[str]:
        """Load proxy list"""
        proxies = []
        try:
            with open("config/proxy.txt", 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        proxies.append(line)
        except FileNotFoundError:
            print("Warning: proxy.txt file does not exist")
        
        return proxies
    
    
    def setup_logging(self):
        """Set up logging"""
        log_level = getattr(logging, self.config.get('log_level', 'INFO'))
        
        # Create logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(log_level)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # File handler (no color)
        file_handler = logging.FileHandler('config/bot.log', encoding='utf-8')
        file_handler.setLevel(log_level)
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        
        # Console handler (with color)
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
        
        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def get_random_proxy(self) -> Optional[Dict[str, str]]:
        """Get a random proxy"""
        if not self.proxies:
            return None
        
        proxy_url = random.choice(self.proxies)
        return {
            'http': proxy_url,
            'https': proxy_url
        }
    
    
    def get_random_user_agent(self) -> str:
        """Get random User-Agent"""
        try:
            return self.user_agent.random
        except Exception:
            # Fallback User-Agent list
            user_agents = [
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0'
            ]
            return random.choice(user_agents)
    
    def check_token_validity(self, account: Dict[str, str]) -> bool:
        """Check token validity"""
        try:
            session_token = account['session_token']
            
            # Check placeholder token
            if not session_token or session_token.startswith('your') or 'session_token' in session_token.lower():
                self.logger.warning(f"Account {account['name']}: token is placeholder, please update real session_token")
                return False
            
            # Try decode JWT token
            if '.' in session_token and session_token.count('.') >= 2:
                parts = session_token.split('.')
                if len(parts) >= 2:
                    payload = parts[1]
                    payload += '=' * (4 - len(payload) % 4)
                    
                    try:
                        decoded = base64.b64decode(payload)
                        token_data = json.loads(decoded)
                        
                        if 'exp' in token_data:
                            exp_timestamp = token_data['exp']
                            exp_datetime = datetime.fromtimestamp(exp_timestamp)
                            current_time = datetime.now()
                            
                            if exp_datetime <= current_time + timedelta(minutes=30):
                                self.logger.warning(f"Account {account['name']} token will expire within 30 minutes")
                                return False
                            
                            remaining = exp_datetime - current_time
                            hours = remaining.total_seconds() / 3600
                            self.logger.info(f"Account {account['name']} token valid, remaining: {hours:.1f} hours")
                            return True
                        else:
                            self.logger.info(f"Account {account['name']} token valid but no expiry info")
                            return True
                            
                    except (base64.binascii.Error, json.JSONDecodeError):
                        return self.test_token_with_api(account)
            else:
                return self.test_token_with_api(account)
                
        except Exception as e:
            self.logger.error(f"Error checking token of {account['name']}: {e}")
            return True
    
    def test_token_with_api(self, account: Dict[str, str]) -> bool:
        """Test token validity via API"""
        try:
            headers = self.config['headers'].copy()
            headers['user-agent'] = self.get_random_user_agent()
            
            cookies = f"__Secure-authjs.session-token={account['session_token']}"
            if account['cookies']:
                cookies += f"; {account['cookies']}"
            headers['cookie'] = cookies
            
            proxy = self.get_random_proxy()
            session = requests.Session()
            session.verify = False
            
            response = session.get(
                "https://app.piggycell.io/api/trpc/user.me?batch=1",
                headers=headers,
                proxies=proxy,
                timeout=10
            )
            
            if response.status_code == 200:
                self.logger.info(f"Account {account['name']} token valid (API test)")
                return True
            else:
                self.logger.warning(f"Account {account['name']} token possibly invalid (status {response.status_code})")
                return False
                
        except Exception as e:
            self.logger.warning(f"API test failed for {account['name']}: {e}, assuming valid")
            return True
    
    def sign_in(self, account: Dict[str, str]) -> bool:
        """Perform check-in"""
        if not self.check_token_validity(account):
            self.logger.error(f"Account {account['name']} token invalid or expiring soon, skipping")
            return False
        
        retry_times = self.config.get('retry_times', 3)
        retry_delay = self.config.get('retry_delay', 5)
        
        for attempt in range(retry_times):
            try:
                headers = self.config['headers'].copy()
                user_agent = self.get_random_user_agent()
                headers['user-agent'] = user_agent
                
                cookies = f"__Secure-authjs.session-token={account['session_token']}"
                if account['cookies']:
                    cookies += f"; {account['cookies']}"
                
                headers['cookie'] = cookies
                
                today = datetime.now().strftime('%Y-%m-%d')
                data = {"0": {"json": {"userDate": today}}}
                
                proxy = self.get_random_proxy()
                
                account_desc = f" ({account.get('description', '')})" if account.get('description') else ""
                if attempt == 0:
                    proxy_info = "no proxy"
                    if proxy:
                        proxy_url = proxy.get('http', '')
                        proxy_info = f"proxy: {proxy_url}"
                    
                    self.logger.info(
                        f"Account {account['name']}{account_desc} starting check-in, "
                        f"User-Agent: {user_agent[:50]}..., {proxy_info}"
                    )
                
                session = requests.Session()
                session.verify = False
                session.mount('https://', requests.adapters.HTTPAdapter(max_retries=3))
                
                response = session.post(
                    self.config['api_url'],
                    headers=headers,
                    json=data,
                    proxies=proxy,
                    timeout=30
                )
                
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        
                        already_checked = False
                        response_text = str(response_data)
                        
                        already_checked_phrases = [
                            'Already checked in today',
                            'already checked in today',
                            'Already checked in',
                            'already checked in'
                        ]
                        
                        self.logger.debug(f"Response text: {response_text}")
                        
                        for phrase in already_checked_phrases:
                            if phrase in response_text:
                                already_checked = True
                                self.logger.debug(f"Detected already checked-in phrase: {phrase}")
                                break
                        
                        if already_checked:
                            self.logger.info(f"Account {account['name']}{account_desc} already manually checked in today")
                        else:
                            self.logger.info(f"Account {account['name']}{account_desc} check-in successful")
                        
                        self.logger.info(f"Response content: {response_data}")
                        
                    except json.JSONDecodeError:
                        self.logger.info(f"Account {account['name']}{account_desc} check-in successful")
                        self.logger.info(f"Response content: {response.text}")
                    
                    return True
                else:
                    self.logger.error(f"Account {account['name']}{account_desc} check-in failed, status: {response.status_code}")
                    self.logger.error(f"Response: {response.text}")
                    return False
                    
            except requests.exceptions.RequestException as e:
                if attempt < retry_times - 1:
                    self.logger.warning(
                        f"Account {account['name']} attempt {attempt + 1} failed: {e}, retrying in {retry_delay}s..."
                    )
                    time.sleep(retry_delay)
                    continue
                else:
                    self.logger.error(f"Account {account['name']} request failed after {retry_times} retries: {e}")
                    return False
            except Exception as e:
                self.logger.error(f"Unknown error during check-in for {account['name']}: {e}")
                return False
        
        return False
    
    def sign_in_all_accounts(self):
        """Perform check-in for all accounts"""
        if not self.accounts:
            self.logger.warning("No accounts found")
            return
        
        self.logger.info(f"Starting check-in for {len(self.accounts)} accounts")
        
        success_count = 0
        for account in self.accounts:
            if self.sign_in(account):
                success_count += 1
            
            time.sleep(random.uniform(2, 5))
        
        self.logger.info(f"Check-in complete, success: {success_count}/{len(self.accounts)}")
    
    def run_scheduler(self):
        """Run scheduler"""
        sign_in_time = self.config.get('sign_in_time', '09:00')
        
        self.logger.info("Program started, running an immediate check-in...")
        self.sign_in_all_accounts()
        
        schedule.every().day.at(sign_in_time).do(self.sign_in_all_accounts)
        
        self.logger.info(f"Scheduled daily check-in at {sign_in_time}")
        self.logger.info("Press Ctrl+C to stop the program")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)
        except KeyboardInterrupt:
            self.logger.info("Program stopped")
    
    def run_once(self):
        """Run check-in once"""
        self.sign_in_all_accounts()

def main():
    """Main function"""
    if len(sys.argv) > 1 and sys.argv[1] == '--once':
        bot = PiggyCellBot()
        bot.run_once()
    else:
        bot = PiggyCellBot()
        bot.run_scheduler()

if __name__ == "__main__":
    main()
