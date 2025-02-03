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

def get_short_description_prompt(prompt_type, product_name, lang, full_language_names, config):
    """Retourne le prompt approprié selon le type choisi."""
    
    if prompt_type == "Simple Description":
        return f'''En tant que rédacteur marketing expérimenté, rédigez une description concise et logique à mon persona sans le citer, à chaque réponse vous devez changer le style pour [{product_name}]. Analysez les caractéristiques du produit et identifiez les segments de clientèle les plus susceptibles d'être intéressés. La description doit être encapsulée dans une balise <p>, comporter exactement 3 phrases courtes, et mettre en avant les principales caractéristiques et avantages du produit. Adoptez un ton [préciser le ton souhaité, par exemple, professionnel, amical, dynamique] et veillez à optimiser le contenu pour le référencement naturel en intégrant les mots-clés et synonymes. Commencez par un bénéfice ou une objection, ou une douleur en fonction du produit et de la niche. Rédigez uniquement dans la langue suivante : {full_language_names[lang]} et la réponse uniquement en <p> sans commentaires ni rien d'autre.'''
    else:  # "Emoji Benefits"
        return f'''Create 4 benefits with emojis for this product: "{product_name}" in {full_language_names[lang]}.

OUTPUT FORMAT - COPY EXACTLY:
<p>emoji benefit<br>emoji benefit<br>emoji benefit<br>emoji benefit</p>

RULES:
- Use EXACTLY this format with <br> tags
- Each line: 1 emoji + 2-3 words
- Benefits must be specific to {product_name}
- Each emoji must match its benefit

Example format:
<p>🔒 Secure storage<br>💻 Plug-and-play<br>🌐 Global access<br>🤖 Automated updates</p>'''

def validate_emoji_format(text):
    """Valide et corrige le format du texte avec emojis."""
    if not text.startswith("<p>") or not text.endswith("</p>"):
        return None
    
    # Enlever les tags p
    content = text[3:-4]
    
    # Séparer les lignes
    lines = [line.strip() for line in content.split("•") if line.strip()]
    if len(lines) != 4:
        lines = [line.strip() for line in content.split("<br>") if line.strip()]
    if len(lines) != 4:
        return None
        
    # Vérifier que chaque ligne commence par un emoji
    for line in lines:
        if not any(c for c in line[:2] if c.isspace() is False and ord(c) > 255):
            return None
    
    # Reformater avec <br>
    formatted = "<p>" + "<br>".join(lines) + "</p>"
    return formatted

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
        # Get the appropriate short description prompt
        short_prompt = get_short_description_prompt(
            config['short_description_type'],
            product_name,
            lang,
            full_language_names,
            config
        )
        
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
            max_tokens=1000,
            temperature=config['temperature'],
            system="You are a professional e-commerce copywriter specialized in product descriptions.",
            messages=[{"role": "user", "content": short_prompt}]
        )
        short_desc = short_response.content[0].text
        
        # Si c'est une description avec emojis, valider et corriger le format
        if config['short_description_type'] == "Emoji Benefits":
            short_desc = validate_emoji_format(short_desc)
            if not short_desc:
                return None, None
        
        # Génération de la description longue
        long_response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1000,
            temperature=config['temperature'],
            system="You are a professional e-commerce copywriter specialized in product descriptions.",
            messages=[{"role": "user", "content": long_prompt}]
        )
        long_description = long_response.content[0].text

        return short_desc, long_description
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

    # Sidebar pour la configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Section Configuration de base
        st.subheader("Configuration de base")
        
        # Choix de la langue
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
        
        # Type de description courte
        short_description_type = st.radio(
            "Style de description courte",
            ["Emoji Benefits", "Simple Description"],
            help="Choisissez entre une description avec emojis ou une description simple"
        )
        
        # Section Style de rédaction
        st.subheader("Style de rédaction")
        
        tone = st.select_slider(
            "Ton",
            options=["Très formel", "Formel", "Neutre", "Décontracté", "Très décontracté"],
            value="Neutre"
        )
        
        writing_style = st.select_slider(
            "Style d'écriture",
            options=["Très direct", "Direct", "Équilibré", "Descriptif", "Très descriptif"],
            value="Équilibré"
        )
        
        language_level = st.select_slider(
            "Niveau de langage",
            options=["Très simple", "Simple", "Moyen", "Complexe", "Très complexe"],
            value="Moyen"
        )
        
        # Section Audience cible
        st.subheader("Audience cible")
        
        target_age = st.select_slider(
            "Âge cible",
            options=["13-17", "18-24", "25-34", "35-44", "45-54", "55-64", "65+"],
            value="25-34"
        )
        
        target_gender = st.radio(
            "Genre cible",
            ["Tous", "Homme", "Femme"],
            index=0
        )
        
        expertise_level = st.select_slider(
            "Niveau d'expertise",
            options=["Débutant", "Intermédiaire", "Avancé", "Expert"],
            value="Intermédiaire"
        )
        
        # Section Paramètres avancés
        st.subheader("Paramètres avancés")
        
        temperature = st.slider(
            "Température",
            min_value=0.0,
            max_value=1.0,
            value=0.7,
            step=0.1,
            help="Contrôle la créativité (0 = conservateur, 1 = créatif)"
        )
        
        keywords_per_text = st.select_slider(
            "Mots-clés par texte",
            options=["Minimal", "Peu", "Moyen", "Beaucoup", "Maximum"],
            value="Moyen"
        )
        
        paragraph_style = st.select_slider(
            "Style de paragraphe",
            options=["Très court", "Court", "Standard", "Long", "Très long"],
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
        'short_description_type': short_description_type,  # Ajout du type de description courte
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
