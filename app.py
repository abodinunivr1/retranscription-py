import streamlit as st
import assemblyai as aai
from datetime import datetime
import os
from pathlib import Path
import json

# Configuration
st.set_page_config(page_title="Transcripteur d'Entretiens", layout="wide")

# Authentification
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if not st.session_state.password_correct:
        st.title("🔐 Authentification")
        password = st.text_input("Entrez le mot de passe", type="password")
        
        if st.button("Se connecter"):
            if password == st.secrets.get("PASSWORD"):
                st.session_state.password_correct = True
                st.rerun()
            else:
                st.error("❌ Mot de passe incorrect")
        st.stop()

check_password()


# Configuration
st.set_page_config(page_title="Transcripteur d'Entretiens", layout="wide")

# Initialiser AssemblyAI
def init_assemblyai(api_key):
    aai.settings.api_key = api_key

# Fonction principale de transcription
def transcrire_audio(file_path, nb_speakers=2):
    try:
        transcriber = aai.Transcriber()
        config = aai.TranscriptionConfig(
            language_code="fr",
            speaker_labels=True,
            speakers_expected=nb_speakers
        )
        transcript = transcriber.transcribe(file_path, config=config)
        
        if transcript.status == aai.TranscriptStatus.error:
            return None, f"Erreur: {transcript.error}"
        
        return transcript, None
    except Exception as e:
        return None, f"Erreur lors de la transcription: {str(e)}"

# Formater la transcription avec diarisation
def formater_transcription(transcript):
    formatted_text = ""
    
    if transcript.utterances:
        for utterance in transcript.utterances:
            speaker = f"Locuteur {utterance.speaker}" if utterance.speaker is not None else "Inconnu"
            formatted_text += f"**{speaker}:** {utterance.text}\n\n"
    else:
        formatted_text = transcript.text
    
    return formatted_text

# Générer rapport structuré
def generer_rapport(transcript, nom_entretien, date_entretien):
    duree_affichage = "Non disponible"
    if hasattr(transcript, 'duration') and transcript.duration is not None:
        duree_min = transcript.duration // 60
        duree_sec = transcript.duration % 60
        duree_affichage = f"{duree_min}m {duree_sec}s"
    
    rapport = f"""# Compte Rendu d'Entretien

**Titre:** {nom_entretien}
**Date:** {date_entretien}
**Durée:** {duree_affichage}

---

## Transcription

"""
    
    if transcript.utterances:
        for utterance in transcript.utterances:
            speaker = f"Locuteur {utterance.speaker}" if utterance.speaker is not None else "Inconnu"
            rapport += f"**{speaker}:** {utterance.text}\n\n"
    else:
        rapport += transcript.text + "\n\n"
    
    if hasattr(transcript, 'words') and transcript.words:
        rapport += "\n---\n## Statistiques\n"
        rapport += f"- Nombre de mots: {len(transcript.words)}\n"
        if hasattr(transcript, 'duration') and transcript.duration is not None:
            rapport += f"- Durée totale: {duree_affichage}\n"
    
    return rapport

# Interface Streamlit
st.title("📝 Transcripteur d'Entretiens")
st.markdown("Application pour transcrire automatiquement vos entretiens en utilisant AssemblyAI")

# Sidebar pour configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    api_key = st.text_input("Clé API AssemblyAI", type="password", help="Obtiens ta clé sur https://www.assemblyai.com/")
    
    if not api_key:
        st.warning("⚠️ Veuillez entrer votre clé API AssemblyAI")
        st.stop()
    
    init_assemblyai(api_key)

# Onglets
tab1, tab2 = st.tabs(["📤 Transcription", "📚 Historique"])

