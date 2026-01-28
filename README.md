# 💰 Smart Asset Management System

A comprehensive personal finance application that integrates multi-platform stock management, real-time gold price tracking, and AI-powered investment analysis.

## 🌟 Features

- 📊 **Multi-Asset Management** - Stocks, gold, cash, and investments
- 📈 **Real-Time Price Updates** - Integration with Alpha Vantage API
- 🏆 **Gold Price Tracking** - Automatic tracking of 916 gold prices in Malaysia
- 📤 **Statement Parser** - Support for MOOMOO, Webull, and other brokers
- 🤖 **AI Analysis** - Claude AI-powered asset allocation recommendations
- 📱 **Responsive Design** - Mobile, tablet, and desktop support
- 📉 **Historical Tracking** - Asset performance over time
- 💱 **Currency Conversion** - Automatic USD to MYR conversion

## 🛠️ Tech Stack

**Backend:**
- Python 3.8+
- Flask (REST API)
- BeautifulSoup4 (Web scraping)
- Pandas (Data processing)
- Alpha Vantage API

**Frontend:**
- React
- Recharts (Data visualization)
- TailwindCSS (Styling)

**AI Integration:**
- Anthropic Claude API

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Installation

1. Clone the repository
```bash
git clone https://github.com/USAGI7878/asset-manager-portfolio.git
cd asset-manager-portfolio
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Configure API keys
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your API keys
# ALPHA_VANTAGE_API_KEY=your_key_here
```

4. Run the API server
```bash
python complete_api_server_safe.py
```

5. Access the API
```
http://localhost:5000
```

## 📖 API Documentation

### Get Stock Price
```bash
GET /api/stock-price/{symbol}?exchange=US
```

**Example:**
```bash
curl http://localhost:5000/api/stock-price/VOO
```

### Get Gold Price
```bash
GET /api/gold-price
```

**Response:**
```json
{
  "success": true,
  "data": {
    "gold_916": 630.00,
    "gold_916_buyback_93": 585.90,
    "last_updated": "2026-01-28 10:01:00"
  }
}
```

### Parse Broker Statement
```bash
POST /api/parse-statement
Content-Type: multipart/form-data

file: statement.xlsx
platform: moomoo
```

### Get Forex Rate
```bash
GET /api/forex-rate?from=USD&to=MYR
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```env
# Alpha Vantage API Key (Required)
ALPHA_VANTAGE_API_KEY=your_api_key_here

# Server Configuration
API_HOST=localhost
API_PORT=5000

# Cache Settings
CACHE_DURATION_MINUTES=15

# Environment
ENVIRONMENT=development
```

### Supported Brokers

- MOOMOO (Excel, CSV, PDF)
- Webull (Excel, CSV)
- Generic brokers (Excel, CSV with standard columns)

## 📊 Features in Detail

### Multi-Platform Stock Management

- Import holdings from multiple broker platforms
- Automatic price synchronization
- Real-time P&L calculation
- Portfolio diversification analysis

### Gold Price Tracking

- Real-time 916 gold prices in Malaysia
- Multiple buyback rate options (90%, 93%, 95%)
- Profit/loss tracking for each gold item
- Historical price trends

### AI-Powered Analysis

- Risk assessment based on current allocation
- Portfolio optimization suggestions
- Market timing recommendations
- Personalized investment advice

## 🔒 Privacy & Security

- All data stored locally
- API keys managed through environment variables
- Uploaded files deleted immediately after processing
- No personal data in repository

## 📸 Screenshots

[Add screenshots here using demo data]

## 🎯 Future Roadmap

- [ ] Support for more broker platforms
- [ ] Price alert notifications
- [ ] Mobile app development
- [ ] Cloud data synchronization
- [ ] Advanced portfolio analytics
- [ ] Tax reporting features

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👤 Author

**Your Name**
- GitHub: [@your_username](https://github.com/USAGI7878)
- LinkedIn: [Your LinkedIn](https://linkedin.com/in/USAGI7878)

## ⚠️ Disclaimer

This is a personal project for educational purposes. Investment decisions should be made carefully. Past performance does not guarantee future results.

## 🙏 Acknowledgments

- Alpha Vantage for stock price data
- BuySilverMalaysia for gold price reference
- Anthropic for Claude AI API
- Open source community

---

**Note:** This project demonstrates full-stack development capabilities including API integration, data processing, web scraping, and AI implementation.
