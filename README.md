# DhanRakshak 💰

**DhanRakshak** (धन रक्षक - "Guardian of Wealth") is an intelligent personal finance dashboard that helps you analyze your bank statements, categorize transactions, and gain insights into your spending habits.

## ✨ Features

- **Smart Transaction Analysis**: Upload bank statements (CSV/TXT) and let AI intelligently categorize your transactions
- **Dual AI Support**: Choose between Google's Gemini API or a local LLaMA model for 100% privacy
- **Interactive Dashboard**: Beautiful visualizations including:
  - Income vs Expenses overview
  - Expense distribution by category (pie chart)
  - Spending by payment method (bar chart)
  - Daily spending trends (line graph)
- **Editable Transactions**: Review and edit transaction remarks directly in the interface
- **Export Capability**: Download your analyzed and annotated statements as CSV
- **Privacy-First**: Option to use local AI models ensures your financial data never leaves your machine

## 🚀 Getting Started

### Prerequisites

- Python 3.7 or higher
- pip (Python package installer)

### Installation

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
   
   Create a `.env` file in the project root for storing sensitive information like API keys:
   ```
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

### Running the Application

```bash
streamlit run src/app.py
```

The application will open in your default web browser at `http://localhost:8501`.

## 📖 Usage Guide

### Step 1: Configure AI Provider

Choose your preferred AI provider in the sidebar:

- **Gemini API**: Uses Google's Gemini 2.5 Flash model for powerful analysis
  - Requires a Gemini API key (get one from [Google AI Studio](https://aistudio.google.com/))
  
- **Local Server**: Uses a local LLaMA model running on your machine
  - Requires LM Studio or similar local inference server
  - Default URL: `http://localhost:1234/v1/chat/completions`
  - Ensures complete privacy - your data never leaves your computer

### Step 2: Enter Your Information

- Enter your full name as it appears in your bank statements
- This helps the system accurately identify self-transfers and personal transactions

### Step 3: Upload Bank Statement

- Support formats: `.txt` or `.csv`
- The statement should contain columns: Date, Narration, Debit Amount, Credit Amount
- Click "Process Statement" to begin analysis

### Step 4: Review and Edit

- View comprehensive financial analytics
- Edit transaction remarks directly in the data table
- Download the annotated statement for your records

## 🗂️ Project Structure

```
DhanRakshak/
├── data/
│   └── data.csv              # Sample input statement
├── notebooks/
│   └── edaNotebook.py        # Exploratory data analysis notebook
├── src/
│   ├── app.py                # Main Streamlit application
│   ├── processor.py          # Core transaction processing logic
│   ├── config.py             # Configuration constants and rules
│   ├── gemini_enricher.py    # Gemini API integration
│   ├── local_ai_enricher.py  # Local LLaMA model integration
│   ├── gemini_cleaner.py     # Data cleaning utilities for Gemini
│   ├── ai_enricher.py        # General AI enrichment utilities
│   ├── utils/                # Parser and helper utilities
│   └── tests/                # Unit tests
├── requirements.txt          # Python dependencies
├── .gitignore                # Git ignore patterns
└── README.md                 # This file
```

## 🛠️ Technology Stack

- **Frontend**: Streamlit
- **Data Processing**: Pandas, NumPy
- **Visualizations**: Plotly Express
- **AI/ML**: 
  - Google Generative AI (Gemini API)
  - Local LLaMA models via LM Studio
- **Additional Libraries**: 
  - python-dotenv (environment management)
  - openpyxl (Excel file support)

## 📊 Transaction Categories

DhanRakshak automatically categorizes transactions into:

- 💳 Shopping
- 🍔 Food
- 🎬 Entertainment
- ✈️ Travel
- 🔧 Utilities
- 🏥 Health & Wellness
- 📈 Investments
- 🛡️ Security Net
- 🔄 Self Transfer
- 👨‍👩‍👧‍👦 Family & Personal
- 📋 Miscellaneous
- 💵 Income

## 🔒 Privacy & Security

- Your bank statements are processed locally
- When using Local AI option, no data is sent to external servers
- API keys are never stored in code or version control
- CSV files are excluded from git tracking via `.gitignore`

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is available for use and modification. Please check with the repository owner for specific license terms.

## 👨‍💻 Author

**Neelaksh Saxena**

## 🙏 Acknowledgments

- Built with Streamlit
- Powered by Google Gemini AI and LLaMA models
- Inspired by the need for better personal finance management tools

---

**Note**: This application is designed for personal use. Always keep your financial data secure and use strong passwords for any API keys or credentials.
