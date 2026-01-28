"""
BuySilverMalaysia 金价爬虫
自动获取马来西亚916金的实时回收价
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import re

def get_gold_prices():
    """
    爬取BuySilverMalaysia的实时金价
    返回：包含各种金价的字典
    """
    url = "https://www.buysilvermalaysia.com/live-price"
    
    try:
        # 设置请求头，模拟浏览器访问
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }
        
        # 发送请求
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # 解析HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查找价格信息
        prices = {}
        
        # 方法1：从文本中提取价格
        text = response.text
        
        # 提取999金价格
        gold_999_match = re.search(r'Gold 999[^\d]*(RM\s*[\d,]+\.?\d*)/gram', text)
        if gold_999_match:
            price_str = gold_999_match.group(1).replace('RM', '').replace(',', '').strip()
            prices['gold_999'] = float(price_str)
        
        # 提取916金价格
        gold_916_match = re.search(r'Gold 916[^\d]*(RM\s*[\d,]+\.?\d*)/gram', text)
        if gold_916_match:
            price_str = gold_916_match.group(1).replace('RM', '').replace(',', '').strip()
            prices['gold_916'] = float(price_str)
        
        # 提取835金价格
        gold_835_match = re.search(r'Gold 835[^\d]*(RM\s*[\d,]+\.?\d*)/gram', text)
        if gold_835_match:
            price_str = gold_835_match.group(1).replace('RM', '').replace(',', '').strip()
            prices['gold_835'] = float(price_str)
        
        # 提取750金价格
        gold_750_match = re.search(r'Gold 750[^\d]*(RM\s*[\d,]+\.?\d*)/gram', text)
        if gold_750_match:
            price_str = gold_750_match.group(1).replace('RM', '').replace(',', '').strip()
            prices['gold_750'] = float(price_str)
        
        # 提取更新时间
        time_match = re.search(r'Last Updated:\s*([^<]+)', text)
        if time_match:
            prices['last_updated'] = time_match.group(1).strip()
        else:
            prices['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 添加时间戳
        prices['timestamp'] = datetime.now().isoformat()
        
        # 计算回收价（假设回收率为93%，可调整）
        if 'gold_916' in prices:
            prices['gold_916_buyback'] = round(prices['gold_916'] * 0.93, 2)
        
        return {
            'success': True,
            'data': prices,
            'source': 'BuySilverMalaysia.com'
        }
        
    except requests.exceptions.RequestException as e:
        return {
            'success': False,
            'error': f'网络请求失败: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'解析失败: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }

def get_alternative_gold_prices():
    """
    备用方案：从导航栏提取金价
    """
    url = "https://www.buysilvermalaysia.com"
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # 从导航栏提取金价
        gold_nav_match = re.search(r'Gold:\s*RM\s*([\d,]+\.?\d*)/g', response.text)
        
        if gold_nav_match:
            gold_999_price = float(gold_nav_match.group(1).replace(',', ''))
            gold_916_price = round(gold_999_price * 0.916, 2)
            
            return {
                'success': True,
                'data': {
                    'gold_999': gold_999_price,
                    'gold_916': gold_916_price,
                    'gold_916_buyback': round(gold_916_price * 0.93, 2),
                    'timestamp': datetime.now().isoformat(),
                    'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                },
                'source': 'BuySilverMalaysia.com (navbar)'
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

if __name__ == '__main__':
    # 测试爬虫
    print("正在获取金价...")
    result = get_gold_prices()
    
    if result['success']:
        print("\n✅ 成功获取金价！")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("\n❌ 主方法失败，尝试备用方案...")
        alt_result = get_alternative_gold_prices()
        print(json.dumps(alt_result, indent=2, ensure_ascii=False))
