"""
AI增强资产账单解析模块
使用AI辅助提取和分析账单数据
"""

import pandas as pd
import re
from datetime import datetime
import io
import json
import requests
import os
from dotenv import load_dotenv

load_dotenv()

class AIAssetStatementParser:
    """AI增强资产账单解析器"""
    
    def __init__(self):
        # 支持多种AI API
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY', '')
        self.groq_api_key = os.getenv('GROQ_API_KEY', '')
        self.openai_api_key = os.getenv('OPENAI_API_KEY', '')
        
    def parse_file_with_ai(self, file_content, file_type='pdf', filename=''):
        """
        使用AI解析资产文件
        支持: Excel (.xlsx), PDF, 图片
        """
        try:
            print(f"开始AI解析: {filename} (类型: {file_type})")
            
            if file_type in ['xlsx', 'xls', 'excel']:
                return self._parse_excel_with_ai(file_content)
            elif file_type == 'pdf':
                return self._parse_pdf_with_ai(file_content)
            elif file_type in ['jpg', 'jpeg', 'png', 'image']:
                return self._parse_image_with_ai(file_content)
            else:
                return {
                    'success': False,
                    'error': f'不支持的文件格式: {file_type}'
                }
                
        except Exception as e:
            print(f"AI解析错误: {str(e)}")
            return {
                'success': False,
                'error': f'AI解析失败: {str(e)}'
            }
    
    def _parse_excel_with_ai(self, file_content):
        """使用AI解析Excel文件"""
        try:
            # 读取Excel
            xls = pd.ExcelFile(io.BytesIO(file_content))
            
            # 提取所有sheet的文本内容
            all_text = []
            for sheet_name in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet_name)
                all_text.append(f"=== Sheet: {sheet_name} ===")
                all_text.append(df.to_string(index=False))
            
            excel_text = "\n\n".join(all_text)
            
            # 使用AI分析
            return self._analyze_with_ai(excel_text, file_type='excel')
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Excel解析失败: {str(e)}'
            }
    
    def _parse_pdf_with_ai(self, file_content):
        """使用AI解析PDF文件"""
        try:
            # 尝试使用pdfplumber提取文本
            try:
                import pdfplumber
                pdf_text = ""
                with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                    for page in pdf.pages:
                        pdf_text += page.extract_text() or ""
                        pdf_text += "\n\n"
            except:
                # 如果pdfplumber不可用，返回错误
                return {
                    'success': False,
                    'error': 'PDF解析库未安装，请安装pdfplumber'
                }
            
            if not pdf_text.strip():
                return {
                    'success': False,
                    'error': 'PDF中未找到文本内容'
                }
            
            # 使用AI分析
            return self._analyze_with_ai(pdf_text, file_type='pdf')
            
        except Exception as e:
            return {
                'success': False,
                'error': f'PDF解析失败: {str(e)}'
            }
    
    def _parse_image_with_ai(self, file_content):
        """使用AI解析图片账单"""
        # TODO: 实现图片OCR + AI分析
        return {
            'success': False,
            'error': '图片解析功能开发中'
        }
    
    def _analyze_with_ai(self, text_content, file_type='unknown'):
        """使用AI分析文本内容"""
        
        # 构建提示词
        prompt = self._build_analysis_prompt(text_content, file_type)
        
        # 尝试不同的AI服务
        if self.anthropic_api_key:
            result = self._call_anthropic_api(prompt)
            if result:
                return result
        
        if self.groq_api_key:
            result = self._call_groq_api(prompt)
            if result:
                return result
        
        if self.openai_api_key:
            result = self._call_openai_api(prompt)
            if result:
                return result
        
        # 如果没有配置AI API，使用传统解析
        return self._fallback_parse(text_content)
    
    def _build_analysis_prompt(self, text_content, file_type):
        """构建AI分析提示词"""
        return f"""你是一个专业的资产账单分析AI助手。请从以下{file_type}文本中提取资产信息。

文本内容:
{text_content[:4000]}  # 限制长度避免超出token限制

请提取以下信息并以JSON格式返回:

1. **可动资产** (liquid_assets): 现金、股票、基金、黄金等
2. **不可动资产** (illiquid_assets): 公积金(EPF/KWSP)、退休金等
3. **股票持仓** (stocks): 包括股票代码、数量、成本价
4. **账户余额** (cash_balance): 现金余额

返回格式:
{{
  "liquid_assets": [
    {{"name": "资产名称", "value": 金额数字, "category": "cash/stocks/gold/investment"}}
  ],
  "illiquid_assets": [
    {{"name": "资产名称", "value": 金额数字, "category": "retirement/pension"}}
  ],
  "stocks_my": [
    {{"symbol": "股票代码", "name": "公司名", "shares": 数量, "avgPrice": 平均成本}}
  ],
  "stocks_us": [
    {{"symbol": "股票代码", "name": "公司名", "shares": 数量, "avgPrice": 平均成本}}
  ],
  "gold": [
    {{"type": "916金", "weight": 重量克数, "purchasePrice": 购买价格}}
  ],
  "cash_balance": 现金余额数字,
  "total_assets": 总资产数字
}}

注意:
- 股票代码识别: 马股是4位数字(如1155), 美股是1-5个大写字母(如AAPL)
- 数字提取: 只提取纯数字,去掉货币符号和逗号
- 如果某类资产不存在,返回空数组[]
- 确保所有数字都是数值类型,不是字符串

只返回JSON,不要其他解释文字。"""
    
    def _call_anthropic_api(self, prompt):
        """调用Anthropic Claude API"""
        try:
            response = requests.post(
                'https://api.anthropic.com/v1/messages',
                headers={
                    'x-api-key': self.anthropic_api_key,
                    'anthropic-version': '2023-06-01',
                    'content-type': 'application/json'
                },
                json={
                    'model': 'claude-3-5-sonnet-20241022',
                    'max_tokens': 2000,
                    'messages': [
                        {'role': 'user', 'content': prompt}
                    ]
                },
                timeout=30
            )
            
            if response.status_code == 200:
                content = response.json()['content'][0]['text']
                return self._parse_ai_response(content)
            else:
                print(f"Anthropic API错误: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Anthropic API调用失败: {str(e)}")
            return None
    
    def _call_groq_api(self, prompt):
        """调用Groq API"""
        try:
            response = requests.post(
                'https://api.groq.com/openai/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {self.groq_api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': 'llama-3.3-70b-versatile',
                    'messages': [
                        {'role': 'user', 'content': prompt}
                    ],
                    'temperature': 0.1,
                    'max_tokens': 2000
                },
                timeout=30
            )
            
            if response.status_code == 200:
                content = response.json()['choices'][0]['message']['content']
                return self._parse_ai_response(content)
            else:
                print(f"Groq API错误: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Groq API调用失败: {str(e)}")
            return None
    
    def _call_openai_api(self, prompt):
        """调用OpenAI API"""
        try:
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {self.openai_api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': 'gpt-4o-mini',
                    'messages': [
                        {'role': 'user', 'content': prompt}
                    ],
                    'temperature': 0.1,
                    'max_tokens': 2000
                },
                timeout=30
            )
            
            if response.status_code == 200:
                content = response.json()['choices'][0]['message']['content']
                return self._parse_ai_response(content)
            else:
                print(f"OpenAI API错误: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"OpenAI API调用失败: {str(e)}")
            return None
    
    def _parse_ai_response(self, ai_response):
        """解析AI返回的JSON数据"""
        try:
            # 提取JSON部分（可能被markdown包裹）
            json_match = re.search(r'```json\s*(.*?)\s*```', ai_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 尝试直接找JSON对象
                json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    json_str = ai_response
            
            # 解析JSON
            data = json.loads(json_str)
            
            # 验证和标准化数据
            result = {
                'success': True,
                'data': {
                    'liquid_assets': data.get('liquid_assets', []),
                    'illiquid_assets': data.get('illiquid_assets', []),
                    'stocks_my': data.get('stocks_my', []),
                    'stocks_us': data.get('stocks_us', []),
                    'gold': data.get('gold', []),
                    'cash_balance': data.get('cash_balance', 0),
                    'total_assets': data.get('total_assets', 0)
                },
                'ai_analysis': {
                    'raw_response': ai_response[:500],  # 保留部分原始响应用于调试
                    'extraction_method': 'AI'
                },
                'timestamp': datetime.now().isoformat()
            }
            
            print("AI解析成功!")
            return result
            
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {str(e)}")
            print(f"AI响应: {ai_response[:200]}")
            return {
                'success': False,
                'error': f'AI返回的数据格式错误: {str(e)}',
                'raw_response': ai_response[:500]
            }
        except Exception as e:
            print(f"解析AI响应失败: {str(e)}")
            return {
                'success': False,
                'error': f'处理AI响应时出错: {str(e)}'
            }
    
    def _fallback_parse(self, text_content):
        """传统解析方法（当AI不可用时）"""
        print("使用传统解析方法...")
        
        data = {
            'liquid_assets': [],
            'illiquid_assets': [],
            'stocks_my': [],
            'stocks_us': [],
            'gold': [],
            'cash_balance': 0
        }
        
        # 简单的正则提取
        # 提取马股 (4位数字)
        my_stocks = re.findall(r'\b(\d{4})\b.*?(\d+).*?([\d,.]+)', text_content)
        for symbol, shares, price in my_stocks:
            try:
                data['stocks_my'].append({
                    'symbol': symbol,
                    'name': symbol,
                    'shares': float(shares),
                    'avgPrice': float(price.replace(',', '')),
                    'currentPrice': 0,
                    'exchange': 'MY'
                })
            except:
                continue
        
        # 提取美股 (大写字母)
        us_stocks = re.findall(r'\b([A-Z]{2,5})\b.*?(\d+).*?([\d,.]+)', text_content)
        for symbol, shares, price in us_stocks[:10]:  # 限制数量避免误匹配
            try:
                data['stocks_us'].append({
                    'symbol': symbol,
                    'name': symbol,
                    'shares': float(shares),
                    'avgPrice': float(price.replace(',', '')),
                    'currentPrice': 0,
                    'exchange': 'US'
                })
            except:
                continue
        
        # 提取账户余额
        balance_patterns = [
            r'余额.*?([\d,]+\.?\d*)',
            r'Balance.*?([\d,]+\.?\d*)',
            r'现金.*?([\d,]+\.?\d*)',
            r'Cash.*?([\d,]+\.?\d*)'
        ]
        
        for pattern in balance_patterns:
            match = re.search(pattern, text_content)
            if match:
                try:
                    data['cash_balance'] = float(match.group(1).replace(',', ''))
                    break
                except:
                    continue
        
        return {
            'success': True,
            'data': data,
            'ai_analysis': {
                'extraction_method': 'Traditional Regex',
                'note': 'AI不可用，使用传统解析'
            },
            'timestamp': datetime.now().isoformat()
        }
    
    def generate_asset_report(self, parsed_data):
        """生成AI资产分析报告"""
        if not parsed_data.get('success'):
            return None
        
        data = parsed_data['data']
        
        # 计算总资产
        total_liquid = sum(asset.get('value', 0) for asset in data.get('liquid_assets', []))
        total_illiquid = sum(asset.get('value', 0) for asset in data.get('illiquid_assets', []))
        total_stocks_my = sum(stock.get('shares', 0) * stock.get('avgPrice', 0) 
                             for stock in data.get('stocks_my', []))
        total_stocks_us = sum(stock.get('shares', 0) * stock.get('avgPrice', 0) 
                             for stock in data.get('stocks_us', []))
        
        total_assets = total_liquid + total_illiquid + total_stocks_my + total_stocks_us
        
        report = {
            'summary': {
                'total_assets': round(total_assets, 2),
                'liquid_assets': round(total_liquid, 2),
                'illiquid_assets': round(total_illiquid, 2),
                'stock_holdings_my': round(total_stocks_my, 2),
                'stock_holdings_us': round(total_stocks_us, 2),
                'cash_balance': data.get('cash_balance', 0)
            },
            'breakdown': {
                'liquid_count': len(data.get('liquid_assets', [])),
                'illiquid_count': len(data.get('illiquid_assets', [])),
                'stocks_my_count': len(data.get('stocks_my', [])),
                'stocks_us_count': len(data.get('stocks_us', []))
            },
            'timestamp': datetime.now().isoformat()
        }
        
        return report

# 测试代码
if __name__ == '__main__':
    parser = AIAssetStatementParser()
    print("AI资产解析器已初始化")
    print(f"Anthropic API: {'✅' if parser.anthropic_api_key else '❌'}")
    print(f"Groq API: {'✅' if parser.groq_api_key else '❌'}")
    print(f"OpenAI API: {'✅' if parser.openai_api_key else '❌'}")
