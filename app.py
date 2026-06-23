import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import numpy as np
from datetime import datetime

st.set_page_config(page_title="Hub Clinico - Valutazione Anziani", layout="centered")

# ==============================================================================
# CONNESSIOINE DIRETTA E SICURA AL GOOGLE FOGLIO
# ==============================================================================
# L'app cerca automaticamente le credenziali salvate nei "Secrets" di Streamlit
conn = st.connection("gsheets", type=GSheetsConnection)

# Sostituisci questo URL con l'URL del tuo Google Foglio (preso dalla barra degli indirizzi)
URL_FOGLIO = "https://docs.google.com/spreadsheets/d/1qbCAMeOUKI23gq3p8g95JSwESI6-tF7mvUp8Mg0Z4Jk/edit"

@st.cache_data(ttl=10)  # Mantiene i dati in cache per soli 10 secondi per aggiornamenti rapidi
def leggi_dati():
    return conn.read(spreadsheet=URL_FOGLIO, worksheet="Dati_Paziente")

df_paziente = leggi_dati()

# --- BARRA LATERALE PER NAVIGAZIONE ---
st.sidebar.title("🩺 Gestione Studio")
modalita = st.sidebar.radio("Seleziona Interfaccia:", ["Screening Completo (Paziente)", "Pannello Analisi (Fisioterapista)"])

