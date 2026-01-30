"""
AI增强资产管理API服务器
集成AI辅助账单解析功能
"""

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
import json
import os
from dotenv import load_dotenv
import io

# 导入AI解析器
from ai_statement_parser import AIAssetStatementParser

load_dotenv()

app = Flask(__name__)
CORS(app)

# API配置
ALPHA_VANTAGE_KEY = os.getenv('ALPHA_VANTAGE_API_KEY')

# 缓存配置
CACHE_DIR = 'cache'
os.makedirs(CACHE_DIR, exist_ok=True)
CACHE_DURATION = timedelta(minutes=int(os.getenv('CACHE_DURATION_MINUTES', 15)))

# 初始化AI解析器
ai_parser = AIAssetStatementParser()

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
        
        soup = BeautifulSoup(response.text, 'html.parser')
        prices = {}
        
        # 提取金价（简化版）
        text = response.text
        gold_916_match = re.search(r'Gold\s*916.*?RM\s*([\d,]+\.?\d*)', text, re.IGNORECASE)
        
        if gold_916_match:
            price = float(gold_916_match.group(1).replace(',', ''))
            prices['gold_916'] = price
            prices['gold_916_buyback_93'] = round(price * 0.93, 2)
            prices['gold_916_buyback_95'] = round(price * 0.95, 2)
        else:
            # 使用参考价格
            prices = {
                'gold_916': 630.00,
                'gold_916_buyback_93': 585.90,
                'gold_916_buyback_95': 598.50,
                'note': '参考价格'
            }
        
        prices['timestamp'] = datetime.now().isoformat()
        prices['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        prices['source'] = 'BuySilverMalaysia.com'
        
        result = {'success': True, 'data': prices}
        save_cache('gold_price', result)
        
        return jsonify(result)
        
    except Exception as e:
        # 返回参考价格
        prices = {
            'gold_916': 630.00,
            'gold_916_buyback_93': 585.90,
            'gold_916_buyback_95': 598.50,
            'timestamp': datetime.now().isoformat(),
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'source': 'Reference Price',
            'error': str(e)
        }
        result = {'success': True, 'data': prices}
        return jsonify(result)

# ==================== AI账单解析API ====================

@app.route('/api/parse-statement-ai', methods=['POST'])
def parse_statement_ai():
    """使用AI解析账单文件"""
    try:
        # 检查是否有文件上传
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
        
        # 获取文件类型
        filename = file.filename.lower()
        if filename.endswith('.xlsx') or filename.endswith('.xls'):
            file_type = 'excel'
        elif filename.endswith('.pdf'):
            file_type = 'pdf'
        elif filename.endswith(('.jpg', '.jpeg', '.png')):
            file_type = 'image'
        else:
            return jsonify({
                'success': False,
                'error': f'不支持的文件格式: {filename}'
            }), 400
        
        # 读取文件内容
        file_content = file.read()
        
        print(f"收到文件: {filename}, 大小: {len(file_content)} bytes")
        
        # 使用AI解析
        result = ai_parser.parse_file_with_ai(
            file_content=file_content,
            file_type=file_type,
            filename=filename
        )
        
        if result.get('success'):
            # 生成报告
            report = ai_parser.generate_asset_report(result)
            result['report'] = report
            
            print(f"解析成功: {report['summary']}")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"账单解析错误: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'服务器错误: {str(e)}'
        }), 500

# ==================== 股票价格API ====================

@app.route('/api/stock-price/<symbol>', methods=['GET'])
def get_stock_price(symbol):
    """获取单只股票价格"""
    if not ALPHA_VANTAGE_KEY:
        return jsonify({
            'success': False, 
            'error': '未配置API密钥'
        }), 500
    
    exchange = request.args.get('exchange', 'US')
    cache_key = f'stock_{symbol}_{exchange}'
    
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
        data = response.json()
        
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
    
    for stock in stocks[:10]:  # 限制数量
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

# ==================== 健康检查 ====================

@app.route('/api/health', methods=['GET'])
def health_check():
    ai_status = 'configured' if (ai_parser.anthropic_api_key or 
                                 ai_parser.groq_api_key or 
                                 ai_parser.openai_api_key) else 'not_configured'
    
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'services': {
            'gold_price': 'ok',
            'stock_price': 'ok' if ALPHA_VANTAGE_KEY else 'api_key_missing',
            'ai_parser': ai_status
        },
        'ai_available': {
            'anthropic': bool(ai_parser.anthropic_api_key),
            'groq': bool(ai_parser.groq_api_key),
            'openai': bool(ai_parser.openai_api_key)
        }
    })

@app.route('/')
def index():
    return jsonify({
        'name': 'AI增强资产管理API服务器',
        'version': '3.0',
        'endpoints': {
            '/api/gold-price': 'GET - 获取916金实时价格',
            '/api/stock-price/<symbol>': 'GET - 获取股票价格',
            '/api/stock-prices': 'POST - 批量获取股票价格',
            '/api/parse-statement-ai': 'POST - AI解析账单文件',
            '/api/health': 'GET - 健康检查'
        },
        'features': {
            'ai_parsing': 'AI辅助账单解析',
            'multi_format': '支持Excel, PDF, 图片',
            'intelligent_extraction': '智能数据提取'
        }
    })

if __name__ == '__main__':
    print("=" * 70)
    print("🤖 AI增强资产管理API服务器启动中...")
    print("=" * 70)
    
    print(f"\n✅ Alpha Vantage API: {'已配置' if ALPHA_VANTAGE_KEY else '未配置'}")
    print(f"🤖 AI服务状态:")
    print(f"   - Anthropic Claude: {'✅ 已配置' if ai_parser.anthropic_api_key else '❌ 未配置'}")
    print(f"   - Groq: {'✅ 已配置' if ai_parser.groq_api_key else '❌ 未配置'}")
    print(f"   - OpenAI: {'✅ 已配置' if ai_parser.openai_api_key else '❌ 未配置'}")
    
    print("\n📡 可用端点:")
    print("  - /api/gold-price")
    print("  - /api/stock-price/<symbol>")
    print("  - /api/parse-statement-ai (NEW! AI解析)")
    print("  - /api/health")
    print("\n📖 文档: /")
    print("=" * 70)
    
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
