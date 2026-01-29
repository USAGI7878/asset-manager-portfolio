"""
完整版资产管理API服务器（精简版）
整合：股票价格、金价
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
import json
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

app = Flask(__name__)
CORS(app)

# Alpha Vantage API配置
ALPHA_VANTAGE_KEY = os.getenv('ALPHA_VANTAGE_API_KEY')

# 缓存配置
CACHE_DIR = 'cache'
os.makedirs(CACHE_DIR, exist_ok=True)
CACHE_DURATION = timedelta(minutes=int(os.getenv('CACHE_DURATION_MINUTES', 15)))

def load_cache(cache_key):
    """加载缓存"""
    cache_file = os.path.join(CACHE_DIR, f'{cache_key}.json')
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                cache = json.load(f)
                cache_time = datetime.fromisoformat(cache['timestamp'])
                if datetime.now() - cache_time < CACHE_DURATION:
                    return cache
        except:
            pass
    return None

def save_cache(cache_key, data):
    """保存缓存"""
    cache_file = os.path.join(CACHE_DIR, f'{cache_key}.json')
    try:
        with open(cache_file, 'w') as f:
            json.dump(data, f)
    except:
        pass

# ==================== 金价API ====================

@app.route('/api/gold-price', methods=['GET'])
def get_gold_price():
    """获取916金实时价格"""
    force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
    
    if not force_refresh:
        cached = load_cache('gold_price')
        if cached:
            return jsonify(cached)
    
    try:
        url = "https://www.buysilvermalaysia.com/live-price"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # 使用BeautifulSoup解析
        soup = BeautifulSoup(response.text, 'html.parser')
        prices = {}
        
        # 尝试多种方法提取金价
        
        # 方法1: 查找包含价格的文本
        text = response.text
        
        # 更灵活的正则表达式
        patterns = {
            'gold_999': [
                r'Gold\s*999.*?RM\s*([\d,]+\.?\d*)',
                r'999.*?RM\s*([\d,]+\.?\d*)',
                r'RM\s*([\d,]+\.?\d*).*?999',
            ],
            'gold_916': [
                r'Gold\s*916.*?RM\s*([\d,]+\.?\d*)',
                r'916.*?RM\s*([\d,]+\.?\d*)',
                r'RM\s*([\d,]+\.?\d*).*?916',
            ],
        }
        
        for key, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        price_str = match.group(1).replace(',', '').strip()
                        price = float(price_str)
                        if 400 < price < 1000:  # 合理的金价范围
                            prices[key] = price
                            break
                    except:
                        continue
        
        # 方法2: 使用BeautifulSoup查找特定元素
        if not prices:
            # 查找所有包含RM的文本
            for element in soup.find_all(text=re.compile(r'RM\s*[\d,]+')):
                parent_text = element.parent.get_text()
                if '916' in parent_text:
                    match = re.search(r'RM\s*([\d,]+\.?\d*)', parent_text)
                    if match and 'gold_916' not in prices:
                        try:
                            price = float(match.group(1).replace(',', ''))
                            if 400 < price < 1000:
                                prices['gold_916'] = price
                        except:
                            pass
                
                if '999' in parent_text:
                    match = re.search(r'RM\s*([\d,]+\.?\d*)', parent_text)
                    if match and 'gold_999' not in prices:
                        try:
                            price = float(match.group(1).replace(',', ''))
                            if 400 < price < 1000:
                                prices['gold_999'] = price
                        except:
                            pass
        
        # 如果抓取成功，计算回收价
        if prices.get('gold_916'):
            prices['gold_916_buyback_93'] = round(prices['gold_916'] * 0.93, 2)
            prices['gold_916_buyback_95'] = round(prices['gold_916'] * 0.95, 2)
            prices['gold_916_buyback_90'] = round(prices['gold_916'] * 0.90, 2)
        
        # 如果完全没有抓取到，使用参考价格
        if not prices:
            print("警告: 未能从网页提取金价，使用参考价格")
            prices = {
                'gold_916': 630.00,
                'gold_916_buyback_93': 585.90,
                'gold_916_buyback_95': 598.50,
                'gold_916_buyback_90': 567.00,
                'gold_999': 680.00,
                'note': '实时抓取失败，显示参考价格'
            }
        
        prices['timestamp'] = datetime.now().isoformat()
        prices['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        prices['source'] = 'BuySilverMalaysia.com'
        
        result = {'success': True, 'data': prices}
        save_cache('gold_price', result)
        
        return jsonify(result)
        
    except Exception as e:
        print(f"金价API错误: {str(e)}")
        # 尝试返回缓存
        cached = load_cache('gold_price')
        if cached:
            cached['warning'] = '无法获取最新价格，返回缓存数据'
            return jsonify(cached), 200
        
        # 如果没有缓存，返回参考价格
        prices = {
            'gold_916': 630.00,
            'gold_916_buyback_93': 585.90,
            'gold_916_buyback_95': 598.50,
            'gold_916_buyback_90': 567.00,
            'gold_999': 680.00,
            'timestamp': datetime.now().isoformat(),
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'source': 'Reference Price',
            'note': f'网络错误: {str(e)}'
        }
        result = {'success': True, 'data': prices}
        return jsonify(result)

# ==================== 股票价格API ====================

@app.route('/api/stock-price/<symbol>', methods=['GET'])
def get_stock_price(symbol):
    """获取单只股票价格"""
    if not ALPHA_VANTAGE_KEY:
        return jsonify({
            'success': False, 
            'error': '未配置API密钥，请设置 ALPHA_VANTAGE_API_KEY 环境变量'
        }), 500
    
    exchange = request.args.get('exchange', 'US')
    force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
    
    cache_key = f'stock_{symbol}_{exchange}'
    
    if not force_refresh:
        cached = load_cache(cache_key)
        if cached:
            return jsonify(cached)
    
    try:
        full_symbol = f"{symbol}.KL" if exchange in ['KL', 'KLSE'] else symbol
        
        params = {
            'function': 'GLOBAL_QUOTE',
            'symbol': full_symbol,
            'apikey': ALPHA_VANTAGE_KEY
        }
        
        response = requests.get('https://www.alphavantage.co/query', params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if 'Error Message' in data:
            return jsonify({'success': False, 'error': '股票代码无效'}), 400
        
        if 'Note' in data:
            return jsonify({'success': False, 'error': 'API请求限制'}), 429
        
        quote = data.get('Global Quote', {})
        
        if not quote:
            return jsonify({'success': False, 'error': '无法获取数据'}), 404
        
        result = {
            'success': True,
            'symbol': symbol,
            'exchange': exchange,
            'price': float(quote.get('05. price', 0)),
            'change': float(quote.get('09. change', 0)),
            'change_percent': quote.get('10. change percent', '0%').replace('%', ''),
            'volume': int(float(quote.get('06. volume', 0))),
            'last_updated': quote.get('07. latest trading day', ''),
            'timestamp': datetime.now().isoformat()
        }
        
        save_cache(cache_key, result)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stock-prices', methods=['POST'])
def get_multiple_stock_prices():
    """批量获取股票价格"""
    data = request.get_json()
    stocks = data.get('stocks', [])
    
    if not stocks:
        return jsonify({'success': False, 'error': '未提供股票列表'}), 400
    
    results = []
    
    for stock in stocks[:5]:
        symbol = stock.get('symbol') or stock.get('code')
        exchange = stock.get('exchange', 'US')
        
        cache_key = f'stock_{symbol}_{exchange}'
        cached = load_cache(cache_key)
        
        if cached and cached.get('success'):
            results.append(cached)
    
    return jsonify({
        'success': True,
        'results': results,
        'total': len(results)
    })

@app.route('/api/forex-rate', methods=['GET'])
def get_forex_rate():
    """获取外汇汇率"""
    if not ALPHA_VANTAGE_KEY:
        return jsonify({
            'success': False,
            'error': '未配置API密钥'
        }), 500
    
    from_currency = request.args.get('from', 'USD')
    to_currency = request.args.get('to', 'MYR')
    
    cache_key = f'forex_{from_currency}_{to_currency}'
    cached = load_cache(cache_key)
    
    if cached:
        return jsonify(cached)
    
    try:
        params = {
            'function': 'CURRENCY_EXCHANGE_RATE',
            'from_currency': from_currency,
            'to_currency': to_currency,
            'apikey': ALPHA_VANTAGE_KEY
        }
        
        response = requests.get('https://www.alphavantage.co/query', params=params, timeout=10)
        data = response.json()
        
        if 'Realtime Currency Exchange Rate' in data:
            rate_data = data['Realtime Currency Exchange Rate']
            result = {
                'success': True,
                'from': from_currency,
                'to': to_currency,
                'rate': float(rate_data.get('5. Exchange Rate', 0)),
                'last_updated': rate_data.get('6. Last Refreshed', ''),
                'timestamp': datetime.now().isoformat()
            }
            save_cache(cache_key, result)
            return jsonify(result)
        
        return jsonify({'success': False, 'error': '无法获取汇率'}), 500
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== 健康检查 ====================

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'services': {
            'gold_price': 'ok',
            'stock_price': 'ok' if ALPHA_VANTAGE_KEY else 'api_key_missing'
        },
        'api_configured': bool(ALPHA_VANTAGE_KEY)
    })

@app.route('/')
def index():
    return jsonify({
        'name': '资产管理API服务器',
        'version': '2.0',
        'endpoints': {
            '/api/gold-price': 'GET - 获取916金实时价格',
            '/api/stock-price/<symbol>': 'GET - 获取股票价格',
            '/api/stock-prices': 'POST - 批量获取股票价格',
            '/api/forex-rate': 'GET - 获取外汇汇率',
            '/api/health': 'GET - 健康检查'
        },
        'api_configured': bool(ALPHA_VANTAGE_KEY)
    })

if __name__ == '__main__':
    print("=" * 70)
    print("🚀 资产管理API服务器启动中...")
    print("=" * 70)
    
    if not ALPHA_VANTAGE_KEY:
        print("\n⚠️  警告: 未配置 Alpha Vantage API 密钥")
    else:
        print(f"\n✅ Alpha Vantage API 已配置")
    
    print("\n📡 可用端点:")
    print("  - /api/gold-price")
    print("  - /api/stock-price/<symbol>")
    print("  - /api/stock-prices (POST)")
    print("  - /api/forex-rate")
    print("  - /api/health")
    print("\n📖 文档: /")
    print("=" * 70)
    
    # 支持云端部署
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
