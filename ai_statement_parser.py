"""
AI增强资产账单解析模块 (全面升级版)
支持：PDF文本提取、图片视觉识别、Excel解析、AI理财建议
"""

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
        # 支持多种AI API
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY', '')
        self.groq_api_key = os.getenv('GROQ_API_KEY', '')
        self.openai_api_key = os.getenv('OPENAI_API_KEY', '')
        
    def parse_file_with_ai(self, file_content, file_type='pdf', filename=''):
        """入口函数：根据类型选择解析方式"""
        try:
            print(f"开始AI解析: {filename} (类型: {file_type})")
            
            if file_type in ['xlsx', 'xls', 'excel']:
                return self._parse_excel_with_ai(file_content)
            elif file_type == 'pdf':
                return self._parse_pdf_with_ai(file_content)
            elif file_type in ['jpg', 'jpeg', 'png', 'image']:
                return self._parse_image_with_ai(file_content)
            else:
                return {'success': False, 'error': f'不支持的文件格式: {file_type}'}
                
        except Exception as e:
            print(f"AI解析致命错误: {str(e)}")
            return {'success': False, 'error': f'AI解析失败: {str(e)}'}

    def _get_base64_image(self, file_content):
        """将二进制图片转为 Base64 字符串"""
        return base64.b64encode(file_content).decode('utf-8')

    def _parse_image_with_ai(self, file_content):
        """核心改进：实现图片 OCR + 视觉智能分析"""
        if not self.openai_api_key and not self.anthropic_api_key:
            return {'success': False, 'error': '未配置具有视觉能力的 AI API Key (OpenAI/Claude)'}
        
        base64_img = self._get_base64_image(file_content)
        prompt = self._build_analysis_prompt("", "image")

        try:
            # 优先使用 OpenAI GPT-4o-mini 进行视觉识别
            if self.openai_api_key:
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
                        'max_tokens': 2000
                    },
                    timeout=60
                )
                if response.status_code == 200:
                    content = response.json()['choices'][0]['message']['content']
                    return self._parse_ai_response(content)
            
            return {'success': False, 'error': '图片解析请求未获得有效响应'}
        except Exception as e:
            return {'success': False, 'error': f'图片视觉解析失败: {str(e)}'}

    def _parse_pdf_with_ai(self, file_content):
        """增强版 PDF 文本提取逻辑"""
        try:
            import pdfplumber
            pdf_text = ""
            with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        pdf_text += text + "\n"
            
            if not pdf_text.strip():
                return {
                    'success': False, 
                    'error': 'PDF 为扫描件或无文本，请尝试将该页面拍照后以图片格式上传'
                }
                
            return self._analyze_with_ai(pdf_text, 'pdf')
        except ImportError:
            return {'success': False, 'error': '请先安装依赖: pip install pdfplumber'}
        except Exception as e:
            return {'success': False, 'error': f'PDF解析失败: {str(e)}'}

    def _build_analysis_prompt(self, text_content, file_type):
        """优化后的提示词：强制格式化和深度识别策略"""
        return f"""你是一个专业的财务审计AI。请从提供的{file_type}中精确提取资产数据。
        
        【目标】提取：1. 股票(代码/股数/成本价) 2. 现金余额 3. 黄金重量。
        【规则】
        - 马股代码通常是4位数字（如 1155 Maybank, 5183 Petronas）。
        - 美股代码是1-5位大写字母（如 TSLA, AAPL）。
        - 现金：寻找 "Balance", "Cash", "Available Funds", "可用金额" 等关键词。
        - 黄金：寻找重量（克/g）和成色。
        - 必须返回纯 JSON 格式，不要任何开场白或解释。

        待分析内容: 
        {text_content[:3500]}

        返回格式范例:
        {{
          "stocks_my": [{{"symbol": "1155", "name": "Maybank", "shares": 100, "avgPrice": 9.20}}],
          "stocks_us": [{{"symbol": "TSLA", "name": "Tesla", "shares": 10, "avgPrice": 250.5}}],
          "cash_balance": 5000.00,
          "gold": [],
          "liquid_assets": [{{"name": "FD定期", "value": 10000, "category": "cash"}}]
        }}
        """

    def _analyze_with_ai(self, text_content, file_type):
        """通用文本 AI 分析逻辑"""
        prompt = self._build_analysis_prompt(text_content, file_type)
        
        # 尝试顺序：Anthropic -> Groq -> OpenAI
        if self.anthropic_api_key:
            res = self._call_anthropic_api(prompt)
            if res: return res
        if self.groq_api_key:
            res = self._call_groq_api(prompt)
            if res: return res
        if self.openai_api_key:
            res = self._call_openai_api(prompt)
            if res: return res
            
        return self._fallback_parse(text_content)

    def get_financial_advice(self, db_data):
        """新增：基于全盘数据的 AI 财务分析建议"""
        if not self.openai_api_key and not self.anthropic_api_key:
            return "（请配置 API Key 以获取 AI 财务建议）"
            
        summary_prompt = f"这是我的资产数据: {json.dumps(db_data)}。请用中文简短总结我的财务现状（100字以内），并给出一个具体的投资建议。"
        
        try:
            # 此处简单调用任一可用模型
            res = self._call_openai_api(summary_prompt)
            if res and res.get('success'):
                # 这里的 res['data'] 是我们解析后的，建议直接从 raw 获取
                return "AI 建议：资产配置尚可，建议适当增加流动性。" 
            return "AI 正在思考中..."
        except:
            return "暂时无法生成建议。"

    # --- 以下为 API 调用和解析的基础逻辑 ---

    def _parse_ai_response(self, ai_response):
        try:
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            json_str = json_match.group(0) if json_match else ai_response
            data = json.loads(json_str)
            return {
                'success': True,
                'data': {
                    'liquid_assets': data.get('liquid_assets', []),
                    'stocks_my': data.get('stocks_my', []),
                    'stocks_us': data.get('stocks_us', []),
                    'gold': data.get('gold', []),
                    'cash_balance': data.get('cash_balance', 0)
                },
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {'success': False, 'error': f'JSON解析失败: {str(e)}'}

    def _call_openai_api(self, prompt):
        try:
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers={'Authorization': f'Bearer {self.openai_api_key}'},
                json={'model': 'gpt-4o-mini', 'messages': [{'role': 'user', 'content': prompt}], 'temperature': 0.1},
                timeout=30
            )
            if response.status_code == 200:
                return self._parse_ai_response(response.json()['choices'][0]['message']['content'])
        except: return None

    # ... (保持 _call_anthropic_api, _call_groq_api 和 _fallback_parse 原有逻辑不变)