with tab1:
    st.header("Uploader et Transcrire")
    
    col1, col2 = st.columns(2)
    
    with col1:
        uploaded_file = st.file_uploader(
            "Sélectionner un fichier audio",
            type=["mp3", "wav", "m4a", "flac", "ogg"]
        )
    
    with col2:
        nom_entretien = st.text_input("Nom de l'entretien", placeholder="Ex: Entretien Client A")
    
    nb_speakers = st.selectbox(
        "Nombre de locuteurs attendus",
        options=[1, 2, 3, 4, 5],
        index=1,
        help="Sélectionnez le nombre de personnes qui parlent"
    )
    
    if uploaded_file and nom_entretien:
        temp_dir = Path("temp_audio")
        temp_dir.mkdir(exist_ok=True)
        
        temp_file_path = temp_dir / uploaded_file.name
        with open(temp_file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        if st.button("🚀 Lancer la transcription", type="primary"):
            with st.spinner("Transcription en cours... Cela peut prendre quelques minutes"):
                transcript, error = transcrire_audio(str(temp_file_path), nb_speakers)
                
                if error:
                    st.error(error)
                else:
                    st.success("✅ Transcription terminée!")
                    
                    formatted = formater_transcription(transcript)
                    st.subheader("Résultat")
                    st.markdown(formatted)
                    
                    st.subheader("Statistiques")
                    col_stat1, col_stat2, col_stat3 = st.columns(3)
                    
                    with col_stat1:
                        if hasattr(transcript, 'duration') and transcript.duration:
                            duree_min = transcript.duration // 60
                            duree_sec = transcript.duration % 60
                            st.metric("Durée", f"{duree_min}m {duree_sec}s")
                        else:
                            st.metric("Durée", "N/A")
                    
                    with col_stat2:
                        if hasattr(transcript, 'words') and transcript.words:
                            st.metric("Nombre de mots", len(transcript.words))
                        else:
                            st.metric("Nombre de mots", "N/A")
                    
                    with col_stat3:
                        if transcript.utterances:
                            unique_speakers = len(set(u.speaker for u in transcript.utterances if u.speaker is not None))
                            st.metric("Locuteurs détectés", unique_speakers)
                        else:
                            st.metric("Locuteurs détectés", "N/A")
                    
                    date_now = datetime.now().strftime("%d/%m/%Y %H:%M")
                    rapport = generer_rapport(transcript, nom_entretien, date_now)
                    
                    st.subheader("Exporter")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.download_button(
                            label="📄 Télécharger en TXT",
                            data=formatted,
                            file_name=f"{nom_entretien}_{date_now.replace('/', '-').replace(' ', '_')}.txt",
                            mime="text/plain"
                        )
                    
                    with col2:
                        st.download_button(
                            label="📋 Télécharger en Markdown",
                            data=rapport,
                            file_name=f"{nom_entretien}_{date_now.replace('/', '-').replace(' ', '_')}.md",
                            mime="text/markdown"
                        )
                    
                    history_file = Path("transcription_history.json")
                    history = []
                    
                    if history_file.exists():
                        with open(history_file, "r", encoding="utf-8") as f:
                            history = json.load(f)
                    
                    history.append({
                        "nom": nom_entretien,
                        "date": date_now,
                        "duree": transcript.duration if hasattr(transcript, 'duration') else 0,
                        "fichier": uploaded_file.name
                    })
                    
                    with open(history_file, "w", encoding="utf-8") as f:
                        json.dump(history, f, ensure_ascii=False, indent=2)
        
        if temp_file_path.exists():
            os.remove(temp_file_path)
    else:
        st.info("👆 Veuillez uploader un fichier audio et entrer un nom d'entretien")

with tab2:
    st.header("Historique des Transcriptions")
    
    history_file = Path("transcription_history.json")
    
    if history_file.exists():
        with open(history_file, "r", encoding="utf-8") as f:
            history = json.load(f)
        
        if history:
            for entry in reversed(history):
                with st.container(border=True):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.write(f"**{entry['nom']}**")
                    with col2:
                        st.write(f"📅 {entry['date']}")
                    with col3:
                        if entry['duree'] > 0:
                            duree_min = entry['duree'] // 60
                            duree_sec = entry['duree'] % 60
                            st.write(f"⏱️ {duree_min}m {duree_sec}s")
                        else:
                            st.write("⏱️ N/A")
        else:
            st.info("Aucune transcription encore")
    else:
        st.info("Aucune transcription encore") 