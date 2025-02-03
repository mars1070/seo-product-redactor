import streamlit as st
import pandas as pd
import anthropic
import os
from dotenv import load_dotenv
import tempfile
import zipfile
import io

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
    """Génère des descriptions courtes et longues pour un produit."""
    
    # Mapping des langues
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
    
    # Détermination de la langue
    if config['target_language'] == "Auto-détection":
        lang = detect_language(product_name)
    else:
        lang = language_mapping.get(config['target_language'], 'en_us')
    
    # Mapping des noms complets des langues
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
        # Prompt pour la description courte
        short_prompt = f'''Vous êtes un expert en rédaction. Écrivez une description courte de produit.

EXIGENCE CRITIQUE DE LANGUE :
- VOUS DEVEZ ÉCRIRE EN {full_language_names[lang]} UNIQUEMENT
- Langue de sortie forcée : {full_language_names[lang]}
- N'UTILISEZ AUCUNE AUTRE LANGUE

Produit à décrire : {product_name}

Ton : {config['tone']}
Style d'écriture : {config['writing_style']}
Niveau de langage : {config['language_level']}
Âge cible : {config['target_age']}
Genre cible : {config['target_gender']}
Niveau d'expertise : {config['expertise_level']}
Température : {config['temperature']}
Mots-clés par texte : {config['keywords_per_text']}
Style de paragraphe : {config['paragraph_style']}
Style de titre : {config['title_style']}'''

        # Prompt pour la description longue
        long_prompt = f'''Vous êtes un expert en rédaction e-commerce. Créez une description de produit engageante en format HTML qui met en valeur deux avantages spécifiques du produit.

EXIGENCE CRITIQUE DE LANGUE :
- VOUS DEVEZ ÉCRIRE EN {full_language_names[lang]} UNIQUEMENT
- Langue de sortie forcée : {full_language_names[lang]}
- N'UTILISEZ AUCUNE AUTRE LANGUE
- Cela inclut TOUT le texte : titres, paragraphes et tout autre contenu
- Si vous ne pouvez pas écrire en {full_language_names[lang]}, répondez "Langue non supportée"

EXIGENCE CRITIQUE POUR LES PARAGRAPHES :
- Chaque paragraphe DOIT contenir 3 à 4 phrases bien construites
- Le nombre de mots DOIT être entre 80 et 100 mots par paragraphe
- C'est une exigence stricte pour l'optimisation SEO
- Comptez soigneusement vos mots et phrases avant de soumettre

Directives :
1. Structure :
   - Deux titres <h2> : titres descriptifs axés sur des avantages spécifiques (6-10 mots)
   - Deux paragraphes <p> : EXACTEMENT 3-4 phrases chacun, 80-100 mots, développant chaque avantage
   
2. Style d'écriture :
   - Titres descriptifs et engageants (6-10 mots)
   - Incluez l'avantage principal + comment/pourquoi il est important dans chaque titre
   - Exemple de structure de titre : "Résultats de Qualité Professionnelle pour Vos Soins Quotidiens"
   - Chaque paragraphe doit avoir 3-4 phrases complètes et bien structurées
   - Chaque phrase doit exprimer une idée claire

Produit à décrire : {product_name}

Ton : {config['tone']}
Style d'écriture : {config['writing_style']}
Niveau de langage : {config['language_level']}
Âge cible : {config['target_age']}
Genre cible : {config['target_gender']}
Niveau d'expertise : {config['expertise_level']}
Température : {config['temperature']}
Mots-clés par texte : {config['keywords_per_text']}
Style de paragraphe : {config['paragraph_style']}
Style de titre : {config['title_style']}'''

        # Génération de la description courte
        short_response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=300,
            temperature=float(config['temperature']),
            messages=[{"role": "user", "content": short_prompt}]
        )
        short_description = short_response.content[0].text

        # Génération de la description longue
        long_response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1000,
            temperature=float(config['temperature']),
            messages=[{"role": "user", "content": long_prompt}]
        )
        long_description = long_response.content[0].text

        return short_description.strip(), long_description.strip()

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
