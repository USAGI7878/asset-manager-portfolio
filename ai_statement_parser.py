import pandas as pd
import re
from datetime import datetime
import io
import json
import requests
import os
import base64
from dotenv import load_dotenv

load_dotenv()

class AIAssetStatementParser:
    """AI增强资产账单解析器"""
    
    def __init__(self):
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY', '')
        self.groq_api_key = os.getenv('GROQ_API_KEY', '')
        self.openai_api_key = os.getenv('OPENAI_API_KEY', '')
        
    def parse_file_with_ai(self, file_content, file_type='pdf', filename=''):
        """入口函数"""
        try:
            if file_type in ['xlsx', 'xls', 'excel']:
                # 这里假设你已经有了 _parse_excel_with_ai
                return {'success': False, 'error': 'Excel解析尚未实现'}
            elif file_type == 'pdf':
                return self._parse_pdf_with_ai(file_content)
            elif file_type in ['jpg', 'jpeg', 'png', 'image']:
                return self._parse_image_with_ai(file_content)
            else:
                return {'success': False, 'error': f'不支持格式: {file_type}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _get_base64_image(self, file_content):
        return base64.b64encode(file_content).decode('utf-8')

    def _parse_image_with_ai(self, file_content):
        """图片视觉解析"""
        if not self.openai_api_key:
            return {'success': False, 'error': '未配置 OpenAI API Key'}
        
        base64_img = self._get_base64_image(file_content)
        prompt = self._build_analysis_prompt("", "图片")

        try:
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers={'Authorization': f'Bearer {self.openai_api_key}', 'Content-Type': 'application/json'},
                json={
                    'model': 'gpt-4o-mini',
                    'messages': [{
                        'role': 'user',
                        'content': [
                            {'type': 'text', 'text': prompt},
                            {'type': 'image_url', 'image_url': {'url': f"data:image/jpeg;base64,{base64_img}"}}
                        ]
                    }],
                    'temperature': 0
                },
                timeout=60
            )
            if response.status_code == 200:
                content = response.json()['choices'][0]['message']['content']
                return self._parse_ai_response(content)
            return {'success': False, 'error': f'API报错: {response.status_code}'}
        except Exception as e:
            return {'success': False, 'error': f'视觉解析失败: {str(e)}'}

    def _parse_pdf_with_ai(self, file_content):
        """PDF 文本提取"""
        try:
            import pdfplumber
            pdf_text = ""
            with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text: pdf_text += text + "\n"
            
            if not pdf_text.strip():
                return {'success': False, 'error': 'PDF无文字，请拍照上传'}
            return self._analyze_with_ai(pdf_text, 'PDF')
        except Exception as e:
            return {'success': False, 'error': f'PDF解析过程错误: {str(e)}'}

    def _build_analysis_prompt(self, text_content, file_type):
        # 修复核心：将 JSON 范例的大括号改为 {{ 和 }}
        return f"""你是一个财务审计AI。请从{file_type}中提取资产数据。
        目标提取：1. 股票(代码/股数/成本价) 2. 现金余额 3. 黄金重量。
        规则：马股代码为4位数字；美股为大写字母。
        必须返回纯JSON，格式如下：
        {{
          "stocks_my": [{{"symbol": "1155", "shares": 100, "avgPrice": 9.20}}],
          "stocks_us": [{{"symbol": "TSLA", "shares": 10, "avgPrice": 250.5}}],
          "cash_balance": 5000.0,
          "gold": []
        }}
        内容: {text_content[:3000]}"""

    def _analyze_with_ai(self, text_content, file_type):
        prompt = self._build_analysis_prompt(text_content, file_type)
        return self._call_openai_api(prompt)

    def _call_openai_api(self, prompt):
        try:
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers={'Authorization': f'Bearer {self.openai_api_key}'},
                json={'model': 'gpt-4o-mini', 'messages': [{'role': 'user', 'content': prompt}], 'temperature': 0},
                timeout=30
            )
            if response.status_code == 200:
                return self._parse_ai_response(response.json()['choices'][0]['message']['content'])
            return {'success': False, 'error': 'OpenAI API 请求失败'}
        except Exception as e: 
            return {'success': False, 'error': f'调用异常: {str(e)}'}

    def _parse_ai_response(self, ai_response):
        try:
            # 使用正则表达式提取 JSON 部分，防止 AI 返回多余的文字
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                return {'success': True, 'data': data}
            return {'success': False, 'error': 'AI未返回有效的JSON格式'}
        except Exception as e: 
            return {'success': False, 'error': f'JSON解析失败: {str(e)}'}

    def get_financial_advice(self, db_data):
        """生成财务建议"""
        if not self.openai_api_key: return "未配置AI密钥"
        prompt = f"我的资产数据: {json.dumps(db_data)}。请用中文给出一个简短的投资理财建议。"
        try:
            res = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers={'Authorization': f'Bearer {self.openai_api_key}'},
                json={'model': 'gpt-4o-mini', 'messages': [{'role': 'user', 'content': prompt}]}
            )
            return res.json()['choices'][0]['message']['content']
        except: return "AI 暂时无法提供建议"
