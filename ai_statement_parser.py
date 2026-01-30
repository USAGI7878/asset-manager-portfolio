import re
import io
import json
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

class AIAssetStatementParser:
    def __init__(self):
        self.google_api_key = os.getenv('GOOGLE_API_KEY', '')
        if self.google_api_key:
            # 初始化 Google AI
            genai.configure(api_key=self.google_api_key)

    def parse_file_with_ai(self, file_content, file_type='pdf', filename=''):
        if not self.google_api_key:
            return {'success': False, 'error': '未配置 GOOGLE_API_KEY'}

        try:
            # 修复 404：使用最稳定的模型标识符
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # 专门针对你的 PDF 格式设计的 Prompt
            prompt = """
            你是一个专业的财务机器人。请分析上传的资产文件，提取所有资产并归类。
            
            提取规则：
            1. liquid_assets (可动资产): 提取 TNG, ASNB, 银行存款, 股票现金余额。
            2. illiquid_assets (不可动资产): 专门提取 KWSP (EPF)。
            3. stocks_my: 马股 (4位代码)。
            4. stocks_us: 美股 (字母代码)。
            5. gold: 提取实物黄金价值。

            必须返回纯 JSON，格式如下：
            {
              "liquid_assets": [{"name": "TNG", "value": 51.83}],
              "illiquid_assets": [{"name": "KWSP", "value": 25411.71}],
              "stocks_my": [{"symbol": "1155", "shares": 100, "avgPrice": 9.5}],
              "stocks_us": [],
              "gold": [{"name": "实体黄金", "value": 17524.88}],
              "cash_balance": 0
            }
            不要输出任何额外文字。
            """

            # 构造输入
            mime_type = 'application/pdf' if file_type == 'pdf' else 'image/jpeg'
            content_part = {'mime_type': mime_type, 'data': file_content}

            # 生成内容
            response = model.generate_content([prompt, content_part])
            return self._process_and_calculate(response.text)

        except Exception as e:
            return {'success': False, 'error': f'Gemini解析失败: {str(e)}'}

    def _process_and_calculate(self, ai_text):
        """核心：自动计算总额，实现类似 Excel 的效果"""
        try:
            # 清洗数据
            json_str = re.search(r'\{.*\}', ai_text, re.DOTALL).group(0)
            data = json.loads(json_str)

            # 1. 计算股票总价值 (股数 * 成本)
            my_stock_val = sum(float(s.get('shares', 0)) * float(s.get('avgPrice', 0)) for s in data.get('stocks_my', []))
            us_stock_val = sum(float(s.get('shares', 0)) * float(s.get('avgPrice', 0)) for s in data.get('stocks_us', []))
            total_stocks = my_stock_val + us_stock_val

            # 2. 计算其它总额
            total_liquid = sum(float(a.get('value', 0)) for a in data.get('liquid_assets', [])) + float(data.get('cash_balance', 0))
            total_illiquid = sum(float(a.get('value', 0)) for a in data.get('illiquid_assets', []))
            total_gold = sum(float(g.get('value', 0)) for g in data.get('gold', []))

            # 3. 总计
            grand_total = total_stocks + total_liquid + total_illiquid + total_gold

            return {
                'success': True,
                'data': data,
                'summary': {
                    'total_stocks': round(total_stocks, 2),
                    'total_liquid': round(total_liquid, 2),
                    'total_illiquid': round(total_illiquid, 2),
                    'total_gold': round(total_gold, 2),
                    'grand_total': round(grand_total, 2)
                }
            }
        except Exception as e:
            return {'success': False, 'error': f'统计异常: {str(e)}'}

    def get_financial_advice(self, db_data):
        if not self.google_api_key: return "未配置密钥"
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = f"我的资产数据: {json.dumps(db_data)}。请用中文分析并给理财建议。"
            response = model.generate_content(prompt)
            return response.text
        except: return "建议生成失败。"