# ==============================================================================
# INTERFACCIA 1: VALUTAZIONE COMPLETA (LATO PAZIENTE / SEMINARIO)
# ==============================================================================
if modalita == "Screening Completo (Paziente)":
    st.title("👵 Modulo di Valutazione del Movimento e del Benessere")
    st.write("Compili tutti i campi sottostanti. I dati verranno elaborati istantaneamente in forma protetta.")
    
    with st.form("form_paziente_totale"):
        st.subheader("📌 Sezione A: Identificazione e Contesto")
        
        col_consenso = st.selectbox(
            "Consenso al trattamento dei dati sanitari:",
            [
                "Ho letto l'informativa e acconsento liberamente al trattamento dei miei dati personali e sanitari per le finalità riabilitative descritte.",
                "Non acconsento."
            ]
        )
        
        col_compilatore = st.selectbox("Chi sta compilando questo modulo?", ["Paziente stesso", "Familiare", "Caregiver / Assistente"])
        
        col_ini, col_an, col_sesso = st.columns(3)
        with col_ini:
            iniziali = st.text_input("Le tue Iniziali (es. Mario Rossi -> MR):", max_chars=3).strip().upper()
        with col_an:
            anno_nascita = st.number_input("Anno di Nascita:", min_value=1920, max_value=2015, value=1950)
        with col_sesso:
            sesso = st.selectbox("Sesso Biologico:", ["Uomo", "Donna"])
            
        situazione_abitativa = st.selectbox(
            "Situazione abitativa attuale:",
            [
                "Vive da solo/a in totale autonomia",
                "Vive con familiari / coniuge",
                "Vive con un assistente continuo o badante"
            ]
        )
        
        # Generazione ID Anonimo Clinico
        id_generato = f"{iniziali}{str(anno_nascita)[-2:]}" if iniziali else ""
        if id_generato:
            st.info(f"🔑 Il tuo Codice Identificativo Personale è: **{id_generato}**")
            
        st.subheader("🩺 Sezione B: Quadro Clinico e Sintomi")
        condizioni_mecc = st.multiselect(
            "Al paziente sono state diagnosticate una o più delle seguenti condizioni meccaniche/strutturali?",
            ["Artrosi Severa", "Osteoporosi", "Protesi d'anca", "Protesi di ginocchio", "Nessuna"]
        )
        condizioni_sist = st.multiselect(
            "Il paziente soffre di una o più delle seguenti patologie sistemiche?",
            ["Ipertensione arteriosa (Pressione alta cronica)", "Diabete", "Cardiopatia", "Nessuna"]
        )
        sintomi_red = st.multiselect(
            "Nelle ultime settimane o negli ultimi giorni, il paziente ha manifestato uno o più dei seguenti sintomi improvvisi?",
            ["Perdita di peso inspiegabile", "Febbre persistente", "Intorpidimento improvviso agli arti", "Nessuno di questi sintomi"]
        )
        
        dolore_nrs = st.slider("In media, nelle ultime 48 ore, che livello di dolore fisico ha avvertito il paziente durante le normali attività quotidiane? (0 = Nessun dolore, 10 = Massimo possibile)", 0, 10, 5)
        farmaci = st.text_input("Indichi brevemente i principali farmaci assunti (es. anticoagulanti, cortisonici, ecc.):", placeholder="cardioaspirina, ecc.")
        
        st.subheader("🧠 Sezione C: Vissuto del Movimento, Umore e Stabilità")
        st.write("Per ciascuna affermazione, indichi quanto si ritrova d'accordo su una scala da 1 (Per nulla d'accordo) a 10 (Completamente d'accordo).")
        
        # Mappatura millimetrica delle 18 domande psicometriche del database
        v1 = st.slider("1. Nelle ultime 2 settimane, quanto spesso è stato infastidito da scarso appetito o eccessiva alimentazione?", 1, 10, 5)
        v2 = st.slider("2. Quanto spesso si sente contento/a e sereno/a con se stesso/a?", 1, 10, 5)
        v3 = st.slider("3. Sente che alcuni pensieri insignificanti le passano per la mente e la infastidiscono?", 1, 10, 5)
        v4 = st.slider("4. Sente di avere un carattere irascibile o di essere una 'testa calda'?", 1, 10, 5)
        v5 = st.slider("5. Quando si arrabbia, le capita di dire cose cattive o di perdere il controllo?", 1, 10, 5)
        v6 = st.slider("6. Quanto la fa sentire furioso/a o a disagio l'essere criticato/a di fronte ad altre persone?", 1, 10, 5)
        v7 = st.slider("7. Non avrei così tanto dolore se non ci fosse qualcosa di potenzialmente pericoloso nel mio corpo", 1, 10, 5)
        v8 = st.slider("8. Quando sente dolore, sente che non riesce a toglierselo dalla testa ed è difficile pensare ad altro", 1, 10, 5)
        v9 = st.slider("9. Quanto crede che l'attività fisica e l'esercizio possano danneggiare la parte del corpo dolorosa?", 1, 10, 5)
        v10 = st.slider("10. Sente di non poter svolgere attività fisica perché teme che possa far peggiorare il suo dolore?", 1, 10, 5)
        v11 = st.slider("11. Sente che le attività quotidiane o la gestione della casa/lavorative sono ormai troppo pesanti e faticose da gestire?", 1, 10, 5)
        v12 = st.slider("12. Quanto si sente spaventato/a, ansioso/a o insicuro/a all'idea di poter scivolare, inciampare o cadere durante la giornata?", 1, 10, 5)
        v13 = st.slider("13. Quando si trova in piedi (fermo o mentre cammina), quanto avverte una sensazione fisica di instabilità o debolezza nelle gambe?", 1, 10, 5)
        v14 = st.slider("14. Quanto si sente sicuro/a di poter condurre uno stile di vita normale e attivo nonostante il dolore?", 1, 10, 5)
        v15 = st.slider("15. Sente che il dolore fisico non è un problema insormontabile nella sua vita quotidiana?", 1, 10, 5)
        v16 = st.slider("16. Sente di riuscire a condurre una vita piena e soddisfacente anche se convive con un dolore cronico?", 1, 10, 5)
        v17 = st.slider("17. Pensa che prima di fare progetti importanti sia assolutamente necessario avere il totale controllo del proprio dolore?", 1, 10, 5)
        v18 = st.slider("18. Quanto si sente sicuro/a di poter portare a termine la sua terapia ed esercizi indipendentemente da come si sente emotivamente?", 1, 10, 5)
        
        submit = st.form_submit_button("Invia Valutazione al Database")
        
        if submit:
            if not iniziali:
                st.error("⚠️ Inserimento bloccato: le Iniziali sono obbligatorie per generare l'ID paziente.")
            elif "Non acconsento" in col_consenso:
                st.error("⚠️ Impossibile salvare i dati senza il consenso al trattamento sanitario.")
            else:
                # Calcolo dell'età dinamica dall'anno di nascita
                eta_calcolata = datetime.now().year - anno_nascita
                
                # Creazione della riga strutturata esattamente come le colonne del tuo foglio Google[cite: 1]
                nuova_riga = pd.DataFrame([{
                    "Informazioni cronologiche": datetime.now().strftime("%d/%m/%Y %H.%M.%S"),
                    "Consenso al trattamento dei dati sanitari:": col_consenso,
                    "ID paziente": id_generato,
                    "Chi sta compilando questo modulo?": col_compilatore,
                    "Età del paziente": eta_calcolata,
                    "Sesso Biologico": sesso,
                    "Situazione abitativa": situazione_abitativa,
                    " Al paziente sono state diagnosticate una o più delle seguenti condizioni meccaniche/strutturali?  ": ", ".join(condizioni_mecc),
                    "Il paziente soffre di una o più delle seguenti patologie sistemiche?\"  ": ", ".join(condizioni_sist),
                    "Nelle ultime settimane o negli ultimi giorni, il paziente ha manifestato uno o più dei seguenti sintomi improvvisi?  ": ", ".join(sintomi_red),
                    "In media, nelle ultime 48 ore, che livello di dolore fisico ha avvertito il paziente durante le normali attività quotidiane?  ": dolore_nrs,
                    "Indichi brevemente i principali farmaci assunti (es. anticoagulanti, cortisonici, beta-bloccanti, ecc.).  ": farmaci,
                    "   Vissuto del movimento, umore e stabilità   [Nelle ultime 2 settimane, quanto spesso è stato infastidito da scarso appetito o eccessiva alimentazione?]": v1,
                    "   Vissuto del movimento, umore e stabilità   [Quanto spesso si sente contento/a e sereno/a con se stesso/a?]": v2,
                    "   Vissuto del movimento, umore e stabilità   [Sente che alcuni pensieri insignificanti le passano per la mente e la infastidiscono?]": v3,
                    "   Vissuto del movimento, umore e stabilità   [Sente di avere un carattere irascibile o di essere una \"testa calda\"?]": v4,
                    "   Vissuto del movimento, umore e stabilità   [Quando si arrabbia, le capita di dire cose cattive o di perdere il controllo]": v5,
                    "   Vissuto del movimento, umore e stabilità   [Quanto la fa sentire furioso/a o a disagio l'essere criticato/a di fronte ad altre persone?]": v6,
                    "   Vissuto del movimento, umore e stabilità   [Non avrei così tanto dolore se non ci fosse qualcosa di potenzialmente pericoloso nel mio corpo]": v7,
                    "   Vissuto del movimento, umore e stabilità   [Quando sente dolore, sente che non riesce a toglierselo dalla testa ed è difficile pensare ad altro]": v8,
                    "   Vissuto del movimento, umore e stabilità   [Quanto crede che l'attività fisica e l'esercizio possano danneggiare la parte del corpo dolorosa?]": v9,
                    "   Vissuto del movimento, umore e stabilità   [Sente di non poter svolgere attività fisica perché teme che possa far peggiorare il suo dolore?]": v10,
                    "   Vissuto del movimento, umore e stabilità   [Sente che le attività quotidiane o la gestione della casa/ lavorative sono ormai troppo pesanti e faticose da gestire?]": v11,
                    "   Vissuto del movimento, umore e stabilità   [Quanto si sente spaventato/a, ansioso/a o insicuro/a all'idea di poter scivolare, inciampare o cadere durante la giornata?]": v12,
                    "   Vissuto del movimento, umore e stabilità   [Quando si trova in piedi (fermo o mentre cammina), quanto avverte una sensazione fisica di instabilità o debolezza nelle gambe?]": v13,
                    "   Vissuto del movimento, umore e stabilità   [Quanto si sente sicuro/a di poter condurre uno stile di vita normale e attivo nonostante il dolore?]": v14,
                    "   Vissuto del movimento, umore e stabilità   [Sente che il dolore fisico non è un problema insormontabile nella sua vita quotidiana?]": v15,
                    "   Vissuto del movimento, umore e stabilità   [Sente di riuscire a condurre una vita piena e soddisfacente anche se convive con un dolore cronico?]": v16,
                    "   Vissuto del movimento, umore e stabilità   [Pensa che prima di fare progetti importanti sia absolutely necessario avere il totale controllo del proprio dolore?]": v17,
                    "   Vissuto del movimento, umore e stabilità   [Quanto si sente sicuro/a di poter portare a termine la sua terapia ed esercizi indipendentemente da come si sente emotivamente?]": v18,
                }])
                
                # Scrittura fisica sul foglio Google tramite accodamento riga
                updated_df = pd.concat([df_paziente, nuova_riga], ignore_index=True)
                conn.update(spreadsheet=URL_FOGLIO, worksheet="Dati_Paziente", data=updated_df)
                
                st.balloons()
                st.success(f"🎉 Valutazione salvata con successo! Il tuo codice è {id_generato}. Comunicalo al Fisioterapista.")

