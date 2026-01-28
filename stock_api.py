"""
Alpha Vantage股票价格API
支持马来西亚股票和美国股票
"""

import requests
import json
from datetime import datetime
import time

class StockPriceAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co/query"
    
    def get_stock_price(self, symbol, exchange="US"):
        """
        获取股票实时价格
        
        参数:
        - symbol: 股票代码（如 'AAPL', 'TSLA', 'MAYBANK'）
        - exchange: 交易所（'US' 或 'KL' 为马来西亚）
        
        返回: {price, change, change_percent, last_updated}
        """
        try:
            # 马来西亚股票需要添加.KL后缀
            if exchange == "KL" or exchange == "KLSE":
                full_symbol = f"{symbol}.KL"
            else:
                full_symbol = symbol
            
            # 使用GLOBAL_QUOTE获取实时报价
            params = {
                'function': 'GLOBAL_QUOTE',
                'symbol': full_symbol,
                'apikey': self.api_key
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # 检查是否有错误信息
            if 'Error Message' in data:
                return {
                    'success': False,
                    'error': f'股票代码无效: {symbol}'
                }
            
            if 'Note' in data:
                return {
                    'success': False,
                    'error': 'API请求限制：每分钟最多5次，每天500次'
                }
            
            # 解析数据
            quote = data.get('Global Quote', {})
            
            if not quote:
                return {
                    'success': False,
                    'error': f'无法获取 {symbol} 的数据'
                }
            
            return {
                'success': True,
                'symbol': symbol,
                'full_symbol': full_symbol,
                'price': float(quote.get('05. price', 0)),
                'change': float(quote.get('09. change', 0)),
                'change_percent': quote.get('10. change percent', '0%').replace('%', ''),
                'volume': int(float(quote.get('06. volume', 0))),
                'last_updated': quote.get('07. latest trading day', ''),
                'timestamp': datetime.now().isoformat()
            }
            
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'网络请求失败: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'解析失败: {str(e)}'
            }
    
    def get_multiple_stocks(self, stocks_list, delay=12):
        """
        批量获取多只股票价格
        
        参数:
        - stocks_list: 股票列表 [{'symbol': 'AAPL', 'exchange': 'US'}, ...]
        - delay: 每次请求间隔秒数（免费版限制每分钟5次）
        
        返回: 股票价格列表
        """
        results = []
        
        for i, stock in enumerate(stocks_list):
            symbol = stock.get('symbol') or stock.get('code', '')
            exchange = stock.get('exchange', 'US')
            
            print(f"正在获取 {symbol} 价格... ({i+1}/{len(stocks_list)})")
            
            result = self.get_stock_price(symbol, exchange)
            results.append({
                **stock,
                **result
            })
            
            # 避免超过API限制（每分钟5次）
            if i < len(stocks_list) - 1:
                print(f"等待 {delay} 秒...")
                time.sleep(delay)
        
        return results
    
    def get_forex_rate(self, from_currency="USD", to_currency="MYR"):
        """
        获取外汇汇率
        
        参数:
        - from_currency: 源货币（默认USD）
        - to_currency: 目标货币（默认MYR）
        
        返回: 汇率
        """
        try:
            params = {
                'function': 'CURRENCY_EXCHANGE_RATE',
                'from_currency': from_currency,
                'to_currency': to_currency,
                'apikey': self.api_key
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'Realtime Currency Exchange Rate' in data:
                rate_data = data['Realtime Currency Exchange Rate']
                return {
                    'success': True,
                    'from': from_currency,
                    'to': to_currency,
                    'rate': float(rate_data.get('5. Exchange Rate', 0)),
                    'last_updated': rate_data.get('6. Last Refreshed', ''),
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'success': False,
                    'error': '无法获取汇率数据'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


def test_api():
    """测试API功能"""
    
    # 你的API Key
    API_KEY = "WEDM8Q69A7PUDJ35"
    
    api = StockPriceAPI(API_KEY)
    
    print("=" * 60)
    print("📊 Alpha Vantage 股票API测试")
    print("=" * 60)
    
    # 测试1：美国股票
    print("\n【测试1】获取美国股票价格...")
    us_stocks = [
        {'symbol': 'VOO', 'exchange': 'US'},
        {'symbol': 'TSM', 'exchange': 'US'},
        {'symbol': 'TSLA', 'exchange': 'US'}
    ]
    
    us_results = api.get_multiple_stocks(us_stocks, delay=12)
    
    for result in us_results:
        if result['success']:
            print(f"\n✅ {result['symbol']}")
            print(f"   价格: ${result['price']:.2f}")
            print(f"   涨跌: {result['change']:+.2f} ({result['change_percent']}%)")
            print(f"   更新: {result['last_updated']}")
        else:
            print(f"\n❌ {result['symbol']}: {result['error']}")
    
    # 测试2：马来西亚股票
    print("\n" + "=" * 60)
    print("【测试2】获取马来西亚股票价格...")
    
    my_stocks = [
        {'symbol': '1155', 'exchange': 'KL', 'name': 'MAYBANK'},  # Maybank
        {'symbol': 'KLCC', 'exchange': 'KL', 'name': 'KLCC'},
    ]
    
    my_results = api.get_multiple_stocks(my_stocks, delay=12)
    
    for result in my_results:
        if result['success']:
            print(f"\n✅ {result.get('name', result['symbol'])}")
            print(f"   价格: RM {result['price']:.2f}")
            print(f"   涨跌: {result['change']:+.2f} ({result['change_percent']}%)")
            print(f"   更新: {result['last_updated']}")
        else:
            print(f"\n❌ {result.get('name', result['symbol'])}: {result['error']}")
    
    # 测试3：汇率
    print("\n" + "=" * 60)
    print("【测试3】获取USD到MYR汇率...")
    
    forex = api.get_forex_rate("USD", "MYR")
    if forex['success']:
        print(f"\n✅ 1 USD = {forex['rate']:.4f} MYR")
        print(f"   更新: {forex['last_updated']}")
    else:
        print(f"\n❌ {forex['error']}")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == '__main__':
    test_api()
