import re
import io
import json
import requests
import os
from dotenv import load_dotenv

load_dotenv()

class AIAssetStatementParser:
    def __init__(self):
        # 只需要这一个 Key
        self.groq_api_key = os.getenv('GROQ_API_KEY', '')

    def parse_file_with_ai(self, file_content, file_type='pdf', filename=''):
        if not self.groq_api_key:
            return {'success': False, 'error': '未配置 GROQ_API_KEY，请在环境变量中设置'}

        try:
            # 1. 提取 PDF 文本
            if file_type == 'pdf':
                import pdfplumber
                with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                    text = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
            else:
                return {'success': False, 'error': '此版本仅支持 PDF 文本解析'}

            if not text.strip():
                return {'success': False, 'error': 'PDF 无法读取文字（可能是扫描件）'}

            # 2. 调用 Groq (使用 Llama 3)
            prompt = f"""你是一个财务助理。请从文本中提取资产数据。
            返回纯JSON格式(不要解释)：
            {{
              "stocks_my": [{{"symbol": "1155", "shares": 100, "avgPrice": 9.20}}],
              "stocks_us": [],
              "cash_balance": 0.0,
              "gold": []
            }}
            文本内容: {text[:3000]}"""

            res = requests.post(
                'https://api.groq.com/openai/v1/chat/completions',
                headers={'Authorization': f'Bearer {self.groq_api_key}'},
                json={
                    'model': 'llama-3.3-70b-versatile', 
                    'messages': [{'role': 'user', 'content': prompt}],
                    'temperature': 0
                },
                timeout=25
            )

            if res.status_code == 200:
                ai_text = res.json()['choices'][0]['message']['content']
                # 提取 JSON 部分
                json_match = re.search(r'\{.*\}', ai_text, re.DOTALL)
                if json_match:
                    return {'success': True, 'data': json.loads(json_match.group(0))}
            
            return {'success': False, 'error': f'Groq API 响应错误: {res.text}'}

        except Exception as e:
            return {'success': False, 'error': f'解析崩溃: {str(e)}'}
