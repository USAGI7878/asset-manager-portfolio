"""
资产账单解析模块
支持多种格式的资产账单导入：Excel, CSV, PDF
"""

import pandas as pd
import re
from datetime import datetime
import pdfplumber
import io

class AssetStatementParser:
    """资产账单解析器"""
    
    def parse_file(self, file_path):
        """
        解析资产文件
        支持: Excel (.xlsx, .xls), CSV, PDF
        """
        try:
            file_ext = file_path.lower().split('.')[-1]
            
            if file_ext in ['xlsx', 'xls']:
                return self.parse_excel(file_path)
            elif file_ext == 'csv':
                return self.parse_csv(file_path)
            elif file_ext == 'pdf':
                return self.parse_pdf(file_path)
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
    
    def parse_excel(self, file_path):
        """
        解析资产Excel文件
        支持: 资产分配、股票持仓、黄金持仓
        """
        try:
            xls = pd.ExcelFile(file_path)
            result = {
                'success': True,
                'data': {
                    'liquid_assets': [],
                    'illiquid_assets': [],
                    'stocks_my': [],
                    'stocks_us': [],
                    'gold': []
                },
                'timestamp': datetime.now().isoformat()
            }
            
            # 解析各个工作表
            for sheet_name in xls.sheet_names:
                if '资产分配' in sheet_name or '资产' in sheet_name:
                    assets = self._parse_assets_sheet(file_path, sheet_name)
                    result['data']['liquid_assets'].extend(assets.get('liquid', []))
                    result['data']['illiquid_assets'].extend(assets.get('illiquid', []))
                
                elif '股票' in sheet_name or 'stock' in sheet_name.lower():
                    stocks = self._parse_stocks_sheet(file_path, sheet_name)
                    result['data']['stocks_my'].extend(stocks.get('my', []))
                    result['data']['stocks_us'].extend(stocks.get('us', []))
                
                elif '金' in sheet_name or 'gold' in sheet_name.lower():
                    gold = self._parse_gold_sheet(file_path, sheet_name)
                    result['data']['gold'].extend(gold)
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': f'解析失败: {str(e)}'
            }
    
    def _parse_assets_sheet(self, file_path, sheet_name):
        """解析资产分配表"""
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            
            liquid = []
            illiquid = []
            
            # 查找数据列
            for index, row in df.iterrows():
                # 跳过空行
                if pd.isna(row.iloc[0]):
                    continue
                
                name = str(row.iloc[0]).strip()
                value = row.iloc[1] if len(row) > 1 else 0
                
                # 尝试转换为数字
                try:
                    value = float(value)
                except:
                    continue
                
                if value <= 0:
                    continue
                
                # 判断资产类别
                category = 'cash'
                if '股票' in name or 'stock' in name.lower():
                    category = 'stocks'
                elif '金' in name or 'gold' in name.lower():
                    category = 'gold'
                elif 'ASNB' in name or '基金' in name:
                    category = 'investment'
                
                # 判断是否为不可动资产
                is_illiquid = False
                if 'KWSP' in name or 'EPF' in name or '公积金' in name:
                    is_illiquid = True
                
                asset_obj = {
                    'name': name,
                    'value': value,
                    'category': category,
                    'notes': ''
                }
                
                if is_illiquid:
                    illiquid.append(asset_obj)
                else:
                    liquid.append(asset_obj)
            
            return {'liquid': liquid, 'illiquid': illiquid}
            
        except Exception as e:
            print(f'解析资产表失败: {e}')
            return {'liquid': [], 'illiquid': []}
    
    def _parse_stocks_sheet(self, file_path, sheet_name):
        """解析股票持仓表"""
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            
            my_stocks = []
            us_stocks = []
            
            # 查找表头
            header_row = 0
            for i, row in df.iterrows():
                if any('名称' in str(cell) or '代码' in str(cell) or 'Symbol' in str(cell) 
                       for cell in row if pd.notna(cell)):
                    header_row = i
                    break
            
            # 重新读取，使用正确的表头
            df = pd.read_excel(file_path, sheet_name=sheet_name, header=header_row)
            
            for index, row in df.iterrows():
                # 跳过空行和合计行
                if pd.isna(row.iloc[0]) or '合计' in str(row.iloc[0]) or '总计' in str(row.iloc[0]):
                    continue
                
                # 提取股票信息
                symbol_name = str(row.iloc[0]).strip()
                
                # 提取代码（括号内的部分）
                symbol_match = re.search(r'\(([^)]+)\)', symbol_name)
                if symbol_match:
                    symbol = symbol_match.group(1)
                    name = symbol_name.split('(')[0].strip()
                else:
                    symbol = symbol_name
                    name = symbol_name
                
                # 提取数量和成本
                shares = 0
                avg_price = 0
                
                # 尝试从"市值/数量"列提取
                if len(row) > 1 and pd.notna(row.iloc[1]):
                    market_qty = str(row.iloc[1])
                    if '/' in market_qty:
                        parts = market_qty.split('/')
                        if len(parts) > 1:
                            try:
                                shares = float(parts[1])
                            except:
                                pass
                
                # 尝试从"现价/成本"列提取
                if len(row) > 2 and pd.notna(row.iloc[2]):
                    price_cost = str(row.iloc[2])
                    if '/' in price_cost:
                        parts = price_cost.split('/')
                        if len(parts) > 1:
                            try:
                                avg_price = float(parts[1])
                            except:
                                pass
                
                if shares <= 0 or avg_price <= 0:
                    continue
                
                # 判断是美股还是马股
                is_us = bool(re.search(r'^[A-Z]{1,5}$', symbol) and len(symbol) <= 5)
                is_my = bool(re.search(r'^\d{4}$', symbol))
                
                stock_obj = {
                    'symbol': symbol,
                    'name': name,
                    'shares': shares,
                    'avgPrice': avg_price,
                    'currentPrice': 0,
                    'exchange': 'US' if is_us else 'MY'
                }
                
                if is_us:
                    us_stocks.append(stock_obj)
                else:
                    my_stocks.append(stock_obj)
            
            return {'my': my_stocks, 'us': us_stocks}
            
        except Exception as e:
            print(f'解析股票表失败: {e}')
            return {'my': [], 'us': []}
    
    def _parse_gold_sheet(self, file_path, sheet_name):
        """解析黄金持仓表"""
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            
            gold_items = []
            
            for index, row in df.iterrows():
                # 跳过空行和合计行
                if pd.isna(row.iloc[0]) or '合计' in str(row.iloc[0]) or '总计' in str(row.iloc[0]):
                    continue
                
                name = str(row.iloc[0]).strip()
                
                # 提取重量（第2列）
                weight = 0
                if len(row) > 1 and pd.notna(row.iloc[1]):
                    try:
                        weight = float(row.iloc[1])
                    except:
                        continue
                
                # 提取买入价（第3列）
                buy_price = 0
                if len(row) > 2 and pd.notna(row.iloc[2]):
                    try:
                        # 可能是总价，需要除以重量
                        total_cost = float(row.iloc[2])
                        if weight > 0:
                            buy_price = total_cost / weight
                    except:
                        continue
                
                # 如果有成本列（第4列），使用它来计算买入价
                if len(row) > 3 and pd.notna(row.iloc[3]):
                    try:
                        total_cost = float(row.iloc[3])
                        if weight > 0:
                            buy_price = total_cost / weight
                    except:
                        pass
                
                if weight <= 0 or buy_price <= 0:
                    continue
                
                gold_obj = {
                    'name': name,
                    'weight': weight,
                    'buyPrice': buy_price,
                    'notes': ''
                }
                
                gold_items.append(gold_obj)
            
            return gold_items
            
        except Exception as e:
            print(f'解析黄金表失败: {e}')
            return []
    
    def parse_pdf(self, file_path):
        """
        解析PDF账单
        支持: MOOMOO, Webull, 通用券商账单
        """
        try:
            result = {
                'success': True,
                'data': {
                    'liquid_assets': [],
                    'illiquid_assets': [],
                    'stocks_my': [],
                    'stocks_us': [],
                    'gold': []
                },
                'timestamp': datetime.now().isoformat()
            }
            
            # 使用pdfplumber提取文本和表格
            with pdfplumber.open(file_path) as pdf:
                full_text = ""
                tables = []
                
                # 提取所有页面的文本和表格
                for page in pdf.pages:
                    full_text += page.extract_text() + "\n"
                    page_tables = page.extract_tables()
                    if page_tables:
                        tables.extend(page_tables)
                
                # 识别券商类型
                broker = self._identify_broker(full_text)
                
                # 根据券商类型解析
                if broker == 'moomoo':
                    parsed = self._parse_moomoo_pdf(full_text, tables)
                elif broker == 'webull':
                    parsed = self._parse_webull_pdf(full_text, tables)
                else:
                    # 通用解析
                    parsed = self._parse_generic_pdf(full_text, tables)
                
                result['data'] = parsed
                result['broker'] = broker
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': f'PDF解析失败: {str(e)}'
            }
    
    def parse_csv(self, file_path):
        """解析CSV文件"""
        try:
            # 尝试不同的编码
            encodings = ['utf-8', 'gbk', 'gb2312', 'latin1']
            df = None
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(file_path, encoding=encoding)
                    break
                except:
                    continue
            
            if df is None:
                return {
                    'success': False,
                    'error': '无法读取CSV文件，编码不支持'
                }
            
            # CSV通常是股票持仓数据
            result = {
                'success': True,
                'data': {
                    'liquid_assets': [],
                    'illiquid_assets': [],
                    'stocks_my': [],
                    'stocks_us': [],
                    'gold': []
                },
                'timestamp': datetime.now().isoformat()
            }
            
            # 解析股票数据
            stocks = self._parse_stocks_from_dataframe(df)
            result['data']['stocks_my'] = stocks.get('my', [])
            result['data']['stocks_us'] = stocks.get('us', [])
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': f'CSV解析失败: {str(e)}'
            }
    
    def _identify_broker(self, text):
        """识别券商类型"""
        text_lower = text.lower()
        
        if 'moomoo' in text_lower or '富途' in text:
            return 'moomoo'
        elif 'webull' in text_lower or '微牛' in text:
            return 'webull'
        elif 'interactive brokers' in text_lower or 'ibkr' in text_lower:
            return 'interactive_brokers'
        else:
            return 'generic'
    
    def _parse_moomoo_pdf(self, text, tables):
        """解析MOOMOO PDF账单"""
        data = {
            'liquid_assets': [],
            'illiquid_assets': [],
            'stocks_my': [],
            'stocks_us': [],
            'gold': []
        }
        
        # 从表格中提取股票持仓
        for table in tables:
            if not table or len(table) < 2:
                continue
            
            # 查找表头
            header = table[0]
            if not any('股票' in str(cell) or 'Symbol' in str(cell) or '代码' in str(cell) 
                      for cell in header if cell):
                continue
            
            # 解析股票数据
            for row in table[1:]:
                if not row or len(row) < 3:
                    continue
                
                try:
                    # 提取股票信息
                    symbol = str(row[0]).strip() if row[0] else ''
                    if not symbol or symbol == 'None':
                        continue
                    
                    # 提取数量和价格
                    quantity = 0
                    avg_price = 0
                    
                    for i, cell in enumerate(row):
                        if cell and str(cell).replace('.', '').replace(',', '').isdigit():
                            try:
                                val = float(str(cell).replace(',', ''))
                                if 0 < val < 10000 and quantity == 0:
                                    quantity = val
                                elif val > 0 and avg_price == 0:
                                    avg_price = val
                            except:
                                pass
                    
                    if quantity > 0 and avg_price > 0:
                        # 判断美股/马股
                        is_us = bool(re.search(r'^[A-Z]{1,5}$', symbol))
                        
                        stock_obj = {
                            'symbol': symbol,
                            'name': symbol,
                            'shares': quantity,
                            'avgPrice': avg_price,
                            'currentPrice': 0,
                            'exchange': 'US' if is_us else 'MY'
                        }
                        
                        if is_us:
                            data['stocks_us'].append(stock_obj)
                        else:
                            data['stocks_my'].append(stock_obj)
                
                except Exception as e:
                    continue
        
        # 从文本中提取账户余额
        balance_pattern = r'账户余额.*?([\d,]+\.?\d*)'
        balance_match = re.search(balance_pattern, text)
        if balance_match:
            try:
                balance = float(balance_match.group(1).replace(',', ''))
                if balance > 0:
                    data['liquid_assets'].append({
                        'name': 'MOOMOO账户余额',
                        'value': balance,
                        'category': 'cash',
                        'notes': '现金余额'
                    })
            except:
                pass
        
        return data
    
    def _parse_webull_pdf(self, text, tables):
        """解析Webull PDF账单"""
        data = {
            'liquid_assets': [],
            'illiquid_assets': [],
            'stocks_my': [],
            'stocks_us': [],
            'gold': []
        }
        
        # Webull的逻辑类似MOOMOO
        for table in tables:
            if not table or len(table) < 2:
                continue
            
            for row in table[1:]:
                if not row or len(row) < 4:
                    continue
                
                try:
                    symbol = str(row[0]).strip() if row[0] else ''
                    if not symbol:
                        continue
                    
                    quantity = float(row[1]) if row[1] and str(row[1]).replace('.', '').isdigit() else 0
                    avg_price = float(row[2]) if row[2] and str(row[2]).replace('.', '').isdigit() else 0
                    
                    if quantity > 0 and avg_price > 0:
                        is_us = bool(re.search(r'^[A-Z]{1,5}$', symbol))
                        
                        stock_obj = {
                            'symbol': symbol,
                            'name': symbol,
                            'shares': quantity,
                            'avgPrice': avg_price,
                            'currentPrice': 0,
                            'exchange': 'US' if is_us else 'MY'
                        }
                        
                        if is_us:
                            data['stocks_us'].append(stock_obj)
                        else:
                            data['stocks_my'].append(stock_obj)
                
                except:
                    continue
        
        return data
    
    def _parse_generic_pdf(self, text, tables):
        """通用PDF解析"""
        data = {
            'liquid_assets': [],
            'illiquid_assets': [],
            'stocks_my': [],
            'stocks_us': [],
            'gold': []
        }
        
        # 尝试从表格中提取股票信息
        for table in tables:
            if not table or len(table) < 2:
                continue
            
            for row in table:
                if not row or len(row) < 2:
                    continue
                
                # 查找股票代码模式
                for i, cell in enumerate(row):
                    if not cell:
                        continue
                    
                    cell_str = str(cell).strip()
                    
                    # 美股代码模式：1-5个大写字母
                    us_match = re.search(r'\b([A-Z]{1,5})\b', cell_str)
                    if us_match:
                        symbol = us_match.group(1)
                        
                        # 尝试找数量和价格
                        numbers = []
                        for c in row[i+1:]:
                            if c:
                                try:
                                    num = float(str(c).replace(',', ''))
                                    if num > 0:
                                        numbers.append(num)
                                except:
                                    pass
                        
                        if len(numbers) >= 2:
                            data['stocks_us'].append({
                                'symbol': symbol,
                                'name': symbol,
                                'shares': numbers[0],
                                'avgPrice': numbers[1],
                                'currentPrice': 0,
                                'exchange': 'US'
                            })
        
        return data
    
    def _parse_stocks_from_dataframe(self, df):
        """从DataFrame解析股票数据"""
        my_stocks = []
        us_stocks = []
        
        # 查找相关列
        symbol_col = None
        quantity_col = None
        price_col = None
        
        for col in df.columns:
            col_lower = str(col).lower()
            if 'symbol' in col_lower or '代码' in col_lower or 'ticker' in col_lower:
                symbol_col = col
            elif 'quantity' in col_lower or '数量' in col_lower or 'shares' in col_lower:
                quantity_col = col
            elif 'price' in col_lower or '价格' in col_lower or 'cost' in col_lower:
                price_col = col
        
        if not symbol_col:
            return {'my': [], 'us': []}
        
        for _, row in df.iterrows():
            try:
                symbol = str(row[symbol_col]).strip()
                if not symbol or symbol == 'nan':
                    continue
                
                quantity = float(row[quantity_col]) if quantity_col and pd.notna(row[quantity_col]) else 0
                price = float(row[price_col]) if price_col and pd.notna(row[price_col]) else 0
                
                if quantity <= 0 or price <= 0:
                    continue
                
                is_us = bool(re.search(r'^[A-Z]{1,5}$', symbol))
                
                stock_obj = {
                    'symbol': symbol,
                    'name': symbol,
                    'shares': quantity,
                    'avgPrice': price,
                    'currentPrice': 0,
                    'exchange': 'US' if is_us else 'MY'
                }
                
                if is_us:
                    us_stocks.append(stock_obj)
                else:
                    my_stocks.append(stock_obj)
            
            except:
                continue
        
        return {'my': my_stocks, 'us': us_stocks}

# 测试代码
if __name__ == '__main__':
    parser = AssetStatementParser()
    
    # 测试Excel
    print("=" * 60)
    print("测试Excel解析:")
    print("=" * 60)
    result = parser.parse_file('/mnt/user-data/uploads/资产.xlsx')
    
    if result['success']:
        print('✅ Excel解析成功！')
        print(f"\n可动资产数量: {len(result['data']['liquid_assets'])}")
        print(f"不可动资产数量: {len(result['data']['illiquid_assets'])}")
        print(f"马股数量: {len(result['data']['stocks_my'])}")
        print(f"美股数量: {len(result['data']['stocks_us'])}")
        print(f"黄金数量: {len(result['data']['gold'])}")
    else:
        print(f'❌ Excel解析失败: {result["error"]}')
