"""
完整版资产管理API服务器（精简版）
整合：股票价格、金价、静态文件服务
"""

from flask import Flask, jsonify, request, send_from_directory
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

app = Flask(__name__, static_folder='.')
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

# ========== 静态文件路由 ==========

@app.route('/')
def index():
    """提供主页HTML文件"""
    return send_from_directory('.', 'index.html')

# ========== API健康检查 ==========

@app.route('/api/health')
def health_check():
    """健康检查端点"""
    return jsonify({
        'status': 'healthy',
        'service': 'Asset Management API',
        'version': '1.0',
        'timestamp': datetime.now().isoformat(),
        'features': {
            'gold_price': True,
            'stock_price': True if ALPHA_VANTAGE_KEY else False,
            'forex_rate': True if ALPHA_VANTAGE_KEY else False
        }
    })

# ========== 金价API ==========

@app.route('/api/gold-price')
def get_gold_price():
    """获取916金价（马来西亚）"""
    
    # 检查缓存
    cache_data = load_cache('gold_price')
    if cache_data:
        return jsonify(cache_data)
    
    try:
        url = 'https://buysilvermalaysia.com/gold-price-malaysia/'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查找916金价
        gold_916 = 0
        price_rows = soup.find_all('tr')
        
        for row in price_rows:
            cells = row.find_all('td')
            if len(cells) >= 2:
                text = cells[0].get_text(strip=True)
                if '916' in text and 'Gold' in text:
                    price_text = cells[1].get_text(strip=True)
                    price_match = re.search(r'RM\s*([\d,]+\.?\d*)', price_text)
                    if price_match:
                        gold_916 = float(price_match.group(1).replace(',', ''))
                        break
        
        if gold_916 == 0:
            return jsonify({
                'success': False,
                'error': '无法获取金价数据'
            }), 500
        
        # 计算回收价
        gold_916_buyback_90 = round(gold_916 * 0.90, 2)
        gold_916_buyback_93 = round(gold_916 * 0.93, 2)
        gold_916_buyback_95 = round(gold_916 * 0.95, 2)
        
        result = {
            'success': True,
            'data': {
                'gold_916': gold_916,
                'gold_916_buyback_90': gold_916_buyback_90,
                'gold_916_buyback_93': gold_916_buyback_93,
                'gold_916_buyback_95': gold_916_buyback_95,
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'source': 'buysilvermalaysia.com'
            },
            'timestamp': datetime.now().isoformat()
        }
        
        # 保存缓存
        save_cache('gold_price', result)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ========== 股票价格API ==========

