import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Hub Stabilità Anziani", layout="centered")

# --- CARICAMENTO DATI LIVE DAL WEB (FASE 1) ---
# Sostituisci questi link d'esempio con i tuoi link di pubblicazione in CSV di Google Fogli
LINK_DATI_PAZIENTE = "INSERISCI_QUI_IL_LINK_CSV_DI_DATI_PAZIENTE"

@st.cache_data(ttl=60) # Aggiorna la cache ogni 60 secondi
def carica_database_live():
    try:
        df = pd.read_csv(LINK_DATI_PAZIENTE)
        return df
    except:
        return None

df_paziente = carica_database_live()

# --- INTERFACCIA APP ---
st.sidebar.title("🚪 Navigazione Portale")
modalita = st.sidebar.radio("Seleziona Area:", ["Screening Gratuito (Paziente)", "Dashboard Clinica (Fisioterapista)"])

# ==============================================================================
# VISIONE PAZIENTE: SCREENING AL SEMINARIO
# ==============================================================================
if modalita == "Screening Gratuito (Paziente)":
    st.title("👵 Test di Autovalutazione della Stabilità")
    st.write("Compila i campi per verificare il tuo livello di sicurezza nelle attività quotidiane.")
    
    with st.form("form_screening"):
        col_ini, col_an = st.columns(2)
        with col_ini:
            iniziali = st.text_input("Le tue Iniziali (es. Mario Rossi -> MR):", max_chars=3).strip().upper()
        with col_an:
            anno = st.number_input("Il tuo Anno di Nascita:", min_value=1920, max_value=2015, value=1950)
            
        id_generato = f"{iniziali}{str(anno)[-2:]}" if iniziali else ""
        if id_generato:
            st.info(f"🔑 Il tuo codice identificativo anonimo è: **{id_generato}**")
            
        st.subheader("Sicurezza nelle ADL (FES-I Ridotta)")
        q1 = st.selectbox("Quanto si sente sicuro/a nell'alzarsi o sedersi da una sedia?", [1,2,3,4], format_func=lambda x: ["", "1 - Molto sicuro", "2 - Un po' sicuro", "3 - Insicuro", "4 - Molto insicuro"][x])
        q2 = st.selectbox("Quanto teme di scivolare o cadere camminando in casa?", [1,2,3,4], format_func=lambda x: ["", "1 - Nessuna paura", "2 - Poca paura", "3 - Moderata paura", "4 - Molta paura"][x])
        
        cadute = st.radio("È caduto/a negli ultimi 12 mesi?", ["No", "Sì, una volta", "Sì, più di una volta"])
        
        st.markdown("*Nota: Questo test è anonimo e tutela la tua privacy secondo il GDPR.*")
        submit = st.form_submit_button("Calcola Risultato")
        
        if submit:
            if not iniziali:
                st.error("⚠️ Inserisci le tue iniziali per generare il codice.")
            else:
                score = q1 + q2
                st.markdown("---")
                if score >= 5 or cadute != "No":
                    st.error(f"🔴 RISCHIO CADUTE AUMENTATO / LIMITAZIONE FUNZIONALE")
                    st.write("Il test evidenzia elementi di ipervigilanza o instabilità. L'esercizio terapeutico specifico può ridurre significativamente il rischio di infortuni.")
                    st.warning(f"💡 **Cosa fare:** Comunica il tuo codice `{id_generato}` al Fisioterapista al termine dell'incontro per impostare un'analisi motoria approfondita.")
                else:
                    st.success("🟢 BUON LIVELLO DI INDIPENDENZA")
                    st.write("Continua a mantenerti attivo per preservare la forza muscolare e la salute articolare!")

# ==============================================================================
# VISIONE FISIOTERAPISTA: ESTRAZIONE REPORT COMPLETO (EX CELLA Colab)
# ==============================================================================
elif modalita == "Dashboard Clinica (Fisioterapista)":
    st.title("🩺 Pannello di Controllo Clinico")
    pin = st.text_input("Inserisci il PIN di sblocco:", type="password")
    
    if pin == "1234": # Il tuo PIN di sicurezza
        st.success("🔓 Accesso autorizzato.")
        
        if df_paziente is not None:
            # Lista di tutti gli ID presenti nel foglio Google per cercarli al volo
            lista_id = df_paziente['ID paziente'].dropna().unique()
            id_ricerca = st.selectbox("Seleziona l'ID del Paziente da valutare:", lista_id)
            
            paz_riga = df_paziente[df_paziente['ID paziente'] == id_ricerca]
            if not paz_riga.empty:
                p = paz_riga.iloc[0].to_dict()
                cols = list(df_paziente.columns)
                
                st.markdown(f"### 📋 Report Anamnestico Remoto per l'ID: **{id_ricerca}**")
                st.write(f"**Età:** {p[cols[4]]} | **Sesso:** {p[cols[5]]}")
                st.write(f"**Contesto abitativo:** {p[cols[6]]}")
                st.write(f"**Dolore iniziale dichiarato (NRS):** {p[cols[10]]}/10")
                
                # Calcolo psicometrico automatico con la logica robusta degli indici
                def media_indici(lista_idx):
                    v = [pd.to_numeric(p[cols[i]], errors='coerce') for i in lista_idx if i < len(cols)]
                    v = [x for x in v if pd.notna(x)]
                    return np.mean(v) if v else 0.0

                st.markdown("#### Indici Psicosociali (Yellow Flags)")
                st.info(f"🧠 Kinesiofobia/Evitamento: **{media_indici([18, 19, 20, 21]):.1f}/10**")
                st.info(f"📉 Paura di cadere percepita: **{media_indici([23, 24]):.1f}/10**")
                
                st.markdown("---")
                st.subheader("🏋️ Inserisci Valutazione Strumentale in Studio")
                # Qui aggiungerai i campi per TUG, 5xSTS e Kg dei muscoli
                st.number_input("Tempo d'esecuzione TUG (secondi):", value=10.0)
                st.number_input("Medio Gluteo DX (Kg):", value=15.0)
                st.button("Salva ed Elabora Scheda Esercizi")
        else:
            st.error("Impossibile connettersi al database Google Fogli. Controlla il link.")
