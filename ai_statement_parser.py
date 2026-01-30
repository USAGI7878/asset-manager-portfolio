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
    def __init__(self):
        self.openai_api_key = os.getenv('OPENAI_API_KEY', '')
        self.groq_api_key = os.getenv('GROQ_API_KEY', '')
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY', '')

    def parse_file_with_ai(self, file_content, file_type='pdf', filename=''):
        try:
            # 1. 提取文本
            if file_type == 'pdf':
                text = self._extract_pdf_text(file_content)
            elif file_type in ['jpg', 'jpeg', 'png', 'image']:
                # 如果是图片，目前只能靠 OpenAI GPT-4o-mini 或 Claude-3-Vision
                return self._parse_image_with_ai(file_content)
            else:
                return {'success': False, 'error': f'不支持格式: {file_type}'}

            if not text.strip():
                return {'success': False, 'error': '未提取到有效文本'}

            # 2. 多模型轮询解析文本
            prompt = self._build_analysis_prompt(text, file_type)
            
            # 顺序：Groq (快/免费) -> OpenAI -> Claude
            for model_name, call_func in [
                ('Groq', lambda: self._call_groq_api(prompt)),
                ('OpenAI', lambda: self._call_openai_api(prompt)),
                ('Claude', lambda: self._call_anthropic_api(prompt))
            ]:
                print(f"正在尝试使用 {model_name} 解析...")
                result = call_func()
                if result and result.get('success'):
                    print(f"{model_name} 解析成功！")
                    return result
            
            return {'success': False, 'error': '所有AI模型均请求失败，请检查网络或API Key'}

        except Exception as e:
            return {'success': False, 'error': f'解析异常: {str(e)}'}

    def _extract_pdf_text(self, file_content):
        import pdfplumber
        with pdfplumber.open(io.BytesIO(file_content)) as pdf:
            return "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])

    def _build_analysis_prompt(self, text, file_type):
        # 修复了双大括号转义问题
        return f"""你是一个财务审计AI。请从{file_type}内容中提取资产数据。
        必须返回纯JSON格式：
        {{
          "stocks_my": [{{"symbol": "1155", "shares": 100, "avgPrice": 9.20}}],
          "stocks_us": [{{"symbol": "TSLA", "shares": 10, "avgPrice": 250.5}}],
          "cash_balance": 5000.0,
          "gold": []
        }}
        内容: {text[:3000]}"""

    # --- 各个 AI 的调用实现 ---

    def _call_groq_api(self, prompt):
        if not self.groq_api_key: return None
        try:
            res = requests.post(
                'https://api.groq.com/openai/v1/chat/completions',
                headers={'Authorization': f'Bearer {self.groq_api_key}'},
                json={'model': 'llama-3.3-70b-versatile', 'messages': [{'role': 'user', 'content': prompt}], 'temperature': 0},
                timeout=20
            )
            return self._parse_ai_response(res.json()['choices'][0]['message']['content'])
        except: return None

    def _call_openai_api(self, prompt):
        if not self.openai_api_key: return None
        try:
            res = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers={'Authorization': f'Bearer {self.openai_api_key}'},
                json={'model': 'gpt-4o-mini', 'messages': [{'role': 'user', 'content': prompt}], 'temperature': 0},
                timeout=20
            )
            return self._parse_ai_response(res.json()['choices'][0]['message']['content'])
        except: return None

    def _call_anthropic_api(self, prompt):
        if not self.anthropic_api_key: return None
        try:
            res = requests.post(
                'https://api.anthropic.com/v1/messages',
                headers={'x-api-key': self.anthropic_api_key, 'anthropic-version': '2023-06-01', 'content-type': 'application/json'},
                json={'model': 'claude-3-haiku-20240307', 'max_tokens': 1024, 'messages': [{'role': 'user', 'content': prompt}]},
                timeout=20
            )
            return self._parse_ai_response(res.json()['content'][0]['text'])
        except: return None

    def _parse_ai_response(self, ai_response):
        try:
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                return {'success': True, 'data': data}
            return None
        except: return None
