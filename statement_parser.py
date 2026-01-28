"""
券商月结单解析器
支持：MOOMOO、Webull、其他券商PDF/Excel对账单
"""

import pandas as pd
import re
from datetime import datetime
import PyPDF2
import io

class StatementParser:
    """券商对账单解析器"""
    
    def __init__(self):
        self.supported_brokers = ['moomoo', 'webull', 'interactive_brokers', 'generic']
    
    def parse_moomoo_statement(self, file_path):
        """
        解析MOOMOO月结单
        支持格式：PDF, Excel, CSV
        """
        try:
            file_ext = file_path.lower().split('.')[-1]
            
            if file_ext == 'pdf':
                return self._parse_moomoo_pdf(file_path)
            elif file_ext in ['xlsx', 'xls']:
                return self._parse_moomoo_excel(file_path)
            elif file_ext == 'csv':
                return self._parse_moomoo_csv(file_path)
            else:
                return {
                    'success': False,
                    'error': f'不支持的文件格式: {file_ext}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'解析失败: {str(e)}'
            }
    
    def _parse_moomoo_pdf(self, file_path):
        """解析MOOMOO PDF对账单"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text()
            
            # 提取持仓信息
            holdings = []
            
            # MOOMOO PDF通常有"持仓明细"部分
            # 正则表达式提取股票信息
            pattern = r'([A-Z]+)\s+(\d+)\s+(\d+\.?\d*)\s+(\d+\.?\d*)'
            matches = re.findall(pattern, text)
            
            for match in matches:
                symbol, quantity, avg_cost, market_value = match
                holdings.append({
                    'symbol': symbol,
                    'quantity': int(quantity),
                    'avg_cost': float(avg_cost),
                    'market_value': float(market_value),
                    'platform': 'moomoo'
                })
            
            return {
                'success': True,
                'platform': 'moomoo',
                'holdings': holdings,
                'total_value': sum(h['market_value'] for h in holdings)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'PDF解析失败: {str(e)}'
            }
    
    def _parse_moomoo_excel(self, file_path):
        """解析MOOMOO Excel对账单"""
        try:
            df = pd.read_excel(file_path)
            
            # 查找持仓数据表
            # MOOMOO Excel通常有这些列：股票代码、数量、成本价、市值等
            holdings = []
            
            for index, row in df.iterrows():
                # 跳过标题行和空行
                if pd.isna(row.get('股票代码')) and pd.isna(row.get('Symbol')):
                    continue
                
                symbol = row.get('股票代码') or row.get('Symbol') or row.get('代码')
                quantity = row.get('持仓数量') or row.get('Quantity') or row.get('数量')
                avg_cost = row.get('成本价') or row.get('Avg Cost') or row.get('平均成本')
                market_value = row.get('市值') or row.get('Market Value') or row.get('当前市值')
                
                if symbol and quantity:
                    holdings.append({
                        'symbol': str(symbol),
                        'quantity': float(quantity),
                        'avg_cost': float(avg_cost) if avg_cost else 0,
                        'market_value': float(market_value) if market_value else 0,
                        'platform': 'moomoo'
                    })
            
            return {
                'success': True,
                'platform': 'moomoo',
                'holdings': holdings,
                'total_value': sum(h['market_value'] for h in holdings)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Excel解析失败: {str(e)}'
            }
    
    def _parse_moomoo_csv(self, file_path):
        """解析MOOMOO CSV对账单"""
        try:
            df = pd.read_csv(file_path)
            
            holdings = []
            
            for index, row in df.iterrows():
                symbol = row.get('Symbol') or row.get('股票代码')
                quantity = row.get('Quantity') or row.get('数量')
                avg_cost = row.get('Avg Cost') or row.get('成本价')
                market_value = row.get('Market Value') or row.get('市值')
                
                if symbol and quantity:
                    holdings.append({
                        'symbol': str(symbol),
                        'quantity': float(quantity),
                        'avg_cost': float(avg_cost) if avg_cost else 0,
                        'market_value': float(market_value) if market_value else 0,
                        'platform': 'moomoo'
                    })
            
            return {
                'success': True,
                'platform': 'moomoo',
                'holdings': holdings,
                'total_value': sum(h['market_value'] for h in holdings)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'CSV解析失败: {str(e)}'
            }
    
    def parse_webull_statement(self, file_path):
        """
        解析Webull月结单
        方法类似MOOMOO
        """
        try:
            file_ext = file_path.lower().split('.')[-1]
            
            if file_ext in ['xlsx', 'xls']:
                df = pd.read_excel(file_path)
            elif file_ext == 'csv':
                df = pd.read_csv(file_path)
            else:
                return {
                    'success': False,
                    'error': f'不支持的文件格式: {file_ext}'
                }
            
            holdings = []
            
            for index, row in df.iterrows():
                # Webull可能使用不同的列名
                symbol = (row.get('Ticker') or row.get('Symbol') or 
                         row.get('股票代码') or row.get('代码'))
                quantity = (row.get('Quantity') or row.get('Shares') or 
                           row.get('持股') or row.get('数量'))
                avg_cost = (row.get('Average Cost') or row.get('Avg Price') or 
                           row.get('成本价'))
                market_value = (row.get('Market Value') or row.get('Total Value') or 
                               row.get('市值'))
                
                if symbol and quantity:
                    holdings.append({
                        'symbol': str(symbol),
                        'quantity': float(quantity),
                        'avg_cost': float(avg_cost) if avg_cost else 0,
                        'market_value': float(market_value) if market_value else 0,
                        'platform': 'webull'
                    })
            
            return {
                'success': True,
                'platform': 'webull',
                'holdings': holdings,
                'total_value': sum(h['market_value'] for h in holdings)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'解析失败: {str(e)}'
            }
    
    def parse_generic_statement(self, file_path, column_mapping=None):
        """
        解析通用券商对账单
        
        参数:
        - file_path: 文件路径
        - column_mapping: 列名映射，例如：
          {
              'symbol': 'Stock Symbol',
              'quantity': 'Qty',
              'avg_cost': 'Cost',
              'market_value': 'Value'
          }
        """
        try:
            file_ext = file_path.lower().split('.')[-1]
            
            if file_ext in ['xlsx', 'xls']:
                df = pd.read_excel(file_path)
            elif file_ext == 'csv':
                df = pd.read_csv(file_path)
            else:
                return {
                    'success': False,
                    'error': f'不支持的文件格式: {file_ext}'
                }
            
            if not column_mapping:
                # 尝试自动识别列名
                column_mapping = self._auto_detect_columns(df.columns)
            
            holdings = []
            
            for index, row in df.iterrows():
                try:
                    symbol = row.get(column_mapping.get('symbol'))
                    quantity = row.get(column_mapping.get('quantity'))
                    avg_cost = row.get(column_mapping.get('avg_cost'))
                    market_value = row.get(column_mapping.get('market_value'))
                    
                    if symbol and quantity:
                        holdings.append({
                            'symbol': str(symbol),
                            'quantity': float(quantity),
                            'avg_cost': float(avg_cost) if avg_cost else 0,
                            'market_value': float(market_value) if market_value else 0,
                            'platform': 'generic'
                        })
                except:
                    continue
            
            return {
                'success': True,
                'platform': 'generic',
                'holdings': holdings,
                'total_value': sum(h['market_value'] for h in holdings)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'解析失败: {str(e)}'
            }
    
    def _auto_detect_columns(self, columns):
        """自动检测列名映射"""
        mapping = {}
        
        columns_lower = [col.lower() for col in columns]
        
        # 检测股票代码列
        symbol_keywords = ['symbol', 'ticker', 'code', '代码', '股票']
        for keyword in symbol_keywords:
            for i, col in enumerate(columns_lower):
                if keyword in col:
                    mapping['symbol'] = columns[i]
                    break
            if 'symbol' in mapping:
                break
        
        # 检测数量列
        quantity_keywords = ['quantity', 'shares', 'qty', '数量', '持股']
        for keyword in quantity_keywords:
            for i, col in enumerate(columns_lower):
                if keyword in col:
                    mapping['quantity'] = columns[i]
                    break
            if 'quantity' in mapping:
                break
        
        # 检测成本价列
        cost_keywords = ['cost', 'price', 'avg', '成本', '价格']
        for keyword in cost_keywords:
            for i, col in enumerate(columns_lower):
                if keyword in col and 'market' not in col:
                    mapping['avg_cost'] = columns[i]
                    break
            if 'avg_cost' in mapping:
                break
        
        # 检测市值列
        value_keywords = ['value', 'total', 'market', '市值', '总值']
        for keyword in value_keywords:
            for i, col in enumerate(columns_lower):
                if keyword in col:
                    mapping['market_value'] = columns[i]
                    break
            if 'market_value' in mapping:
                break
        
        return mapping
    
    def merge_multiple_platforms(self, statements_data):
        """
        合并多个平台的持仓数据
        
        参数:
        - statements_data: 多个解析结果的列表
        
        返回: 合并后的持仓数据
        """
        all_holdings = []
        total_value = 0
        
        for data in statements_data:
            if data['success']:
                all_holdings.extend(data['holdings'])
                total_value += data.get('total_value', 0)
        
        # 按平台分组
        by_platform = {}
        for holding in all_holdings:
            platform = holding['platform']
            if platform not in by_platform:
                by_platform[platform] = []
            by_platform[platform].append(holding)
        
        return {
            'success': True,
            'total_holdings': len(all_holdings),
            'total_value': total_value,
            'by_platform': by_platform,
            'all_holdings': all_holdings
        }


# 使用示例
def example_usage():
    """使用示例"""
    
    parser = StatementParser()
    
    # 示例1：解析MOOMOO对账单
    print("示例1：解析MOOMOO对账单")
    moomoo_result = parser.parse_moomoo_statement('moomoo_statement.xlsx')
    if moomoo_result['success']:
        print(f"MOOMOO持仓: {len(moomoo_result['holdings'])}只股票")
        print(f"总市值: RM {moomoo_result['total_value']:,.2f}")
    
    # 示例2：解析Webull对账单
    print("\n示例2：解析Webull对账单")
    webull_result = parser.parse_webull_statement('webull_statement.csv')
    if webull_result['success']:
        print(f"Webull持仓: {len(webull_result['holdings'])}只股票")
        print(f"总市值: ${webull_result['total_value']:,.2f}")
    
    # 示例3：合并所有平台
    print("\n示例3：合并多平台数据")
    merged = parser.merge_multiple_platforms([moomoo_result, webull_result])
    if merged['success']:
        print(f"总计: {merged['total_holdings']}只股票")
        print(f"总市值: {merged['total_value']:,.2f}")
        print("\n各平台分布:")
        for platform, holdings in merged['by_platform'].items():
            print(f"  {platform}: {len(holdings)}只股票")


if __name__ == '__main__':
    print("=" * 60)
    print("券商月结单解析器")
    print("=" * 60)
    print("\n支持的券商:")
    print("  - MOOMOO (PDF, Excel, CSV)")
    print("  - Webull (Excel, CSV)")
    print("  - 其他券商 (通用格式)")
    print("\n使用方法:")
    print("  parser = StatementParser()")
    print("  result = parser.parse_moomoo_statement('statement.xlsx')")
    print("=" * 60)
