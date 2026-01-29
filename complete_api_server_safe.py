"""
完整版资产管理API服务器（安全版本）
整合：股票价格、金价、月结单解析
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
import json
import os
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

app = Flask(__name__)
CORS(app)

# 配置 - 从环境变量读取
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'xlsx', 'xls', 'csv'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Alpha Vantage API配置 - 从环境变量读取
ALPHA_VANTAGE_KEY = os.getenv('ALPHA_VANTAGE_API_KEY')

if not ALPHA_VANTAGE_KEY:
    print("⚠️  警告: 未找到 ALPHA_VANTAGE_API_KEY 环境变量")
    print("   请创建 .env 文件并添加你的API密钥")
    print("   示例: ALPHA_VANTAGE_API_KEY=your_key_here")

# 缓存配置
CACHE_DIR = 'cache'
os.makedirs(CACHE_DIR, exist_ok=True)
CACHE_DURATION = timedelta(minutes=int(os.getenv('CACHE_DURATION_MINUTES', 15)))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        text = response.text
        prices = {}
        
        patterns = {
            'gold_999': r'Gold 999[^\d]*(RM\s*[\d,]+\.?\d*)/gram',
            'gold_916': r'Gold 916[^\d]*(RM\s*[\d,]+\.?\d*)/gram',
            'gold_835': r'Gold 835[^\d]*(RM\s*[\d,]+\.?\d*)/gram',
            'gold_750': r'Gold 750[^\d]*(RM\s*[\d,]+\.?\d*)/gram',
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, text)
            if match:
                price_str = match.group(1).replace('RM', '').replace(',', '').strip()
                prices[key] = float(price_str)
        
        if 'gold_916' in prices:
            prices['gold_916_buyback_93'] = round(prices['gold_916'] * 0.93, 2)
            prices['gold_916_buyback_95'] = round(prices['gold_916'] * 0.95, 2)
            prices['gold_916_buyback_90'] = round(prices['gold_916'] * 0.90, 2)
        
        prices['timestamp'] = datetime.now().isoformat()
        prices['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        prices['source'] = 'BuySilverMalaysia.com'
        
        result = {'success': True, 'data': prices}
        save_cache('gold_price', result)
        
        return jsonify(result)
        
    except Exception as e:
        cached = load_cache('gold_price')
        if cached:
            cached['warning'] = '无法获取最新价格，返回缓存数据'
            return jsonify(cached), 200
        return jsonify({'success': False, 'error': str(e)}), 500

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
        else:
            try:
                result = get_stock_price(symbol)
                results.append(result.get_json())
            except:
                results.append({
                    'success': False,
                    'symbol': symbol,
                    'error': '获取失败'
                })
    
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

# ==================== 月结单解析API ====================

@app.route('/api/parse-statement', methods=['POST'])
def parse_statement():
    """解析券商月结单"""
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': '未上传文件'}), 400
    
    file = request.files['file']
    platform = request.form.get('platform', 'generic')
    
    if file.filename == '':
        return jsonify({'success': False, 'error': '未选择文件'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'error': '不支持的文件格式'}), 400
    
    try:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        file_ext = filename.rsplit('.', 1)[1].lower()
        
        if file_ext in ['xlsx', 'xls']:
            df = pd.read_excel(filepath)
        elif file_ext == 'csv':
            df = pd.read_csv(filepath)
        else:
            return jsonify({'success': False, 'error': 'PDF解析暂不支持'}), 400
        
        holdings = []
        
        for index, row in df.iterrows():
            symbol = None
            quantity = None
            avg_cost = None
            market_value = None
            
            for col in df.columns:
                col_lower = str(col).lower()
                if any(k in col_lower for k in ['symbol', 'ticker', 'code', '代码', '股票']):
                    symbol = row[col]
                    break
            
            for col in df.columns:
                col_lower = str(col).lower()
                if any(k in col_lower for k in ['quantity', 'shares', 'qty', '数量', '持股']):
                    try:
                        quantity = float(row[col])
                        break
                    except:
                        pass
            
            for col in df.columns:
                col_lower = str(col).lower()
                if any(k in col_lower for k in ['cost', 'price', 'avg', '成本', '价格']):
                    try:
                        avg_cost = float(row[col])
                        break
                    except:
                        pass
            
            for col in df.columns:
                col_lower = str(col).lower()
                if any(k in col_lower for k in ['value', 'total', 'market', '市值']):
                    try:
                        market_value = float(row[col])
                        break
                    except:
                        pass
            
            if symbol and quantity:
                holdings.append({
                    'symbol': str(symbol),
                    'quantity': quantity,
                    'avg_cost': avg_cost or 0,
                    'market_value': market_value or 0,
                    'platform': platform
                })
        
        # 删除上传的文件（保护隐私）
        os.remove(filepath)
        
        return jsonify({
            'success': True,
            'platform': platform,
            'holdings': holdings,
            'total_holdings': len(holdings),
            'total_value': sum(h['market_value'] for h in holdings)
        })
        
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
            'stock_price': 'ok' if ALPHA_VANTAGE_KEY else 'api_key_missing',
            'statement_parser': 'ok'
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
            '/api/parse-statement': 'POST - 解析券商月结单',
            '/api/health': 'GET - 健康检查'
        },
        'api_configured': bool(ALPHA_VANTAGE_KEY),
        'cache_duration': f'{CACHE_DURATION.seconds // 60}分钟'
    })

if __name__ == '__main__':
    print("=" * 70)
    print("🚀 资产管理API服务器启动中...")
    print("=" * 70)
    
    if not ALPHA_VANTAGE_KEY:
        print("\n⚠️  警告: 未配置 Alpha Vantage API 密钥")
        print("   请创建 .env 文件并添加: ALPHA_VANTAGE_API_KEY=your_key")
    else:
        print(f"\n✅ Alpha Vantage API 已配置: {ALPHA_VANTAGE_KEY[:8]}...")
    
    print("\n📡 可用端点:")
    print("  - http://localhost:5000/api/gold-price")
    print("  - http://localhost:5000/api/stock-price/AAPL")
    print("  - http://localhost:5000/api/stock-prices (POST)")
    print("  - http://localhost:5000/api/forex-rate?from=USD&to=MYR")
    print("  - http://localhost:5000/api/parse-statement (POST)")
    print("\n📖 文档: http://localhost:5000")
    print("=" * 70)
    
    host = os.getenv('API_HOST', 'localhost')
    port = int(os.getenv('API_PORT', 5000))
    
    app.run(debug=True, host=host, port=port)
