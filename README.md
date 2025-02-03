# SEO Product Redactor 📝

An AI-powered Streamlit application that automatically generates SEO-optimized descriptions for your e-commerce products using Anthropic's Claude Haiku API.

## Features 🎯

- Upload single or multiple CSV files
- Generate SEO-optimized short and long descriptions
- Intuitive user interface
- Export results as CSV or ZIP files
- Built-in error handling
- Real-time progress tracking
- Secure API key handling

## Requirements 📋

- Python 3.8 or higher
- Anthropic API key
- Internet connection

## Installation 🚀

1. Clone the repository:
```bash
git clone https://github.com/yourusername/seo-product-redactor.git
cd seo-product-redactor
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
streamlit run app.py
```

## Usage 💡

1. Get your Anthropic API key from [https://console.anthropic.com/](https://console.anthropic.com/)
2. Prepare your CSV file with a "Name" column containing your product names
3. Launch the application and enter your API key
4. Upload your CSV file(s)
5. Click "Generate Descriptions"
6. Download the processed results

## CSV File Format 📋

### Input Format
Your CSV file must contain:
- A "Name" column with product names

### Output Format
The processed file will include:
- Original "Name" column
- "Short description": SEO-optimized short HTML description
- "Description": Detailed HTML description with structured layout

## Generated Description Format 🎨

### Short Description
- Concise, engaging product summary
- SEO-optimized content
- Simple HTML paragraph format

### Long Description
- Detailed product description
- Structured HTML layout with:
  - Left and right-aligned image sections
  - H2 headings
  - Feature paragraphs
  - Bullet points for key features
  - Meta keywords
  - Product highlights
  - Styled container with shadow and rounded corners

## Déploiement sur Streamlit Cloud

1. Créez un compte sur [Streamlit Cloud](https://share.streamlit.io)
2. Connectez votre compte GitHub
3. Déployez l'application :
   - Cliquez sur "New app"
   - Sélectionnez ce repository
   - Main file path : `app.py`
   - Python version : 3.9

4. Configurez la clé API Anthropic :
   - Dans les paramètres de l'application
   - Ajoutez un secret : `ANTHROPIC_API_KEY`
   - Valeur : votre clé API Anthropic

## Troubleshooting 🔧

If you encounter any issues:
1. Ensure your CSV file has the correct format
2. Verify your Anthropic API key is valid
3. Check your internet connection
4. Make sure all dependencies are properly installed

## Support 💬

If you need help or want to report issues, please open an issue on the GitHub repository.