@app.route('/api/stock-price/<symbol>')
def get_stock_price(symbol):
    """获取股票实时价格"""
    
    if not ALPHA_VANTAGE_KEY:
        return jsonify({
            'success': False,
            'error': 'Alpha Vantage API密钥未配置'
        }), 500
    
    exchange = request.args.get('exchange', 'US').upper()
    
    # 检查缓存
    cache_key = f'stock_{symbol}_{exchange}'
    cache_data = load_cache(cache_key)
    if cache_data:
        return jsonify(cache_data)
    
    try:
        # 马来西亚股票需要添加.KL后缀
        api_symbol = f'{symbol}.KL' if exchange == 'MY' else symbol
        
        url = 'https://www.alphavantage.co/query'
        params = {
            'function': 'GLOBAL_QUOTE',
            'symbol': api_symbol,
            'apikey': ALPHA_VANTAGE_KEY
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if 'Global Quote' not in data or not data['Global Quote']:
            return jsonify({
                'success': False,
                'error': f'无法获取股票 {symbol} 的数据'
            }), 404
        
        quote = data['Global Quote']
        price = float(quote.get('05. price', 0))
        change = float(quote.get('09. change', 0))
        change_percent = quote.get('10. change percent', '0%').replace('%', '')
        
        result = {
            'success': True,
            'data': {
                'symbol': symbol,
                'exchange': exchange,
                'price': price,
                'change': change,
                'change_percent': float(change_percent),
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            'timestamp': datetime.now().isoformat()
        }
        
        # 保存缓存
        save_cache(cache_key, result)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ========== 批量股票价格API ==========

@app.route('/api/stock-prices', methods=['POST'])
def get_stock_prices():
    """批量获取股票价格"""
    
    if not ALPHA_VANTAGE_KEY:
        return jsonify({
            'success': False,
            'error': 'Alpha Vantage API密钥未配置'
        }), 500
    
    try:
        data = request.get_json()
        symbols = data.get('symbols', [])
        
        if not symbols:
            return jsonify({
                'success': False,
                'error': '未提供股票代码'
            }), 400
        
        results = []
        
        for item in symbols:
            symbol = item.get('symbol')
            exchange = item.get('exchange', 'US')
            
            # 检查缓存
            cache_key = f'stock_{symbol}_{exchange}'
            cache_data = load_cache(cache_key)
            
            if cache_data:
                results.append(cache_data['data'])
                continue
            
            try:
                api_symbol = f'{symbol}.KL' if exchange == 'MY' else symbol
                
                url = 'https://www.alphavantage.co/query'
                params = {
                    'function': 'GLOBAL_QUOTE',
                    'symbol': api_symbol,
                    'apikey': ALPHA_VANTAGE_KEY
                }
                
                response = requests.get(url, params=params, timeout=10)
                quote_data = response.json()
                
                if 'Global Quote' in quote_data and quote_data['Global Quote']:
                    quote = quote_data['Global Quote']
                    price = float(quote.get('05. price', 0))
                    
                    stock_data = {
                        'symbol': symbol,
                        'exchange': exchange,
                        'price': price,
                        'success': True
                    }
                    
                    # 保存缓存
                    save_cache(cache_key, {
                        'success': True,
                        'data': stock_data,
                        'timestamp': datetime.now().isoformat()
                    })
                    
                    results.append(stock_data)
                else:
                    results.append({
                        'symbol': symbol,
                        'exchange': exchange,
                        'success': False,
                        'error': '无法获取数据'
                    })
                    
            except Exception as e:
                results.append({
                    'symbol': symbol,
                    'exchange': exchange,
                    'success': False,
                    'error': str(e)
                })
        
        return jsonify({
            'success': True,
            'data': results,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ========== 账单解析API ==========

@app.route('/api/parse-statement', methods=['POST'])
def parse_statement():
    """解析资产账单"""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': '未上传文件'
            }), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': '文件名为空'
            }), 400
        
        # 检查文件类型
        allowed_extensions = {'xlsx', 'xls', 'csv', 'pdf'}
        file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        
        if file_ext not in allowed_extensions:
            return jsonify({
                'success': False,
                'error': f'不支持的文件格式: {file_ext}'
            }), 400
        
        # 保存临时文件
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_ext}') as temp_file:
            file.save(temp_file.name)
            temp_path = temp_file.name
        
        try:
            # 导入解析器
            import sys
            import os
            sys.path.insert(0, os.path.dirname(__file__))
            from statement_parser import AssetStatementParser
            
            parser = AssetStatementParser()
            result = parser.parse_file(temp_path)
            
            # 删除临时文件
            os.unlink(temp_path)
            
            return jsonify(result)
            
        except Exception as e:
            # 删除临时文件
            try:
                os.unlink(temp_path)
            except:
                pass
            
            return jsonify({
                'success': False,
                'error': f'解析失败: {str(e)}'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ========== 外汇汇率API ==========

@app.route('/api/forex-rate')
def get_forex_rate():
    """获取外汇汇率"""
    
    if not ALPHA_VANTAGE_KEY:
        return jsonify({
            'success': False,
            'error': 'Alpha Vantage API密钥未配置'
        }), 500
    
    from_currency = request.args.get('from', 'USD').upper()
    to_currency = request.args.get('to', 'MYR').upper()
    
    # 检查缓存
    cache_key = f'forex_{from_currency}_{to_currency}'
    cache_data = load_cache(cache_key)
    if cache_data:
        return jsonify(cache_data)
    
    try:
        url = 'https://www.alphavantage.co/query'
        params = {
            'function': 'CURRENCY_EXCHANGE_RATE',
            'from_currency': from_currency,
            'to_currency': to_currency,
            'apikey': ALPHA_VANTAGE_KEY
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if 'Realtime Currency Exchange Rate' not in data:
            return jsonify({
                'success': False,
                'error': '无法获取汇率数据'
            }), 500
        
        exchange_data = data['Realtime Currency Exchange Rate']
        rate = float(exchange_data.get('5. Exchange Rate', 0))
        
        result = {
            'success': True,
            'data': {
                'from': from_currency,
                'to': to_currency,
                'rate': rate,
                'last_updated': exchange_data.get('6. Last Refreshed', ''),
                'timezone': exchange_data.get('7. Time Zone', '')
            },
            'timestamp': datetime.now().isoformat()
        }
        
        # 保存缓存
        save_cache(cache_key, result)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ========== 错误处理 ==========

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': '端点不存在'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': '服务器内部错误'
    }), 500

# ========== 启动服务器 ==========

if __name__ == '__main__':
    print("=" * 70)
    print("🚀 资产管理API服务器启动中...")
    print("=" * 70)
    
    if not ALPHA_VANTAGE_KEY:
        print("\n⚠️  警告: 未配置 Alpha Vantage API 密钥")
        print("    股票和汇率功能将无法使用")
    else:
        print(f"\n✅ Alpha Vantage API 已配置")
    
    print("\n📡 可用端点:")
    print("  - /                         (主页)")
    print("  - /api/health               (健康检查)")
    print("  - /api/gold-price           (金价)")
    print("  - /api/stock-price/<symbol> (单个股票)")
    print("  - /api/stock-prices         (批量股票, POST)")
    print("  - /api/forex-rate           (外汇汇率)")
    print("  - /api/parse-statement      (解析账单, POST)")
    print("=" * 70)
    
    # 支持云端部署
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
