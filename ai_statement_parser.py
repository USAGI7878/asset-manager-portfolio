import re
import io
import json
import requests
import os
import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

class AIAssetStatementParser:
    def __init__(self):
        self.google_api_key = os.getenv('GOOGLE_API_KEY', '')
        self.groq_api_key = os.getenv('GROQ_API_KEY', '')
        if self.google_api_key:
            genai.configure(api_key=self.google_api_key)

    def parse_file_with_ai(self, file_content, file_type='pdf', filename=''):
        """主入口：优先使用 Google Gemini 处理图片和复杂 PDF"""
        try:
            if file_type in ['jpg', 'jpeg', 'png', 'image', 'pdf']:
                return self._parse_with_gemini(file_content, file_type)
            else:
                return {'success': False, 'error': f'暂不支持格式: {file_type}'}
        except Exception as e:
            return {'success': False, 'error': f'解析失败: {str(e)}'}

    def _parse_with_gemini(self, file_content, file_type):
        """使用 Gemini 1.5 Flash 提取数据并计算总额"""
        if not self.google_api_key:
            return {'success': False, 'error': '未配置 GOOGLE_API_KEY'}

        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # 针对你提供的“资产.pdf”格式优化的 Prompt
        prompt = """
        你是一个专业的财务审计机器人。请分析上传的文件，提取所有资产信息。
        要求：
        1. 识别并归类：
           - 可动资产 (liquid_assets): 如 TNG, ASNB, 银行存款, 现金等。
           - 不可动资产 (illiquid_assets): 如 KWSP, 房地产等。
           - 股票 (stocks): 区分 symbol, shares, avgPrice。
           - 黄金 (gold): 提取名称和对应的估算价值。
        2. 返回纯 JSON 格式，必须包含以下结构：
        {
          "liquid_assets": [{"name": "TNG", "value": 51.83}],
          "illiquid_assets": [{"name": "KWSP", "value": 25411.71}],
          "stocks_my": [{"symbol": "MAYBANK", "shares": 100, "avgPrice": 9.5}],
          "stocks_us": [],
          "gold": [{"name": "实体黄金", "value": 17524.88}],
          "cash_balance": 0
        }
        不要输出任何 Markdown 标记或额外文字。
        """

        # 处理文件数据
        content_blob = {
            'mime_type': 'application/pdf' if file_type == 'pdf' else 'image/jpeg',
            'data': file_content
        }

        response = model.generate_content([prompt, content_blob])
        return self._process_and_calculate(response.text)

    def _process_and_calculate(self, ai_text):
        """清洗数据并进行类似 Excel 的自动求和"""
        try:
            # 去除 JSON 标记
            clean_json = re.search(r'\{.*\}', ai_text, re.DOTALL).group(0)
            data = json.loads(clean_json)

            # --- 开始自动计算统计 (类似你的 Excel 逻辑) ---
            
            # 1. 计算股票总价值
            s_my_total = sum(float(s.get('shares', 0)) * float(s.get('avgPrice', 0)) for s in data.get('stocks_my', []))
            s_us_total = sum(float(s.get('shares', 0)) * float(s.get('avgPrice', 0)) for s in data.get('stocks_us', []))
            total_stocks = s_my_total + s_us_total

            # 2. 计算可动/不可动/黄金总价值
            total_liquid = sum(float(a.get('value', 0)) for a in data.get('liquid_assets', [])) + data.get('cash_balance', 0)
            total_illiquid = sum(float(a.get('value', 0)) for a in data.get('illiquid_assets', []))
            total_gold = sum(float(g.get('value', 0)) for g in data.get('gold', []))

            # 3. 资产总计 (Total Assets)
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
            return {'success': False, 'error': f'数据统计失败: {str(e)}'}