# ==============================================================================
# INTERFACCIA 2: PLOT & ANALISI REALE (LATO FISIOTERAPISTA)
# ==============================================================================
elif modalita == "Pannello Analisi (Fisioterapista)":
    st.title("🩺 Controllo Clinico Bio-Psico-Sociale")
    pin = st.text_input("Inserisci il codice PIN di sblocco:", type="password")
    
    if pin == "1234":
        st.success("🔓 Accesso ai dati personali confermato.")
        
        if df_paziente is not None and not df_paziente.empty:
            lista_id = df_paziente['ID paziente'].dropna().unique()
            id_scelto = st.selectbox("Seleziona il paziente da analizzare:", lista_id)
            
            paz_riga = df_paziente[df_paziente['ID paziente'] == id_scelto]
            if not paz_riga.empty:
                p = paz_riga.iloc[0].to_dict()
                cols = list(df_paziente.columns)
                
                # Layout clinico a schede
                tab1, tab2 = st.tabs(["📋 Anamnesi e Sintomi", "🧠 Indici Psicometrici (Yellow Flags)"])
                
                with tab1:
                    st.markdown(f"### Report Anamnestico per **{id_scelto}**")
                    st.write(f"**Età:** {p[cols[4]]} anni | **Sesso:** {p[cols[5]]}")
                    st.write(f"**Contesto di vita:** {p[cols[6]]}")
                    st.write(f"**Dolore iniziale (NRS):** {p[cols[10]]}/10")
                    st.write(f"**Condizioni Meccaniche:** {p[cols[7]]}")
                    st.write(f"**Patologie Sistemiche:** {p[cols[8]]}")
                    st.text_area("Terapia farmacologica dichiarata:", value=str(p[cols[11]]), disabled=True)
                
                with tab2:
                    st.markdown("### Profilo Psicometrico Avanzato")
                    
                    def calcola_media(indici_colonna):
                        valori = [pd.to_numeric(p[cols[i]], errors='coerce') for i in indici_colonna if i < len(cols)]
                        valori = [x for x in valori if pd.notna(x)]
                        return np.mean(valori) if valori else 0.0
                    
                    # Calcolo degli indici clinici speculari a Colab
                    distress = calcola_media([12, 14, 15, 16, 17])
                    kinesiofobia = calcola_media([18, 19, 20, 21])
                    paura_cadute = calcola_media([23, 24])
                    coping = calcola_media([25, 26, 27, 28, 29])
                    
                    st.metric("Indice Distress / Umore", f"{distress:.1f} / 10")
                    st.metric("Kinesiofobia (Evitamento)", f"{kinesiofobia:.1f} / 10")
                    st.metric("Paura di cadere (Instabilità nelle ADL)", f"{paura_cadute:.1f} / 10")
                    st.metric("Capacità di Coping Attivo (Accettazione)", f"{coping:.1f} / 10")
                    
                    if kinesiofobia > 6.0 or paura_cadute > 6.0:
                        st.warning("⚠️ Paziente ipervigilante: indicata un'esposizione graduale al carico (Graded Exposure).")
        else:
            st.info("Nessun dato trovato nel foglio Google.")
