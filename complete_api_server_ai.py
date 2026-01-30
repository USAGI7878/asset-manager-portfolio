from flask import Flask, jsonify, request
from flask_cors import CORS
import os
from ai_statement_parser import AIAssetStatementParser
from gold_scraper import get_gold_prices # 假设你已有该爬虫脚本

app = Flask(__name__)
CORS(app)

# 初始化解析器
ai_handler = AIAssetStatementParser()

@app.route('/api/parse-statement-ai', methods=['POST'])
def api_parse_statement():  # 函数名已修改，避免与类方法重名
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': '未找到文件'})
    
    file = request.files['file']
    content = file.read()
    ext = file.filename.split('.')[-1].lower()
    
    file_type = 'image' if ext in ['jpg', 'jpeg', 'png'] else ext
    result = ai_handler.parse_file_with_ai(content, file_type, file.filename)
    return jsonify(result)

@app.route('/api/ai-advisor', methods=['POST'])
def api_get_advice():
    db_data = request.json
    advice = ai_handler.get_financial_advice(db_data)
    return jsonify({'success': True, 'advice': advice})

@app.route('/api/gold-price', methods=['GET'])
def api_gold_price():
    # 调用你之前的 gold_scraper.py
    return jsonify(get_gold_prices())

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'ai_ready': bool(os.getenv('OPENAI_API_KEY'))})

if __name__ == '__main__':
    # Render 环境会自动分配 PORT
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
