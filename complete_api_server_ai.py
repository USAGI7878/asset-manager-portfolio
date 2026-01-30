from flask import Flask, jsonify, request
from flask_cors import CORS
import os
from ai_statement_parser import AIAssetStatementParser
from gold_scraper import get_gold_prices

app = Flask(__name__)
CORS(app)

ai_handler = AIAssetStatementParser()

@app.route('/api/parse-statement-ai', methods=['POST'])
def api_parse_statement():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': '未找到文件'})
    
    file = request.files['file']
    content = file.read()
    filename = file.filename
    ext = filename.split('.')[-1].lower()
    
    # 只要是 pdf 就传 pdf，其余传 image
    file_type = 'pdf' if ext == 'pdf' else 'image'
    
    # 这里会得到包含 summary (grand_total) 的结果
    result = ai_handler.parse_file_with_ai(content, file_type, filename)
    return jsonify(result)

@app.route('/api/ai-advisor', methods=['POST'])
def api_get_advice():
    db_data = request.json
    advice = ai_handler.get_financial_advice(db_data)
    return jsonify({'success': True, 'advice': advice})

@app.route('/api/gold-price', methods=['GET'])
def api_gold_price():
    return jsonify(get_gold_prices())

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'google_ready': bool(os.getenv('GOOGLE_API_KEY'))})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
