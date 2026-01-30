from flask import Flask, jsonify, request
from flask_cors import CORS
import os
from ai_statement_parser import AIAssetStatementParser
from gold_scraper import get_gold_prices

app = Flask(__name__)
CORS(app)

# 初始化解析器
ai_handler = AIAssetStatementParser()

@app.route('/api/parse-statement-ai', methods=['POST'])
def api_parse_statement():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': '未找到文件'})
    
    file = request.files['file']
    content = file.read()
    filename = file.filename
    ext = filename.split('.')[-1].lower()
    
    # 自动识别是 PDF 还是图片
    file_type = 'pdf' if ext == 'pdf' else 'image'
    
    # 调用增强后的 Gemini 解析逻辑
    result = ai_handler.parse_file_with_ai(content, file_type, filename)
    return jsonify(result)

@app.route('/api/ai-advisor', methods=['POST'])
def api_get_advice():
    # 接收包含 summary 的数据
    db_data = request.json
    advice = ai_handler.get_financial_advice(db_data)
    return jsonify({'success': True, 'advice': advice})

@app.route('/api/gold-price', methods=['GET'])
def api_gold_price():
    return jsonify(get_gold_prices())

@app.route('/api/health', methods=['GET'])
def health():
    # 检查 Google Key 是否在 Render 环境中生效
    return jsonify({
        'status': 'ok', 
        'google_ready': bool(os.getenv('GOOGLE_API_KEY'))
    })

if __name__ == '__main__':
    # 适配 Render 端口
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
