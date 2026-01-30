import re
import io
import json
import os
import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

class AIAssetStatementParser:
    def __init__(self):
        self.google_api_key = os.getenv('GOOGLE_API_KEY', '')
        if self.google_api_key:
            genai.configure(api_key=self.google_api_key)

    def parse_file_with_ai(self, file_content, file_type='pdf', filename=''):
        """使用 Gemini 1.5 Flash 同时处理 PDF 和图片"""
        if not self.google_api_key:
            return {'success': False, 'error': '未配置 GOOGLE_API_KEY'}

        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # 针对你的资产 PDF 优化的提示词
            prompt = """
            你是一个专业的财务审计机器人。请分析上传的文件，提取所有资产信息。
            
            分类规则（参考用户本地格式）：
            1. 可动资产 (liquid_assets): 包含 TNG, ASNB, 现金, 银行存款, 股票现金账户(RKT/MOOMOO可用余额)等。
            2. 不可动资产 (illiquid_assets): 专门识别 KWSP (EPF) 或 锁定期资产。
            3. 股票 (stocks): 区分 symbol, shares, avgPrice。
            4. 黄金 (gold): 识别实物黄金名称和对应的价值。

            返回 JSON 格式必须严格如下：
            {
              "liquid_assets": [{"name": "TNG", "value": 51.83}],
              "illiquid_assets": [{"name": "KWSP", "value": 25411.71}],
              "stocks_my": [{"symbol": "MAYBANK", "shares": 100, "avgPrice": 9.5}],
              "stocks_us": [],
              "gold": [{"name": "实体黄金", "value": 17524.88}],
              "cash_balance": 0
            }
            """

            # 构造内容
            mime_type = 'application/pdf' if file_type == 'pdf' else 'image/jpeg'
            content_part = {'mime_type': mime_type, 'data': file_content}

            response = model.generate_content([prompt, content_part])
            return self._process_and_calculate(response.text)

        except Exception as e:
            return {'success': False, 'error': f'Gemini解析失败: {str(e)}'}

    def _process_and_calculate(self, ai_text):
        """核心：自动计算各分类总和"""
        try:
            # 清洗 AI 可能带有的 Markdown 标签
            json_str = re.search(r'\{.*\}', ai_text, re.DOTALL).group(0)
            data = json.loads(json_str)

            # 1. 计算股票总额 (股数 * 成本价)
            my_stock_val = sum(float(s.get('shares', 0)) * float(s.get('avgPrice', 0)) for s in data.get('stocks_my', []))
            us_stock_val = sum(float(s.get('shares', 0)) * float(s.get('avgPrice', 0)) for s in data.get('stocks_us', []))
            total_stocks = my_stock_val + us_stock_val

            # 2. 计算其他各项分类总额
            total_liquid = sum(float(a.get('value', 0)) for a in data.get('liquid_assets', [])) + float(data.get('cash_balance', 0))
            total_illiquid = sum(float(a.get('value', 0)) for a in data.get('illiquid_assets', []))
            total_gold = sum(float(g.get('value', 0)) for g in data.get('gold', []))

            # 3. 最终总计
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
        """基于总资产数据给建议"""
        if not self.google_api_key: return "未配置AI密钥"
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = f"这是我的全盘资产数据: {json.dumps(db_data)}。请用中文简短分析我的财务健康度，并给一个具体的理财建议（100字内）。"
            response = model.generate_content(prompt)
            return response.text
        except: return "暂时无法生成建议。"
