# 💰 Dhanrakshak - AI-Powered Personal Finance Analyzer

**Dhanrakshak** (Sanskrit: धनरक्षक - Guardian of Wealth) is an intelligent expense tracking and analysis application that uses AI to automatically categorize and analyze your bank transactions. Get insights into your spending patterns with beautiful visualizations and smart categorization.

## ✨ Features

- **🤖 AI-Powered Categorization**: Automatically categorizes transactions using either Google Gemini API or a local LLM
- **📊 Interactive Dashboard**: Beautiful visualizations including:
  - Expense distribution by category (pie chart)
  - Spending by payment method (bar chart)
  - Daily spending trends over time (line chart)
- **💳 Smart Payment Method Detection**: Automatically identifies UPI, Card, Net Banking, Cash, and other payment methods
- **✏️ Editable Transaction Remarks**: Add personal notes to any transaction
- **📥 Export Functionality**: Download your analyzed data as CSV
- **🔒 Privacy-Focused**: Option to use local AI models for 100% data privacy
- **🎯 Custom Rules**: Intelligent detection of:
  - Self-transfers between accounts
  - Security net transfers
  - Investment SIPs
  - Specific merchant categorizations

## 🚀 Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/TheRealNeelaksh/DhanRakshak.git
   cd DhanRakshak
   ```

2. **Create a virtual environment** (recommended)
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables** (optional)
   Create a `.env` file in the root directory if you want to store your API key securely:
   ```
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

## 🎮 Usage

### Running the Application

Start the Streamlit web application:

```bash
streamlit run app.py
```

The application will open in your default web browser at `http://localhost:8501`

### Using the Application

1. **Configure AI Provider**
   - Choose between "Local Server" or "Gemini API"
   - For Gemini API: Enter your API key
   - For Local Server: Ensure LM Studio is running and enter the server URL

2. **Enter Your Information**
   - Provide your full name as it appears in bank statements
   - This helps identify self-transfers accurately

3. **Upload Bank Statement**
   - Supported formats: `.txt` or `.csv`
   - The file should contain columns: Date, Narration, Debit Amount, Credit Amount

4. **Process Statement**
   - Click "Process Statement" button
   - Wait for AI analysis to complete
   - View your financial dashboard with insights

5. **Review and Edit**
   - Review categorized transactions
   - Add personal remarks in the editable data table
   - Download the updated statement

## 🔧 Configuration

### AI Provider Options

#### Option 1: Google Gemini API (Recommended for Power Users)
- **Pros**: Fast, powerful, cloud-based
- **Cons**: Requires API key, data sent to Google
- **Setup**: Get API key from [Google AI Studio](https://makersuite.google.com/app/apikey)

#### Option 2: Local LLM via LM Studio (Privacy-Focused)
- **Pros**: 100% private, no data leaves your machine
- **Cons**: Requires more setup, needs decent hardware
- **Setup**: 
  1. Download [LM Studio](https://lmstudio.ai/)
  2. Download a Llama 3 model
  3. Start the local server
  4. Use `http://localhost:1234/v1/chat/completions` as the URL

### Category Configuration

Categories are defined in `config.py` and include:
- Shopping
- Food
- Entertainment
- Travel
- Utilities
- Health & Wellness
- Investments
- Security Net
- Self Transfer
- Family & Personal
- Miscellaneous
- Income

Payment methods are automatically detected based on transaction descriptions.

## 📂 Project Structure

```
DhanRakshak/
├── app.py                  # Main Streamlit application
├── processor.py            # Core transaction processing logic
├── config.py              # Configuration and category definitions
├── ai_enricher.py         # Base AI enricher (not actively used)
├── gemini_enricher.py     # Google Gemini API integration
├── local_ai_enricher.py   # Local LLM integration
├── gemini_cleaner.py      # Helper utilities
├── edaNotebook.py         # Exploratory data analysis
├── requirements.txt       # Python dependencies
├── .gitignore            # Git ignore rules
└── README.md             # This file
```

## 🛠️ Technology Stack

- **Frontend**: [Streamlit](https://streamlit.io/) - Interactive web application framework
- **Data Processing**: [Pandas](https://pandas.pydata.org/) - Data manipulation and analysis
- **Visualizations**: [Plotly](https://plotly.com/) - Interactive charts and graphs
- **AI/ML**: 
  - [Google Gemini API](https://ai.google.dev/) - Cloud-based LLM
  - [LM Studio](https://lmstudio.ai/) - Local LLM runtime
- **Language**: Python 3.8+

## 📊 Supported Bank Statement Formats

The application expects bank statements with the following columns:
- **Date**: Transaction date
- **Narration**: Transaction description
- **Debit Amount**: Amount debited from account
- **Credit Amount**: Amount credited to account

The parser automatically detects the header row and processes data accordingly.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

### Development Setup

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is open source and available under the [MIT License](LICENSE).

## 👨‍💻 Author

**Neelaksh Saxena**
- GitHub: [@TheRealNeelaksh](https://github.com/TheRealNeelaksh)

## 🙏 Acknowledgments

- Google Gemini API for powerful AI capabilities
- Streamlit team for the amazing framework
- LM Studio for local LLM capabilities
- Open source community for various libraries used

## 📧 Support

If you encounter any issues or have questions, please:
1. Check the existing [Issues](https://github.com/TheRealNeelaksh/DhanRakshak/issues)
2. Create a new issue if your problem isn't already reported
3. Provide detailed information about the problem

## 🔮 Future Enhancements

- [ ] Support for multiple bank formats
- [ ] Budget tracking and alerts
- [ ] Recurring transaction detection
- [ ] Multi-month analysis
- [ ] Mobile app version
- [ ] Machine learning-based fraud detection
- [ ] Export to various formats (PDF, Excel)
- [ ] Multi-user support with authentication

---

**Made with ❤️ for better financial awareness**
