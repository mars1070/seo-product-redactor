import streamlit as st
import pandas as pd
import anthropic
import os
from dotenv import load_dotenv
import tempfile
import zipfile
import io
import re
from langdetect import detect, lang_detect_exception
import time

# Configuration de la page Streamlit
st.set_page_config(
    page_title="Rédacteur de Produits SEO ",
    page_icon="📝",
    layout="wide"
)

# Styles CSS personnalisés
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        margin-top: 20px;
    }
    .success {
        padding: 20px;
        border-radius: 10px;
        background-color: #d4edda;
        color: #155724;
        margin: 10px 0;
    }
    .error {
        padding: 20px;
        border-radius: 10px;
        background-color: #f8d7da;
        color: #721c24;
        margin: 10px 0;
    }
    </style>
""", unsafe_allow_html=True)

def generate_descriptions(client, product_name, config):
    """Generates short and long descriptions for a product."""
    
    # Language mapping
    language_mapping = {
        "Français": "fr",
        "Anglais (US)": "en_us",
        "Anglais (UK)": "en_uk",
        "Espagnol": "es",
        "Allemand": "de",
        "Italien": "it",
        "Portugais": "pt",
        "Néerlandais": "nl",
        "Polonais": "pl",
        "Grec": "el",
        "Turc": "tr",
        "Roumain": "ro",
        "Norvégien": "no",
        "Suédois": "sv"
    }
    
    # Language detection
    if config['target_language'] == "Auto-détection":
        try:
            lang = detect(product_name)
        except lang_detect_exception.LangDetectException:
            lang = 'en_us'
    else:
        lang = language_mapping.get(config['target_language'], 'en_us')
    
    # Full language names
    full_language_names = {
        'fr': 'FRENCH',
        'en_us': 'AMERICAN ENGLISH',
        'en_uk': 'BRITISH ENGLISH',
        'es': 'SPANISH',
        'de': 'GERMAN',
        'it': 'ITALIAN',
        'pt': 'PORTUGUESE',
        'nl': 'DUTCH',
        'pl': 'POLISH',
        'el': 'GREEK',
        'tr': 'TURKISH',
        'ro': 'ROMANIAN',
        'no': 'NORWEGIAN',
        'sv': 'SWEDISH'
    }

    try:
        # Prompt for short description
        short_prompt = f'''You are a professional e-commerce copywriter. Write a compelling short product description (200-250 characters) in {full_language_names[lang]} for: {product_name}

CRITICAL LANGUAGE REQUIREMENT:
- Write ONLY in {full_language_names[lang]}
- NO words in other languages allowed
- If you cannot write in {full_language_names[lang]}, respond with "Language not supported"

CRITICAL FORMAT REQUIREMENT:
- Return ONLY a single <p> tag containing your text
- Exact format must be: <p>Your text here</p>
- NO other text or tags allowed
- NO comments
- NO explanations
- NO line breaks
- ONLY <p>text</p>

WRITING GUIDELINES:
1. Start with one of these approaches (in a short sentence):
   - Direct benefit
   - Emotion or experience
   - Engaging question
   - Direct action verb
   - Key feature with benefit
   - Problem-solution
   - Projected usage

2. Target audience adaptation:
   - Automatically adapt to product type (e.g., jewelry → women 30-50, dashcam → men 45-65)
   - Match tone and style to product category

3. Content requirements:
   - Main keyword (product name) must be recognizable throughout
   - Mix features, benefits, and usage naturally
   - Keep sentences balanced and similar in length
   - Use precise terms, avoid excessive adjectives
   - Adapt tone to target market culture

4. Structure:
   - Separate features and benefits into distinct sentences
   - Maintain natural flow and readability
   - Link features to specific benefits or concrete usage

Remember: The output must be ONLY the HTML paragraph with your description in {full_language_names[lang]}, nothing else.'''

        # Prompt for long description
        long_prompt = f'''You are an e-commerce copywriting expert. Create an engaging HTML product description in {full_language_names[lang]} that highlights two specific benefits of the product.

CRITICAL LANGUAGE REQUIREMENT:
- Write ONLY in {full_language_names[lang]}
- NO words in other languages allowed
- This includes ALL text: titles, paragraphs, and any other content
- If you cannot write in {full_language_names[lang]}, respond with "Language not supported"

CRITICAL FORMAT REQUIREMENTS:
- Return ONLY raw HTML code
- NO introductory text like "Here's the description..."
- NO comments or explanations
- ONLY <h2> and <p> tags
- EXACTLY two <h2> titles and two <p> paragraphs

CRITICAL PARAGRAPH REQUIREMENTS:
- Each paragraph MUST contain 3-4 well-constructed sentences
- Word count MUST be between 80-100 words per paragraph
- This is a strict requirement for SEO optimization
- Carefully count your words and sentences before submitting

Guidelines:
1. Structure:
   - Two <h2> titles: descriptive benefit-focused headings (6-10 words)
   - Two <p> paragraphs: EXACTLY 3-4 sentences each, 80-100 words, developing each benefit
   
2. Writing Style:
   - Descriptive and engaging titles (6-10 words)
   - Include main benefit + how/why it matters in each title
   - Example title structure: "Professional Quality Results for Your Daily Care"
   - Each paragraph must have 3-4 complete, well-structured sentences
   - Each sentence must express a clear idea

Product to describe: {product_name}

Tone: {config['tone']}
Writing Style: {config['writing_style']}
Language Level: {config['language_level']}
Target Age: {config['target_age']}
Target Gender: {config['target_gender']}
Expertise Level: {config['expertise_level']}
Temperature: {config['temperature']}
Keywords per Text: {config['keywords_per_text']}
Paragraph Style: {config['paragraph_style']}
Title Style: {config['title_style']}'''

        # Génération de la description courte
        short_response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=300,
            temperature=float(config['temperature']),
            messages=[{"role": "user", "content": short_prompt}]
        )
        short_description = short_response.content[0].text.strip()

        # Vérification du format de la description courte
        if not short_description.startswith('<p>') or not short_description.endswith('</p>'):
            short_description = f"<p>{short_description}</p>"
        
        # Si le texte contient d'autres balises HTML, on les supprime
        if '<' in short_description[3:-4]:  # Vérifie entre <p> et </p>
            short_description = f"<p>{re.sub('<[^>]+>', '', short_description[3:-4])}</p>"

        # Génération de la description longue
        long_response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1000,
            temperature=float(config['temperature']),
            messages=[{"role": "user", "content": long_prompt}]
        )
        long_description = long_response.content[0].text

        return short_description, long_description
    except Exception as e:
        st.error(f"Erreur lors de la génération des descriptions : {str(e)}")
        return None, None

def process_file(file, api_key, config):
    """Traite un fichier CSV et génère les descriptions."""
    try:
        client = anthropic.Anthropic(api_key=api_key)
        
        # Lecture du fichier CSV
        df = pd.read_csv(file)
        
        # Vérification des colonnes requises
        required_columns = ['Name']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            st.error(f"Le fichier CSV doit contenir les colonnes suivantes : {', '.join(missing_columns)}")
            return None
            
        # Ajout des colonnes pour les descriptions
        df['Short description'] = ''
        df['Description'] = ''
        
        # Barre de progression
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Créer un conteneur pour l'aperçu des résultats
        preview = st.container()
        with preview:
            st.subheader("🔍 Aperçu des descriptions générées")
            current_product = st.empty()
            current_short = st.empty()
            current_long = st.empty()
        
        # Traitement de chaque produit
        for index, row in df.iterrows():
            product_name = row['Name']
            status_text.text(f"Traitement du produit {index + 1}/{len(df)}: {product_name}")
            
            # Afficher le nom du produit en cours
            current_product.markdown(f"### 📦 Produit en cours : {product_name}")
            
            short_desc, long_desc = generate_descriptions(client, product_name, config)
            if short_desc and long_desc:
                df.at[index, 'Short description'] = short_desc
                df.at[index, 'Description'] = long_desc
                
                # Afficher les descriptions générées
                current_short.markdown(f"**Description courte :**\n{short_desc}")
                current_long.markdown(f"**Description longue :**\n{long_desc}")
                
                # Ajouter une ligne de séparation visuelle
                st.markdown("---")
            
            progress_bar.progress((index + 1) / len(df))
            
            # Pause entre chaque produit (3 secondes)
            if index < len(df) - 1:  # Ne pas attendre après le dernier produit
                with st.spinner(f"Pause de 3 secondes avant le prochain produit..."):
                    time.sleep(3)
        
        status_text.text("Traitement terminé!")
        return df
    except Exception as e:
        st.error(f"Erreur lors du traitement du fichier : {str(e)}")
        return None

def main():
    st.title("🎯 Rédacteur de Produits SEO")
    
    st.markdown("""
    ### Générateur de descriptions produits optimisées pour WooCommerce
    
    Cette application utilise l'IA Claude d'Anthropic pour générer des descriptions de produits **optimisées SEO** dans 14 langues.
    Importez simplement votre fichier CSV WooCommerce, configurez le style de rédaction, et obtenez des descriptions :
    - Courtes (200-250 caractères) pour les aperçus
    - Longues (2 paragraphes de 80-100 mots) avec titres H2
    - Adaptées à votre cible et optimisées pour le référencement
    """)

    # Récupération de la clé API depuis les variables d'environnement
    api_key = st.secrets["ANTHROPIC_API_KEY"]
    if not api_key:
        st.error("La clé API Anthropic n'est pas configurée. Veuillez l'ajouter dans les secrets de l'application.")
        st.stop()
        
    client = anthropic.Anthropic(api_key=api_key)

    # Configuration du style de rédaction
    with st.expander("⚙️ Configuration du rédacteur", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Style de rédaction")
            
            target_language = st.selectbox(
                "Langue de rédaction",
                [
                    "Français", 
                    "Anglais (US)", 
                    "Anglais (UK)",
                    "Espagnol", 
                    "Allemand", 
                    "Italien", 
                    "Portugais",
                    "Néerlandais",
                    "Polonais",
                    "Grec",
                    "Turc",
                    "Roumain",
                    "Norvégien",
                    "Suédois",
                    "Auto-détection"
                ],
                index=14,
                help="Choisissez la langue de rédaction ou laissez l'auto-détection"
            )
            
            tone = st.select_slider(
                "Ton",
                options=["Très professionnel", "Professionnel", "Équilibré", "Décontracté", "Très décontracté"],
                value="Équilibré"
            )
            
            writing_style = st.select_slider(
                "Style d'écriture",
                options=["Très persuasif", "Persuasif", "Équilibré", "Informatif", "Très informatif"],
                value="Équilibré"
            )
            
            language_level = st.select_slider(
                "Niveau de langage",
                options=["Simple", "Standard", "Technique", "Expert"],
                value="Standard"
            )

        with col2:
            st.subheader("Public cible")
            
            target_age = st.select_slider(
                "Âge cible",
                options=["18-25", "25-35", "35-50", "50+", "Tous âges"],
                value="Tous âges"
            )
            
            target_gender = st.radio(
                "Genre cible",
                options=["Homme", "Femme", "Tous"],
                index=2
            )
            
            expertise_level = st.select_slider(
                "Niveau d'expertise",
                options=["Débutant", "Intermédiaire", "Avancé", "Expert", "Tous niveaux"],
                value="Tous niveaux"
            )

        st.subheader("Paramètres avancés")
        col3, col4 = st.columns(2)
        
        with col3:
            temperature = st.slider(
                "Créativité (température)",
                min_value=0.0,
                max_value=1.0,
                value=0.7,
                step=0.1
            )
            
            keywords_per_text = st.number_input(
                "Mots-clés par texte",
                min_value=1,
                max_value=5,
                value=3
            )

        with col4:
            paragraph_style = st.select_slider(
                "Style de paragraphe",
                options=["Très concis", "Concis", "Standard", "Détaillé", "Très détaillé"],
                value="Standard"
            )
            
            title_style = st.select_slider(
                "Style de titre",
                options=["Très court", "Court", "Standard", "Long", "Très long"],
                value="Standard"
            )

    # Stockage des paramètres dans la session
    if 'config' not in st.session_state:
        st.session_state.config = {}
    
    # Mise à jour de la configuration
    st.session_state.config = {
        'target_language': target_language,
        'tone': tone,
        'writing_style': writing_style,
        'language_level': language_level,
        'target_age': target_age,
        'target_gender': target_gender,
        'expertise_level': expertise_level,
        'temperature': temperature,
        'keywords_per_text': keywords_per_text,
        'paragraph_style': paragraph_style,
        'title_style': title_style
    }

    # Utilisation de la configuration stockée
    config = st.session_state.config

    # Upload de fichiers
    uploaded_files = st.file_uploader("Chargez vos fichiers CSV", type=['csv'], accept_multiple_files=True)

    if uploaded_files:
        if st.button("Générer les Descriptions"):
            with tempfile.TemporaryDirectory() as temp_dir:
                processed_files = []
                
                for uploaded_file in uploaded_files:
                    st.write(f"Traitement de {uploaded_file.name}...")
                    processed_df = process_file(uploaded_file, api_key, config)
                    
                    if processed_df is not None:
                        output_path = os.path.join(temp_dir, f"processed_{uploaded_file.name}")
                        processed_df.to_csv(output_path, index=False)
                        processed_files.append((uploaded_file.name, output_path))
                
                if processed_files:
                    if len(processed_files) == 1:
                        with open(processed_files[0][1], 'rb') as f:
                            st.download_button(
                                label="Télécharger le fichier traité",
                                data=f,
                                file_name=f"processed_{processed_files[0][0]}",
                                mime="text/csv"
                            )
                    else:
                        zip_buffer = io.BytesIO()
                        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                            for original_name, processed_path in processed_files:
                                zip_file.write(processed_path, f"processed_{original_name}")
                        
                        st.download_button(
                            label="Télécharger tous les fichiers traités (ZIP)",
                            data=zip_buffer.getvalue(),
                            file_name="processed_files.zip",
                            mime="application/zip"
                        )
    else:
        st.info("Veuillez charger un fichier CSV pour commencer.")

if __name__ == "__main__":
    main()
