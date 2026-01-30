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
            genai.configure(api_key=self.google_api_key)

    def parse_file_with_ai(self, file_content, file_type='pdf', filename=''):
        if not self.google_api_key:
            return {'success': False, 'error': '未配置 GOOGLE_API_KEY'}

        try:
            # 解决 404: 移除 v1beta 等路径，直接使用模型名
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # 针对你的“资产.pdf”定制 Prompt，确保分类准确
            prompt = """
            你是一个专业的财务分析机器人。请分析上传的资产文件，提取所有数据。
            
            分类指令：
            1. liquid_assets: 提取 TNG, ASNB, 银行存款, 证券账户现金余额。
            2. illiquid_assets: 专门提取 KWSP (EPF)。
            3. stocks_my: 马股，需包含 symbol, shares, avgPrice。
            4. stocks_us: 美股，需包含 symbol, shares, avgPrice。
            5. gold: 实物黄金，提取名称和价值。

            请严格返回纯 JSON 格式：
            {
              "liquid_assets": [{"name": "资产名", "value": 0.0}],
              "illiquid_assets": [{"name": "KWSP", "value": 0.0}],
              "stocks_my": [{"symbol": "代码", "shares": 0, "avgPrice": 0.0}],
              "stocks_us": [],
              "gold": [{"name": "金饰名", "value": 0.0}],
              "cash_balance": 0.0
            }
            """

            # 构造输入（支持 PDF 和图片）
            mime_type = 'application/pdf' if file_type == 'pdf' else 'image/jpeg'
            content_part = {'mime_type': mime_type, 'data': file_content}

            response = model.generate_content([prompt, content_part])
            
            # 关键：调用下方的计算函数
            return self._process_and_calculate(response.text)

        except Exception as e:
            # 捕获 404 或其他异常并返回友好提示
            return {'success': False, 'error': f'AI解析失败: {str(e)}'}

    def _process_and_calculate(self, ai_text):
        """在这里实现类似 Excel 的自动统计功能"""
        try:
            # 提取 JSON 字符串
            json_str = re.search(r'\{.*\}', ai_text, re.DOTALL).group(0)
            data = json.loads(json_str)

            # 1. 自动计算股票总额 (shares * avgPrice)
            my_stock_val = sum(float(s.get('shares', 0)) * float(s.get('avgPrice', 0)) for s in data.get('stocks_my', []))
            us_stock_val = sum(float(s.get('shares', 0)) * float(s.get('avgPrice', 0)) for s in data.get('stocks_us', []))
            total_stocks = my_stock_val + us_stock_val

            # 2. 计算其它分类
            total_liquid = sum(float(a.get('value', 0)) for a in data.get('liquid_assets', [])) + float(data.get('cash_balance', 0))
            total_illiquid = sum(float(a.get('value', 0)) for a in data.get('illiquid_assets', []))
            total_gold = sum(float(g.get('value', 0)) for g in data.get('gold', []))

            # 3. 最终汇总 (总资产)
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
            return {'success': False, 'error': f'汇总计算异常: {str(e)}'}

    def get_financial_advice(self, db_data):
        if not self.google_api_key: return "未配置密钥"
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = f"我的资产数据: {json.dumps(db_data)}。请用中文简短分析并给一个理财建议。"
            response = model.generate_content(prompt)
            return response.text
        except: return "暂时无法生成建议。"
