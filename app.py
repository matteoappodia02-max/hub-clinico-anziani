import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go

# Configurazione della pagina Streamlit
st.set_page_config(page_title="Hub Clinico & Ricerca - Geriatria", layout="wide")

# ==============================================================================
# GESTIONE DELLO STATO E AUTENTICAZIONE
# ==============================================================================
if "fiso_auth" not in st.session_state:
    st.session_state.fiso_auth = False

# ==============================================================================
# CONNESSIONE DATABASE (GOOGLE SHEETS)
# ==============================================================================
conn = st.connection("gsheets", type=GSheetsConnection)
URL_FOGLIO = "https://docs.google.com/spreadsheets/d/1qbCAMeOUKI23gq3p8g95JSwESI6-tF7mvUp8Mg0Z4Jk/edit"

@st.cache_data(ttl=5)
def leggi_dati_paziente():
    df = conn.read(spreadsheet=URL_FOGLIO, worksheet="Dati_Paziente")
    # Rimuove righe completamente vuote importate dal foglio di calcolo
    return df.dropna(how="all").reset_index(drop=True)

@st.cache_data(ttl=5)
def leggi_dati_valutazioni():
    df = conn.read(spreadsheet=URL_FOGLIO, worksheet="Valutazioni_Studio")
    # Rimuove righe completamente vuote importate dal foglio di calcolo
    return df.dropna(how="all").reset_index(drop=True)

# ==========================================
# 1. ALGORITMO DI GENERAZIONE PROGRESSIONE
# ==========================================
def genera_progressione_senior(dati_paziente, test_funzionali):
    """
    Algoritmo per la generazione di progressioni di allenamento contro resistenza
    per soggetti in età geriatrica, basato sul testo "Science and Practice of Strength Training".
    """
    # ESTRAZIONE DATI
    patologie = dati_paziente.get('patologie', [])
    rischio_caduta = dati_paziente.get('rischio_caduta', 'basso') # basso, medio, alto
    fragilita = dati_paziente.get('fragilita_percepita', 1) # scala 1-10
    distress = dati_paziente.get('distress_emotivo', 1) # scala 1-10
    esperienza = dati_paziente.get('esperienza_allenamento', 'novizio') # novizio, intermedio, avanzato
    
    # INIZIALIZZAZIONE DEL PIANO E REGOLE DI SICUREZZA
    piano_allenamento = {
        "fase_allenamento": "",
        "intensita_forza": "",
        "volume_forza": "",
        "allenamento_potenza_velocita": False,
        "parametri_potenza": {},
        "recupero_tra_sedute": "48-72 ore",
        "note_sicurezza": [],
        "focus_fisioterapista": []
    }

    # GESTIONE PATOLOGIE (Vincoli medici e biomeccanici)
    if "ipertensione" in patologie or "cardiopatia" in patologie:
        piano_allenamento["note_sicurezza"].append("Assolutamente evitare la manovra di Valsalva per non aumentare la pressione intratoracica e arteriosa.")
        piano_allenamento["note_sicurezza"].append("Mantenere ripetizioni > 8 evitando sforzi massimali a cedimento (1-3 RM).")
    
    if "osteoporosi" in patologie:
        piano_allenamento["note_sicurezza"].append("Includere esercizi multi-articolari per lo stimolo assiale (es. step-up, pressa), evitando flessioni spinali sotto carico.")
    
    if "artrosi" in patologie or "dolore_articolare" in patologie:
        piano_allenamento["note_sicurezza"].append("Selezionare range di movimento (ROM) senza dolore. Evitare la decelerazione improvvisa del carico.")

    # GESTIONE FATICABILITA' E DISTRESS
    if fragilita > 7 or distress > 7:
        piano_allenamento["fase_allenamento"] = "Condizionamento di base / Adattamento Anatomico"
        piano_allenamento["note_sicurezza"].append("Livelli di distress e fragilità elevati: ridurre il volume totale del 20-30% per prevenire l'overreaching non funzionale.")
        esperienza = "novizio" # Declassamento protettivo

    # ASSEGNAZIONE PROGRESSIONE DI CARICO (Linee guida NSCA per progressione)
    if esperienza == "novizio":
        piano_allenamento["intensita_forza"] = "50-70% 1RM stimato (o 10-15 RM)"
        piano_allenamento["volume_forza"] = "1-2 serie per gruppo muscolare, 10-15 ripetizioni"
        piano_allenamento["focus_fisioterapista"].append("Focus su apprendimento motorio, coordinazione e controllo posturale.")
        if not piano_allenamento["fase_allenamento"]:
            piano_allenamento["fase_allenamento"] = "Adattamento Anatomico"
        
    elif esperienza == "intermedio":
        piano_allenamento["intensita_forza"] = "60-80% 1RM stimato (o 8-12 RM)"
        piano_allenamento["volume_forza"] = "2-3 serie per gruppo muscolare, 8-12 ripetizioni"
        piano_allenamento["focus_fisioterapista"].append("Iniziare a implementare il principio del sovraccarico progressivo (aumenti del 5-10%).")
        if not piano_allenamento["fase_allenamento"]:
            piano_allenamento["fase_allenamento"] = "Ipertrofia / Forza Generale"
        
    elif esperienza == "avanzato":
        piano_allenamento["intensita_forza"] = "70-85% 1RM stimato (o 6-10 RM)"
        piano_allenamento["volume_forza"] = "3+ serie per gruppo muscolare, 6-10 ripetizioni"
        piano_allenamento["focus_fisioterapista"].append("Introdurre variazioni di carico ondulate per prevenire la monotonia e l'accommodation.")
        if not piano_allenamento["fase_allenamento"]:
            piano_allenamento["fase_allenamento"] = "Forza Massima Periodizzata"

    # MODULO PREVENZIONE CADUTE (Sviluppo della Potenza)
    if rischio_caduta in ["medio", "alto"] and fragilita < 8:
        piano_allenamento["allenamento_potenza_velocita"] = True
        piano_allenamento["focus_fisioterapista"].append("Importanza critica della Rate of Force Development (RFD). Richiedere massima intenzione di accelerazione nella fase concentrica.")
        
        piano_allenamento["parametri_potenza"] = {
            "intensita": "30-60% 1RM (carichi leggeri)",
            "volume": "1-3 serie, 3-6 ripetizioni (non arrivare mai a cedimento)",
            "esecuzione": "Fase eccentrica controllata, fase concentrica eseguita alla massima velocità possibile",
            "recupero_tra_serie": "2-3 minuti per rigenerazione ATP-CP"
        }

    # PERIODIZZAZIONE E FEEDBACK SUI TEST
    deficit_forza_lower = test_funzionali.get("deficit_lower_body", False)
    if deficit_forza_lower:
        piano_allenamento["focus_fisioterapista"].append("Priorità all'ipertrofia e forza degli arti inferiori (squat/pressa/step-up). Gli arti inferiori subiscono un declino di massa più rapido rispetto alla parte superiore.")

    return piano_allenamento

def renderizza_sezione_fisioterapista(df_pazienti, df_valutazioni):
    st.header("🦾 Progressione Senior (Algoritmo NSCA & Zatsiorsky)")
    st.markdown("Monitora lo storico clinico e genera un piano d'allenamento basato sulle prove scientifiche.")
    
    if df_pazienti.empty:
        st.warning("Nessun dato paziente disponibile al momento.")
        return

    # Trova la colonna ID in modo flessibile per evitare KeyError
    colonna_id = None
    for col in ["ID Paziente", "ID_Paziente", "id paziente", "id_paziente"]:
        if col in df_pazienti.columns:
            colonna_id = col
            break
            
    # Fallback sicuro all'indice di colonna 2 (la terza colonna) se non trova il nome esatto
    if colonna_id is None and len(df_pazienti.columns) > 2:
        colonna_id = df_pazienti.columns[2]

    if colonna_id is None:
        st.error("Errore di configurazione: impossibile identificare la colonna ID Paziente.")
        return

    # Estrazione degli ID pazienti validi e puliti
    lista_pazienti = df_pazienti[colonna_id].dropna().astype(str).str.strip().unique().tolist()
    paziente_selezionato = st.selectbox("Seleziona ID Paziente da analizzare", lista_pazienti, key="sb_nsca_prog")
    
    if paciente_selezionato:
        st.markdown("---")
        
        # Filtra lo storico del paziente
        storico_paz = df_pazienti[df_pazienti[colonna_id].astype(str).str.strip() == paziente_selezionato]
        
        # Trova la colonna ID anche nel foglio delle valutazioni
        col_id_val = None
        for col in ["ID Paziente", "ID_Paziente", "id paziente", "id_paziente"]:
            if col in df_valutazioni.columns:
                col_id_val = col
                break
        if col_id_val is None and len(df_valutazioni.columns) > 10:
            col_id_val = df_valutazioni.columns[10]
        
        storico_val = pd.DataFrame()
        if col_id_val is not None and not df_valutazioni.empty:
            storico_val = df_valutazioni[df_valutazioni[col_id_val].astype(str).str.strip() == paziente_selezionato]
        
        st.subheader("📈 Storico Andamento Clinico")
        
        col_grafici_1, col_grafici_2 = st.columns(2)
        
        # Grafico 1: Andamento Paura di Cadere (V12)
        with col_grafici_1:
            col_v12 = None
            for col in storico_paz.columns:
                if "V12" in col or "Paura_Cadere" in col:
                    col_v12 = col
                    break
            if col_v12 is None and len(storico_paz.columns) > 23:
                col_v12 = storico_paz.columns[23] # Indice colonna V12 nel database standard
                
            if col_v12 and not storico_paz.empty:
                try:
                    fig = px.line(storico_paz, x=storico_paz.columns[0], y=col_v12, 
                                  markers=True, title="Andamento Paura di Cadere (V12)")
                    st.plotly_chart(fig, use_container_width=True)
                except:
                    st.info("Impossibile caricare il tracciato della Paura di Cadere.")
            else:
                st.info("Dati insufficienti per il grafico Paura di Cadere.")
                
        # Grafico 2: Andamento Chair Stand Test
        with col_grafici_2:
            col_chair = None
            for col in storico_val.columns:
                if "Chair" in col or "30-Second" in col or "chair stand" in col.lower():
                    col_chair = col
break
            if col_chair is None and len(storico_val.columns) > 4:
                col_chair = storico_val.columns[4] # Indice colonna nel database standard
                
            if col_chair and not storico_val.empty:
                try:
                    fig2 = px.bar(storico_val, x=storico_val.columns[0], y=col_chair, 
                                  title="Andamento 30s Chair Stand Test")
                    st.plotly_chart(fig2, use_container_width=True)
                except:
                    st.info("Impossibile caricare il tracciato del Chair Stand Test.")
            else:
                st.info("Dati insufficienti per il grafico Chair Stand Test.")

        # ---------------------------------------------------------
        # MAPPATURA CLINICA PER L'ALGORITMO
        # ---------------------------------------------------------
        if not storico_paz.empty:
            ultimo_record = storico_paz.iloc[-1]
            
            # Mappatura Patologie
            col_pat_sist = next((col for col in storico_paz.columns if "Sistemiche" in col or "Comorbilità" in col), None)
            col_cond_mecc = next((col for col in storico_paz.columns if "Meccaniche" in col or "Limitazioni" in col), None)
            
            if col_pat_sist is None and len(storico_paz.columns) > 8: col_pat_sist = storico_paz.columns[8]
            if col_cond_mecc is None and len(storico_paz.columns) > 7: col_cond_mecc = storico_paz.columns[7]
            
            pat_sist_val = str(ultimo_record[col_pat_sist]) if col_pat_sist else ""
            cond_mecc_val = str(ultimo_record[col_cond_mecc]) if col_cond_mecc else ""
            
            patologie_raw = (pat_sist_val + " " + cond_mecc_val).lower()
            patologie_attive = [p for p in ["ipertensione", "cardiopatia", "osteoporosi", "artrosi"] if p in patologie_raw]

            # Mappatura indicatori psicocomportamentali
            col_v13 = next((col for col in storico_paz.columns if "V13" in col or "Instabilita" in col), None)
            col_v9 = next((col for col in storico_paz.columns if "V9" in col or "Danno" in col), None)
            col_v10 = next((col for col in storico_paz.columns if "V10" in col or "Evitamento" in col), None)
            col_dolore = next((col for col in storico_paz.columns if "Dolore" in col or "NRS" in col), None)
            
            if col_v13 is None and len(storico_paz.columns) > 24: col_v13 = storico_paz.columns[24]
            if col_v9 is None and len(storico_paz.columns) > 20: col_v9 = storico_paz.columns[20]
            if col_v10 is None and len(storico_paz.columns) > 21: col_v10 = storico_paz.columns[21]
            if col_dolore is None and len(storico_paz.columns) > 10: col_dolore = storico_paz.columns[10]

            paura_cadere = pd.to_numeric(ultimo_record[col_v12], errors='coerce') if col_v12 else 0
            instabilita = pd.to_numeric(ultimo_record[col_v13], errors='coerce') if col_v13 else 0
            paura_danno = pd.to_numeric(ultimo_record[col_v9], errors='coerce') if col_v9 else 0
            evitamento = pd.to_numeric(ultimo_record[col_v10], errors='coerce') if col_v10 else 0
            dolore_nrs = pd.to_numeric(ultimo_record[col_dolore], errors='coerce') if col_dolore else 0

            # Pulizia NaN
            paura_cadere = 0 if pd.isna(paura_cadere) else paura_cadere
            instabilita = 0 if pd.isna(instabilita) else instabilita
            paura_danno = 0 if pd.isna(paura_danno) else paura_danno
            evitamento = 0 if pd.isna(evitamento) else evitamento
            dolore_nrs = 0 if pd.isna(dolore_nrs) else dolore_nrs

            fragilita_max = max(paura_cadere, instabilita)
            distress_max = max(paura_danno, evitamento, dolore_nrs)

            rischio_cad = "basso"
            if fragilita_max >= 7:
                rischio_cad = "alto"
            elif 4 <= fragilita_max < 7:
                rischio_cad = "medio"
dati_algoritmo_paz = {
                "patologie": patologie_attive,
                "rischio_caduta": rischio_cad,
                "fragilita_percepita": fragilita_max,
                "distress_emotivo": distress_max,
                "esperienza_allenamento": "novizio"
            }

            # Verifica deficit di forza arti inferiori
            dati_algoritmo_test = {"deficit_lower_body": False}
            if not storico_val.empty:
                ultimo_test = storico_val.iloc[-1]
                # Quad DX (colonna 16), Quad SN (colonna 17) nel foglio valutazioni standard
                forza_dx = pd.to_numeric(ultimo_test.iloc[16], errors='coerce') if len(ultimo_test) > 16 else 0
                forza_sn = pd.to_numeric(ultimo_test.iloc[17], errors='coerce') if len(ultimo_test) > 17 else 0
                
                forza_dx = 0 if pd.isna(forza_dx) else forza_dx
                forza_sn = 0 if pd.isna(forza_sn) else forza_sn
                
                if (forza_dx > 0 and forza_sn > 0):
                    if (forza_dx < 10 and forza_sn < 10) or abs(forza_dx - forza_sn) > (max(forza_dx, forza_sn) * 0.20):
                        dati_algoritmo_test["deficit_lower_body"] = True

            # Esecuzione dell'algoritmo
            risultato_progressione = genera_progressione_senior(dati_algoritmo_paz, dati_algoritmo_test)

            st.markdown("---")
            st.subheader("🎯 Programmazione del Carico (Zatsiorsky & NSCA)")
            
            col1, col2 = st.columns(2)
            with col1:
                st.info(f"Intensità Forza: {risultato_progressione['intensita_forza']}")
                st.info(f"Volume Forza: {risultato_progressione['volume_forza']}")
            with col2:
                st.warning(f"Fase Allenamento: {risultato_progressione['fase_allenamento']}")
                st.warning(f"Recupero Consigliato: {risultato_progressione['recupero_tra_sedute']}")

            # Modulo Note di Sicurezza
            if risultato_progressione["note_sicurezza"]:
                st.error("⚠️ Note di Sicurezza e Patologie:\n" + 
                         "\n".join([f"- {nota}" for nota in risultato_progressione["note_sicurezza"]]))

            # Modulo Focus Clinico
            if risultato_progressione["focus_fisioterapista"]:
                st.success("🎯 Focus e Priorità Cliniche:\n" + 
                           "\n".join([f"- {focus}" for focus in risultato_progressione["focus_fisioterapista"]]))

            # Modulo Prevenzione Cadute / Potenza
            if risultato_progressione["allenamento_potenza_velocita"]:
                with st.expander("⚡ Protocollo Prevenzione Cadute (Sviluppo Potenza/RFD)", expanded=True):
                    param_pot = risultato_progressione["parametri_potenza"]
                    st.write(f"- Intensità Target: {param_pot['intensita']}")
                    st.write(f"- Volume: {param_pot['volume']}")
                    st.write(f"- Esecuzione: {param_pot['esecuzione']}")
                    st.write(f"- Recupero tra serie: {param_pot['recupero_tra_serie']}")
# ==============================================================================
# COSTANTI SCIENTIFICHE E METRICHE DI RILEVANZA CLINICA (MDC)
# ==============================================================================
MDC_SOGLIE = {
    "SPPB": 1.0,       # Incremento >= 1 punto è clinicamente solido
    "TUG": -2.1,       # Riduzione di almeno 2.1 secondi
    "STS_5X": -2.3,    # Riduzione di almeno 2.3 secondi
    "HANDGRIP": 5.0    # Incremento di almeno 5 kg
}

OPZIONI_FASE = ["Baseline (Prima Valutazione)", "Follow-up 3 Mesi", "Follow-up 6 Mesi", "Follow-up 9 Mesi", "Follow-up 12 Mesi"]

# ==============================================================================
# FUNZIONI DI ELABORAZIONE E CALCOLO CLINICO
# ==============================================================================
def formatta_asse_x(riga):
    """Garantisce l'ordinamento cronologico forzando un indice numerico sull'asse X"""
    try:
        data_completa = str(riga.iloc[0])
        data_pulita = data_completa.split()[0]
        fase_completa = str(riga.iloc[25]).strip()
        
        mappa_fasi = {"Baseline": ("1", "Baseline"), "3": ("2", "3M"), "6": ("3", "6M"), "9": ("4", "9M"), "12": ("5", "12M")}
        num_ordine, fase_breve = "6", fase_completa
        for chiave, (ordine, breve) in mappa_fasi.items():
            if chiave in fase_completa:
                num_ordine, fase_breve = ordine, breve
                break
        return f"{num_ordine}. {data_pulita} ({fase_breve})"
    except:
        return "Data N/D"

def calcola_dimensioni_biopsicosociali(riga_paziente):
    """Raggruppa i quesiti V1-V18 della Sezione C in 4 macro-dimensioni standardizzate (Scala 0-10)"""
    try:
        v = riga_paziente.iloc[12:30].astype(float).values
        kinesiofobia = np.mean([v[9], v[10], v[11], v[16]])      # V10, V11, V12, V17
        accettazione_act = np.mean([v[2], v[6], v[7], v[14]])   # V3, V7, V8, V15
        autoefficacia = np.mean([v[0], v[1], v[8], v[15]])      # V1, V2, V9, V16
        impatto_dolore = np.mean([v[12], v[13], v[17]])          # V13, V14, V18
        return {
            "Kinesiofobia & Paura": round(kinesiofobia, 2),
            "Accettazione (Framework ACT)": round(accettazione_act, 2),
            "Autoefficacia Motoria": round(autoefficacia, 2),
            "Percezione Stato Funzionale": round(impatto_dolore, 2)
        }
    except:
        return {"Kinesiofobia & Paura": 0, "Accettazione (Framework ACT)": 0, "Autoefficacia Motoria": 0, "Percezione Stato Funzionale": 0}

def esegui_screening_geriatrici(riga_valutazione, sesso_paziente):
    """Applica algoritmi decisionali basati su consensi internazionali per intercettare sindromi geriatriche"""
    alert_sarcopenia = "Verde (Rischio Basso)"
    alert_frailty = "Verde (Robusto)"
    alert_cadute = "Verde (Rischio Basso)"
    
    try:
        handgrip_dx = float(riga_valutazione.iloc[22]) if pd.notna(riga_valutazione.iloc[22]) else 0
        handgrip_sn = float(riga_valutazione.iloc[23]) if pd.notna(riga_valutazione.iloc[23]) else 0
        max_handgrip = max(handgrip_dx, handgrip_sn)
        
        tug = float(riga_valutazione.iloc[11]) if pd.notna(riga_valutazione.iloc[11]) else 0
        sts_5x = float(riga_valutazione.iloc[12]) if pd.notna(riga_valutazione.iloc[12]) else 0
        sppb_totale = sum([int(riga_valutazione.iloc[13]), int(riga_valutazione.iloc[14]), int(riga_valutazione.iloc[15])])
        
        # 1. SCREENING SARCOPENIA (Consenso EWGSOP2)
        cutoff_hg = 27 if sesso_paziente == "Uomo" else 16
        if max_handgrip < cutoff_hg and max_handgrip > 0:
            alert_sarcopenia = "Rosso (Sarcopenia Sospetta - Richiesto approfondimento DXA)"
        elif sts_5x > 15:
            alert_sarcopenia = "Giallo (Forza muscolare ridotta alla sedia)"
            
        # 2. SCREENING FRAGILITÀ (Frailty Index semplificato)
        punti_fragilita = 0
        if sppb_totale < 9: punti_fragilita += 1
        if max_handgrip < cutoff_hg and max_handgrip > 0: punti_fragilita += 1
        if sts_5x > 15: punti_fragilita += 1
        
        if punti_fragilita >= 2: alert_frailty = "Rosso (Paziente Fragile)"
        elif punti_fragilita == 1: alert_frailty = "Giallo (Pre-Fragile)"
        
        # 3. RISCHIO CADUTE
        if tug > 12 or sppb_totale < 10:
            alert_cadute = "Rosso (Rischio Cadute Elevato)"
    except:
        pass
        
    return {"sarcopenia": alert_sarcopenia, "frailty": alert_frailty, "cadute": alert_cadute}

# ==============================================================================
# STRUTTURA DI NAVIGAZIONE (SIDEBAR)
# ==============================================================================
st.sidebar.title("🩺 Sistema di Monitoraggio Clinico")
modalita_principale = st.sidebar.radio("Seleziona Area Logica:", [
    "📋 Screening Iniziale (Paziente)", 
    "📊 Pannello Analisi Avanzata (Fisioterapista)", 
    "🔐 Area Personale (Paziente)"
])

# ==============================================================================
# INTERFACCIA 1: INSERIMENTO ACCETTAZIONE E VALUTAZIONE INIZIALE PAZIENTE
# ==============================================================================
if modalita_principale == "📋 Screening Iniziale (Paziente)":
    st.title("👵 Modulo Integrato di Valutazione del Movimento")
    df_paziente = leggi_dati_paziente()
    
    with st.form("form_paziente_totale"):
        st.subheader("📌 Sezione A: Identificazione e Tempistica")
        fase_paziente = st.selectbox("Fase della valutazione attuale:", OPZIONI_FASE)
        col_consenso = st.selectbox("Consenso Informato GDPR:", ["Ho letto l'informativa e acconsento liberamente al trattamento dei miei dati personali e sanitari per le finalità riabilitative descritte.", "Non acconsento."])
        col_compilatore = st.selectbox("Chi sta inserendo i dati?", ["Paziente stesso", "Familiare", "Caregiver / Assistente"])
        col_ini, col_an, col_sesso = st.columns(3)
        with col_ini: iniziali = st.text_input("Iniziali Paziente (Max 3 lettere):", max_chars=3).strip().upper()
        with col_an: anno_nascita = st.number_input("Anno di Nascita:", 1920, 2016, 1950)
        with col_sesso: sesso = st.selectbox("Sesso Biologico:", ["Uomo", "Donna"])
        situazione_abitativa = st.selectbox("Contesto abitativo:", ["Vive da solo/a in totale autonomia", "Vive con familiari / coniuge", "Vive con un assistente continuo o badante"])
        
        st.subheader("🩺 Sezione B: Anamnesi Generale e Sintomi")
        condizioni_mecc = st.multiselect("Limitazioni strutturali/meccaniche note:", ["Artrosi Severa", "Osteoporosi", "Protesi d'anca", "Protesi di ginocchio", "Nessuna"])
        condizioni_sist = st.multiselect("Comorbilità sistemiche:", ["Ipertensione arteriosa", "Diabete", "Cardiopatia", "Nessuna"])
        sintomi_red = st.multiselect("Segnali d'allarme (Red Flags):", ["Perdita di peso inspiegabile", "Febbre persistente", "Intorpidimento improvviso agli arti", "Nessuno di questi sintomi"])
        dolore_nrs = st.slider("Intensità media del dolore nelle ultime 24 ore (NRS 0-10):", 0, 10, 5)
        farmaci = st.text_input("Terapie farmacologiche in corso (separate da virgola):")
        specifiche_cliniche = st.text_area("Note e specificità anamnestiche (opzionale):")

        st.subheader("🧠 Sezione C: Esplorazione del Vissuto e della Dimensione Psicocomportamentale")
        st.caption("Punteggi da 1 (Completamente in disaccordo / Mai) a 10 (Completamente d'accordo / Sempre)")
        
        v1 = st.slider("1. Nelle ultime 2 settimane mi sono sentito/a energico/a e vitale", 1, 10, 5)
        v2 = st.slider("2. Quanto spesso si sente contento/a della propria routine quotidiana?", 1, 10, 5)
        v3 = st.slider("3. Sento che alcuni pensieri o preoccupazioni bloccano le mie azioni", 1, 10, 5)
        v4 = st.slider("4. Sente di avere un carattere resiliente di fronte alle difficoltà fisiche?", 1, 10, 5)
        v5 = st.slider("5. When mi arrabbio o mi spavento, fatico a calmarmi fisicamente", 1, 10, 5)
        v6 = st.slider("6. Quanto la fa sentire furioso/a l'idea di aver perso parte della sua mobilità?", 1, 10, 5)
        v7 = st.slider("7. Non avrei così tanto dolore se potessi controllare la mia mente", 1, 10, 5)
        v8 = st.slider("8. Quando si sente dolore, interrompe immediatamente qualsiasi attività?", 1, 10, 5)
        v9 = st.slider("9. Quanto crede che l'attività fisica sia sicuro ed efficace per la sua salute?", 1, 10, 5)
        v10 = st.slider("10. Sente di non poter svolgere i compiti domestici per paura di subire lesioni?", 1, 10, 5)
        v11 = st.slider("11. Sente che le attività quotidiane aumentano il rischio di usura articolare?", 1, 10, 5)
        v12 = st.slider("12. Quanto si sente spaventato/a all'idea di perdere l'equilibrio e cadere?", 1, 10, 5)
        v13 = st.slider("13. Quando si trova in piedi, percepisce instabilità o debolezza?", 1, 10, 5)
        v14 = st.slider("14. Quanto si sente sicuro/a nel salire e scendere le scale in autonomia?", 1, 10, 5)
        v15 = st.slider("15. Sente che il dolore fisico definisce interamente la sua identità attuale?", 1, 10, 5)
        v16 = st.slider("16. Sente di riuscire a condurre una vita densa di significato nonostante i sintomi?", 1, 10, 5)
        v17 = st.slider("17. Pensa che prima di fare progetti sia obbligatorio eliminare del tutto il dolore?", 1, 10, 5)
        v18 = st.slider("18. Quanto si sente sicuro/a nell'alzarsi da una sedia senza usare le braccia?", 1, 10, 5)

        submit_paziente = st.form_submit_button("Invia ed Archivia Screening")
        
        if submit_paziente:
            eta = datetime.now().year - anno_nascita
            id_gen = f"{iniziali}{str(anno_nascita)[-2:]}"
            riga_valori = [
                datetime.now().strftime("%d/%m/%Y %H.%M.%S"), col_consenso, id_gen, col_compilatore, eta, sesso, situazione_abitativa,
                ", ".join(condizioni_mecc), ", ".join(condizioni_sist), ", ".join(sintomi_red), dolore_nrs, farmaci,
                v1, v2, v3, v4, v5, v6, v7, v8, v9, v10, v11, v12, v13, v14, v15, v16, v17, v18, specifiche_cliniche, fase_paziente
            ]
            try:
                nuovo_df = pd.concat([df_paziente, pd.DataFrame([riga_valori], columns=df_paziente.columns)], ignore_index=True)
                conn.update(spreadsheet=URL_FOGLIO, worksheet="Dati_Paziente", data=nuovo_df)
                st.success(f"Screening salvato correttamente per l'ID univoco: {id_gen} ({fase_paziente})")
                st.cache_data.clear()
            except Exception as e:
                st.error(f"Errore di archiviazione: {e}")

# ==============================================================================
# INTERFACCIA 2: INTERFACCIA AVANZATA DEL FISIOTERAPISTA / RICERCATORE
# ==============================================================================
elif modalita_principale == "📊 Pannello Analisi Avanzata (Fisioterapista)":
    if not st.session_state.fiso_auth:
        st.title("🔒 Controllo Accesso Professionisti")
        pin = st.text_input("Inserisci credenziale PIN Clinico:", type="password")
        if st.button("Autentica"):
            if pin == "1234":
                st.session_state.fiso_auth = True
                st.rerun()
            else:
                st.error("PIN non valido.")
        st.stop()

    if st.sidebar.button("🚪 Blocca Sessione Clinica"):
        st.session_state.fiso_auth = False
        st.rerun()
st.title("👨‍⚕️ Dashboard Clinica Avanzata & Data Management")
    
    sub_menu = st.radio("Seleziona Ambito Operativo:", [
        "🦾 Progressione Senior (NSCA)",
        "📝 Registrazione Nuovi Test", 
        "📈 Analisi Longitudinale & Grafici", 
        "🧠 Analisi Multidimensionale (BPS)", 
        "🧫 Clinical Decision Support & Screening", 
        "💾 Export & Data Pipeline per la Ricerca"
    ], horizontal=True)
    st.markdown("---")

    df_paziente = leggi_dati_paziente()
    df_valutazioni = leggi_dati_valutazioni()

    # Pulizia preventiva per ID Paziente (più sicura usando il nome colonna o l'indice 2)
    if not df_paziente.empty:
        col_id_paz = "ID Paziente" if "ID Paziente" in df_paziente.columns else df_paziente.columns[2]
        lista_pazienti = df_paziente[col_id_paz].dropna().astype(str).str.strip().unique().tolist()
    else:
        lista_pazienti = []

    # ==============================================================================
    # GESTIONE DELLE SOTTO-PAGINE (STRUTTURA PIATTA)
    # ==============================================================================

    # --- SOTTO-PAGINA 1: ALGORITMO DI PROGRESSIONE ---
    if sub_menu == "🦾 Progressione Senior (NSCA)":
        if not df_paziente.empty:
            renderizza_sezione_fisioterapista(df_paziente, df_valutazioni)
        else:
            st.warning("Dati non disponibili. Verifica la connessione al foglio Google.")

    # --- SOTTO-PAGINA 2: REGISTRAZIONE NUOVI TEST CLINICI ---
    elif sub_menu == "📝 Registrazione Nuovi Test":
        st.subheader("Inserimento Valutazione Funzionale Obiettiva")
        
        if not lista_pazienti:
            st.warning("Nessun paziente registrato.")
        else:
            paz_scelto = st.selectbox("Seleziona ID Paziente target:", lista_pazienti, key="sb_registrazione")
            
            fc_max_tanaka = None
            col_id_temp = "ID Paziente" if "ID Paziente" in df_paziente.columns else df_paziente.columns[2]
            storico_paz = df_paziente[df_paziente[col_id_temp].astype(str).str.strip() == paz_scelto]
            if not storico_paz.empty:
                try:
                    sesso_paz = storico_paz.iloc[0, 5]
                    eta_paz = int(storico_paz.iloc[0, 4])
                    fc_max_tanaka = round(208 - (0.7 * eta_paz), 1)
                except:
                    st.warning("Impossibile calcolare FC Max: verifica data nascita nell'anagrafica.")

            with st.form("form_fiso_valutazione"):
                fase_test = st.selectbox("Fase temporale della misurazione:", OPZIONI_FASE)
                
                st.markdown("##### 🫀 Parametri Emodinamici a Riposo")
                col_em1, col_em2, col_em3 = st.columns(3)
                with col_em1: pas = st.number_input("PAS (Pressione Sistolica a riposo - mmHg)", 50, 250, value=None)
                with col_em2: fc_rip = st.number_input("FC (Frequenza Cardiaca a riposo - bpm)", 30, 200, value=None)
                with col_em3: sat_rip = st.number_input("SatO2 a riposo (%)", 50, 100, value=None)

                st.markdown("##### 🏃 Test Funzionali Standardizzati e Risposte Emodinamiche")
                c_f1, c_f2, c_f3 = st.columns(3)
                with c_f1: chair_30 = st.number_input("30-Sec Chair Stand Test (rep)", value=None, step=1)
                with c_f2: step_30 = st.number_input("30-Sec Step Test (rep)", value=None, step=1)
                with c_f3: fc_post = st.number_input("FC immediata Post-Test (bpm)", value=None)
                
                c_f4, c_f5, c_f6 = st.columns(3)
                with c_f4: tug = st.number_input("Timed Up & Go - TUG (secondi)", value=None, format="%.2f")
                with c_f5: sts_5x = st.number_input("5 Times Chair Stand - 5xSTS (secondi)", value=None, format="%.2f")
                with c_f6: sat_post = st.number_input("Saturazione O2 post test (%)", 50, 100, value=None)
                
                tempo_rec = st.number_input("Tempo di recupero (minuti)", value=None, step=1)
st.markdown("##### 📊 Sotto-punteggi Batteria SPPB")
                c_s1, c_s2, c_s3 = st.columns(3)
                with c_s1: sppb_eq = st.number_input("Punteggio Equilibrio (0-4)", 0, 4, value=None)
                with c_s2: sppb_cam = st.number_input("Punteggio Cammino 4m (0-4)", 0, 4, value=None)
                with c_s3: sppb_ch = st.number_input("Punteggio Chair Stand (0-4)", 0, 4, value=None)

                st.markdown("##### 🏋️ Dinamometria di Forza ad Alta Precisione (Kg)")
                c_d1, c_d2 = st.columns(2)
                with c_d1:
                    q_dx = st.number_input("Forza Estensori Ginocchio (Quadricipite) DX", value=None, step=0.5)
                    g_dx = st.number_input("Forza Estensori Anca (Gluteo) DX", value=None, step=0.5)
                    p_dx = st.number_input("Forza Flessori Anca (Iliopsoas) DX", value=None, step=0.5)
                    h_dx = st.number_input("Handgrip Strength DX", value=None, step=0.5)
                with c_d2:
                    q_sn = st.number_input("Forza Estensori Ginocchio (Quadricipite) SN", value=None, step=0.5)
                    g_sn = st.number_input("Forza Estensori Anca (Gluteo) SN", value=None, step=0.5)
                    p_sn = st.number_input("Forza Flessori Anca (Iliopsoas) SN", value=None, step=0.5)
                    h_sn = st.number_input("Handgrip Strength SN", value=None, step=0.5)

                salva_test = st.form_submit_button("💾 Salva Record nel Database")

            if salva_test:
                riga_val_out = [
                    datetime.now().strftime("%d/%m/%Y %H.%M.%S"), pas, fc_rip, sat_rip, chair_30, step_30, fc_post, 
                    sat_post, tempo_rec, "", 
                    paz_scelto, tug, sts_5x, sppb_eq, sppb_cam, sppb_ch, q_dx, q_sn, g_dx, g_sn, p_dx, p_sn, h_dx, h_sn, fc_max_tanaka, fase_test
                ]
                try:
                    df_aggiornato = pd.concat([df_valutazioni, pd.DataFrame([riga_val_out], columns=df_valutazioni.columns)], ignore_index=True)
                    conn.update(spreadsheet=URL_FOGLIO, worksheet="Valutazioni_Studio", data=df_aggiornato)
                    st.success("Test clinici memorizzati correttamente associando i dati ai rispettivi canali H, I, J.")
                    st.cache_data.clear()
                except Exception as e:
                    st.error(f"Errore nel salvataggio: {e}")

    # --- SOTTO-PAGINA 3: ANALISI LONGITUDINALE ---
    elif sub_menu == "📈 Analisi Longitudinale & Grafici":
        st.subheader("Evoluzione Temporale e Verifica della Significatività Clinica (MDC)")
        
        if not lista_pazienti:
            st.warning("Nessun paziente registrato.")
        else:
            paz_scelto = st.selectbox("Seleziona Paciente da esaminare:", lista_pazienti, key="sb_longitudinale")
            
            df_val_clean = df_valutazioni.dropna(subset=[df_valutazioni.columns[10], df_valutazioni.columns[25]])
            storico_val = df_val_clean[df_val_clean.iloc[:, 10].astype(str).str.strip() == paz_scelto].copy()
            
            if not storico_val.empty and len(storico_val) > 0:
                ordine_cronologico = {f: i for i, f in enumerate(OPZIONI_FASE)}
                storico_val["Ordine"] = storico_val.iloc[:, 25].astype(str).str.strip().map(ordine_cronologico).fillna(99)
                storico_val = storico_val.sort_values("Ordine", ascending=True)
                storico_val["Asse_X"] = storico_val.apply(formatta_asse_x, axis=1)
                
                val_baseline = storico_val.iloc[0]
                val_attuale = storico_val.iloc[-1]
                
                st.markdown("#### Verifiche del Cambiamento Clinico Rispetto alla Baseline")
                c_m1, c_m2, c_m3 = st.columns(3)
sppb_base = sum([int(val_baseline.iloc[13]) if pd.notna(val_baseline.iloc[13]) else 0, int(val_baseline.iloc[14]) if pd.notna(val_baseline.iloc[14]) else 0, int(val_baseline.iloc[15]) if pd.notna(val_baseline.iloc[15]) else 0])
                sppb_att = sum([int(val_attuale.iloc[13]) if pd.notna(val_attuale.iloc[13]) else 0, int(val_attuale.iloc[14]) if pd.notna(val_attuale.iloc[14]) else 0, int(val_attuale.iloc[15]) if pd.notna(val_attuale.iloc[15]) else 0])
                delta_sppb = sppb_att - sppb_base
                with c_m1:
                    stato_sppb = "✅ Significativo" if delta_sppb >= MDC_SOGLIE["SPPB"] else "❌ Sotto soglia MDC"
                    st.metric(label="Delta Batteria SPPB (Target: +1)", value=f"{delta_sppb} pt", delta=f"{stato_sppb}")
                
                tug_base = float(val_baseline.iloc[11]) if pd.notna(val_baseline.iloc[11]) else 0
                tug_att = float(val_attuale.iloc[11]) if pd.notna(val_attuale.iloc[11]) else 0
                delta_tug = round(tug_att - tug_base, 2)
                with c_m2:
                    stato_tug = "✅ Significativo" if delta_tug <= MDC_SOGLIE["TUG"] else "❌ Sotto soglia MDC"
                    st.metric(label="Delta TUG Test (Target: -2.1s)", value=f"{delta_tug} s", delta=f"{stato_tug}", delta_color="inverse")
                    
                sts_base = float(val_baseline.iloc[12]) if pd.notna(val_baseline.iloc[12]) else 0
                sts_att = float(val_attuale.iloc[12]) if pd.notna(val_attuale.iloc[12]) else 0
                delta_sts = round(sts_att - sts_base, 2)
                with c_m3:
                    stato_sts = "✅ Significativo" if delta_sts <= MDC_SOGLIE["STS_5X"] else "❌ Sotto soglia MDC"
                    st.metric(label="Delta 5xSTS (Target: -2.3s)", value=f"{delta_sts} s", delta=f"{stato_sts}", delta_color="inverse")

                tab_funz, tab_forza, tab_emo = st.tabs(["Performance Motorie", "Dinamometria di Forza per Distretti", "Capacità Emodinamiche & Recupero"])
                
                with tab_funz:
                    fig_funz = go.Figure()
                    fig_funz.add_trace(go.Scatter(x=storico_val["Asse_X"], y=storico_val.iloc[:, 11], name="Timed Up & Go (TUG)", mode='lines+markers', line=dict(width=3)))
                    fig_funz.add_trace(go.Scatter(x=storico_val["Asse_X"], y=storico_val.iloc[:, 12], name="Test 5xSTS", mode='lines+markers', line=dict(width=3)))
                    fig_funz.update_layout(title="Evoluzione Test Funzionali Cronometrati (Secondi)", xaxis_title="Timeline Valutazioni (Inizio ➔ Successive)", yaxis_title="Tempo (s)", legend_orientation="h")
                    st.plotly_chart(fig_funz, use_container_width=True)
                
                with tab_forza:
                    fig_forza = go.Figure()
                    fig_forza.add_trace(go.Scatter(x=storico_val["Asse_X"], y=storico_val.iloc[:, 16], name="Quadricipite DX", mode='lines+markers'))
                    fig_forza.add_trace(go.Scatter(x=storico_val["Asse_X"], y=storico_val.iloc[:, 17], name="Quadricipite SN", mode='lines+markers'))
                    fig_forza.add_trace(go.Scatter(x=storico_val["Asse_X"], y=storico_val.iloc[:, 18], name="Gluteo DX", mode='lines+markers', line=dict(dash='dash')))
                    fig_forza.add_trace(go.Scatter(x=storico_val["Asse_X"], y=storico_val.iloc[:, 19], name="Gluteo SN", mode='lines+markers', line=dict(dash='dash')))
                    fig_forza.add_trace(go.Scatter(x=storico_val["Asse_X"], y=storico_val.iloc[:, 20], name="Iliopsoas DX", mode='lines+markers', line=dict(dash='dot')))
                    fig_forza.add_trace(go.Scatter(x=storico_val["Asse_X"], y=storico_val.iloc[:, 21], name="Iliopsoas SN", mode='lines+markers', line=dict(dash='dot')))
fig_forza.add_trace(go.Scatter(x=storico_val["Asse_X"], y=storico_val.iloc[:, 22], name="Handgrip DX", mode='lines+markers', line=dict(width=3)))
                    fig_forza.add_trace(go.Scatter(x=storico_val["Asse_X"], y=storico_val.iloc[:, 23], name="Handgrip SN", mode='lines+markers', line=dict(width=3)))
                    fig_forza.update_layout(title="Evoluzione della Forza Muscolare Massima per Distretto", xaxis_title="Timeline Valutazioni (Inizio ➔ Successive)", yaxis_title="Forza Espressa (Kg)", legend_orientation="h")
                    st.plotly_chart(fig_forza, use_container_width=True)
                    
                with tab_emo:
                    fig_emo = go.Figure()
                    fig_emo.add_trace(go.Scatter(x=storico_val["Asse_X"], y=storico_val.iloc[:, 1], name="PAS Riposo (mmHg)", mode='lines+markers'))
                    fig_emo.add_trace(go.Scatter(x=storico_val["Asse_X"], y=storico_val.iloc[:, 2], name="FC Riposo (bpm)", mode='lines+markers'))
                    fig_emo.add_trace(go.Scatter(x=storico_val["Asse_X"], y=storico_val.iloc[:, 6], name="FC Immediata Post-Test (bpm)", mode='lines+markers', line=dict(width=3)))
                    fig_emo.add_trace(go.Scatter(x=storico_val["Asse_X"], y=storico_val.iloc[:, 3], name="SatO2 Riposo (%)", mode='lines+markers'))
                    fig_emo.add_trace(go.Scatter(x=storico_val["Asse_X"], y=storico_val.iloc[:, 7], name="SatO2 Post-Test (%)", mode='lines+markers', line=dict(width=3)))
                    fig_emo.add_trace(go.Bar(x=storico_val["Asse_X"], y=storico_val.iloc[:, 8], name="Tempo di recupero (min)", opacity=0.4))
                    fig_emo.update_layout(title="Adattamento Emodinamico e Tolleranza al Carico", xaxis_title="Timeline Valutazioni (Inizio ➔ Successive)", yaxis_title="Valori metrici", legend_orientation="h")
                    st.plotly_chart(fig_emo, use_container_width=True)
            else:
                st.info("Dati insufficienti per generare analisi longitudinali per questo paziente.")

    # --- SOTTO-PAGINA 4: BPS ---
    elif sub_menu == "🧠 Analisi Multidimensionale (BPS)":
        st.subheader("Profilo Psicocomportamentale e Vissuto del Paziente")
        
        if not lista_pazienti:
            st.warning("Nessun paziente registrato.")
        else:
            paz_scelto = st.selectbox("Seleziona ID Paziente:", lista_pazienti, key="sb_bps")
            
            col_id_temp = "ID Paziente" if "ID Paziente" in df_paziente.columns else df_paziente.columns[2]
            storico_paz = df_paziente[df_paziente[col_id_temp].astype(str).str.strip() == paz_scelto].copy()
            if not storico_paz.empty:
                fasi_disponibili = storico_paz.iloc[:, 31].dropna().astype(str).str.strip().unique().tolist()
                fasi_disponibili = sorted(fasi_disponibili, key=lambda x: next((i for i, opt in enumerate(OPZIONI_FASE) if x in opt), 99))
                
                if not fasi_disponibili:
                    st.warning("Nessuna fase di screening valida trovata per questo paziente.")
                else:
                    fase_scelta = st.selectbox("Seleziona fase di screening da visualizzare:", fasi_disponibili, key="sb_fase_bps")
                    sub_df = storico_paz[storico_paz.iloc[:, 31].astype(str).str.strip() == fase_scelta]
                    
                    if sub_df.empty:
                        st.error("Errore nel recupero della riga selezionata.")
                    else:
                        riga_mirata = sub_df.iloc[0]
                        dimensioni = calcola_dimensioni_biopsicosociali(riga_mirata)
                        
                        categorie = list(dimensioni.keys())
                        valori = list(dimensioni.values())
valori += valori[:1]
                        categorie += categorie[:1]
                        
                        fig = go.Figure()
                        fig.add_trace(go.Scatterpolar(
                            r=valori,
                            theta=categorie,
                            fill='toself',
                            name=fase_scelta,
                            line_color="#1f77b4"
                        ))
                        fig.update_layout(
                            polar=dict(radialaxis=dict(visible=True, range=[0, 10])),
                            showlegend=True,
                            title=f"Mappatura Biopsicosociale - ID {paz_scelto} ({fase_scelta})"
                        )
                        st.plotly_chart(fig, use_container_width=True)
                        
                        st.markdown("##### 📊 Punteggi Analitici delle Dimensioni (Scala 0-10):")
                        c_b1, c_b2, c_b3, c_b4 = st.columns(4)
                        with c_b1: st.metric("Kinesiofobia", f"{dimensioni['Kinesiofobia & Paura']}/10")
                        with c_b2: st.metric("Accettazione ACT", f"{dimensioni['Accettazione (Framework ACT)']}/10")
                        with c_b3: st.metric("Autoefficacia Motoria", f"{dimensioni['Autoefficacia Motoria']}/10")
                        with c_b4: st.metric("Percezione Funzionale", f"{dimensioni['Percezione Stato Funzionale']}/10")

                        st.markdown("##### 🩺 Interpretazione Clinica del Profilo:")
                        mostrato_alert = False
                        if dimensioni["Kinesiofobia & Paura"] > 6:
                            st.warning("⚠️ Livello elevato di Kinesiofobia: Il paziente manifesta forti barriere cognitive al movimento. Priorità all'educazione neuroscientifica del dolore (PNE) e ad una progressione di carico altamente graduale (Graded Exposure).")
                            mostrato_alert = True
                        if dimensioni["Accettazione (Framework ACT)"] < 4:
                            st.info("💡 Bassa Accettazione Psicologica: Sincronizzare l'allenamento con obiettivi di valore personali del paziente, integrando strategie di mindfulness e defusione per svincolare l'azione motoria dalla presenza del sintomo.")
                            mostrato_alert = True
                            
                        if not mostrato_alert:
                            st.success("✅ Profilo Biopsicosociale Bilanciato: I punteggi attuali indicano l'assenza di barriere psicocomportamentali critiche o livelli di allarme. Il paziente mostra un'adeguata predisposizione emotiva al movimento. Continuare con la pianificazione riabilitativa standard basata sulle necessità fisico-funzionali.")

    # --- SOTTO-PAGINA 5: CDS ---
    elif sub_menu == "🧫 Clinical Decision Support & Screening":
        st.subheader("Sistemi di Supporto Decisionale Clinico basati su Linee Guida")
        
        if not lista_pazienti:
            st.warning("Nessun paziente registrato.")
        else:
            paz_scelto = st.selectbox("Seleziona Paziente:", lista_pazienti, key="sb_cds")
            
            col_id_temp = "ID Paziente" if "ID Paziente" in df_paziente.columns else df_paziente.columns[2]
            storico_paz = df_paziente[df_paziente[col_id_temp].astype(str).str.strip() == paz_scelto]
            df_val_clean = df_valutazioni.dropna(subset=[df_valutazioni.columns[10]])
            storico_val = df_val_clean[df_val_clean.iloc[:, 10].astype(str).str.strip() == paz_scelto]
            
            if not storico_paz.empty and not storico_val.empty:
                sesso_paz = storico_paz.iloc[0, 5]
                riga_ultima_val = storico_val.iloc[-1]
esiti = esegui_screening_geriatrici(riga_ultima_val, sesso_paz)
                
                st.markdown("#### Stato delle Sindromi Geriatriche Intercettate")
                col_e1, col_e2, col_e3 = st.columns(3)
                with col_e1: st.error(f"Sarcopenia (EWGSOP2): \n\n {esiti['sarcopenia']}")
                with col_e2: st.warning(f"Fenotipo Fragilità (Frailty): \n\n {esiti['frailty']}")
                with col_e3: st.info(f"Rischio Cadute: \n\n {esiti['cadute']}")
                
                st.markdown("---")
                st.markdown("#### 📚 Suggerimenti per la Decisione Clinica (Evidence-Based Medicine)")
                sppb_punteggio = sum([int(riga_ultima_val.iloc[13]) if pd.notna(riga_ultima_val.iloc[13]) else 0, int(riga_ultima_val.iloc[14]) if pd.notna(riga_ultima_val.iloc[14]) else 0, int(riga_ultima_val.iloc[15]) if pd.notna(riga_ultima_val.iloc[15]) else 0])
                
                if sppb_punteggio < 7:
                    st.markdown("> ⚠️ LIMITAZIONE FUNZIONALE GRAVE (SPPB < 7): Le linee guida raccomandano l'impostazione immediata di un programma multicomponente focalizzato sulla sicurezza. Priorità assoluta ad esercizi di stabilità postulare e controllo dell'equilibrio in ambiente protetto, affiancati da rinforzo progressivo degli estensori di ginocchio sub-massimale.")
                elif 7 <= sppb_punteggio <= 9:
                    st.markdown("> 💡 LIMITAZIONE MODERATA (SPPB 7-9): Indicazione clinica per allenamento di forza progressivo a medio-alta intensità (60-70% 1RM o RPE 7/10 sulla scala Borg). Integrare percorsi di cammino a velocità variabile ed ostacoli per stimolare la riserva motoria.")
                else:
                    st.markdown("> ✅ BUONA CAPACITÀ FUNZIONALE (SPPB >= 10): Focus sul mantenimento e sulla prevenzione primaria. È possibile inserire esercizi di potenza ad alta velocità esecutiva (Power Training) e compiti complessi a doppio compito (Dual-Task) per ottimizzare la resilienza neuro-motoria.")
            else:
                st.info("Necessari sia i dati anagrafici che i test funzionali per generare gli alert.")

    # --- SOTTO-PAGINA 6: EXPORT ---
    elif sub_menu == "💾 Export & Data Pipeline per la Ricerca":
        st.subheader("Estrazione e Anonimizzazione Dataset (Conformità GDPR)")
        st.write("Configura il formato del file di esportazione pronto per l'importazione in R, Python, SPSS o Jamovi.")
        
        formato_export = st.radio("Seleziona formato strutturale:", ["Formato LONG (Una riga per ogni singola sessione)", "Formato WIDE (Una riga per paziente con follow-up affiancati)"])
        
        if st.button("Genera Pipeline Dati Anonimizzati"):
            df_paz_clean = df_paziente.copy()
            df_val_clean = df_valutazioni.copy()
            
            if "Note" in df_paz_clean.columns: df_paz_clean = df_paz_clean.drop(columns=["Note"])
            
            df_ricerca_long = pd.merge(df_val_clean, df_paz_clean.iloc[:, [2, 4, 5, 6, 7, 8]], left_on=df_val_clean.columns[10], right_on=df_paz_clean.columns[2], how="inner")
            df_ricerca_long.rename(columns={df_ricerca_long.columns[10]: "ID_Paziente_Anonimo"}, inplace=True)
            
            if formato_export == "Formato LONG (Una riga per ogni singola sessione)":
                csv_data = df_ricerca_long.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Scarica Dataset LONG .CSV", data=csv_data, file_name="dataset_ricerca_geriatrica_LONG.csv", mime="text/csv")
                st.dataframe(df_ricerca_long.head())
            else:
                try:
                    colonna_fase = df_ricerca_long.columns[25]
                    # Rimuove duplicati per evitare errori nel formato WIDE
df_ricerca_long_pulito = df_ricerca_long.drop_duplicates(subset=["ID_Paziente_Anonimo", colonna_fase], keep="last")
                    
                    df_wide = df_ricerca_long_pulito.pivot(index="ID_Paziente_Anonimo", columns=colonna_fase)
                    df_wide.columns = [f"{col[0]}_{col[1]}" for col in df_wide.columns]
                    df_wide.reset_index(inplace=True)
                    
                    csv_data_wide = df_wide.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Scarica Dataset WIDE .CSV", data=csv_data_wide, file_name="dataset_ricerca_geriatrica_WIDE.csv", mime="text/csv")
                    st.dataframe(df_wide.head())
                except Exception as e:
                    st.error(f"Errore nella strutturazione del formato WIDE: {e}")
# ==============================================================================
# INTERFACCIA 3: AREA PERSONALE DIGITALE DEL PAZIENTE
# ==============================================================================
elif modalita_principale == "🔐 Area Personale (Paziente)":
    st.title("🔒 Accesso Area Personale Paziente")
    st.write("Inserisci il tuo codice identificativo personale fornito dal centro clinico per visualizzare i tuoi progressi.")
    
    id_input = st.text_input("Codice Identificativo Personale (es. AB50):").strip().upper()
    
    if id_input:
        df_paziente = leggi_dati_paziente()
        df_valutazioni = leggi_dati_valutazioni()
        
        # Pulizia id per matching perfetto
        pazienti_validi = df_paziente.dropna(subset=[df_paziente.columns[2]]).iloc[:, 2].astype(str).str.strip().values
        
        if id_input in pazienti_validi:
            st.success("✅ Autenticazione riuscita! Benvenuto nella tua area personale.")
            st.markdown("---")
            
            # SOLUZIONE IMPRECISIONE 1: Rimozione righe corrotte e indicizzazione numerica asse X
            df_val_clean = df_valutazioni.dropna(subset=[df_valutazioni.columns[10], df_valutazioni.columns[25]])
            storico_val_paz = df_val_clean[df_val_clean.iloc[:, 10].astype(str).str.strip() == id_input].copy()
            
            st.subheader("📈 L'Evoluzione dei tuoi Risultati nel Tempo")
            
            if not storico_val_paz.empty and len(storico_val_paz) > 0:
                # Ordinamento temporale forzato da dizionario
                ordine_cronologico = {f: i for i, f in enumerate(OPZIONI_FASE)}
                storico_val_paz["Ordine"] = storico_val_paz.iloc[:, 25].astype(str).str.strip().map(ordine_cronologico).fillna(99)
                storico_val_paz = storico_val_paz.sort_values("Ordine", ascending=True)
                
                # Creazione etichette asse X numerate per forzare la direzione Sinistra ➔ Destra in Plotly
                def etichetta_paziente_fissa(riga):
                    fase = str(riga.iloc[25]).strip()
                    if "Baseline" in fase: return "1. Inizio Percorso"
                    elif "3" in fase: return "2. Dopo 3 Mesi"
                    elif "6" in fase: return "3. Dopo 6 Mesi"
                    elif "9" in fase: return "4. Dopo 9 Mesi"
                    elif "12" in fase: return "5. Dopo 12 Mesi"
                    return f"Controllo: {fase}"
                
                storico_val_paz["Visualizzazione_X"] = storico_val_paz.apply(etichetta_paziente_fissa, axis=1)
                
                t1, t2, t3 = st.tabs(["Capacità Funzionali e Agilità", "Sviluppo della Forza", "Parametri di Salute ed Emodinamica"])
                
                with t1:
                    fig_p1 = go.Figure()
                    fig_p1.add_trace(go.Scatter(x=storico_val_paz["Visualizzazione_X"], y=storico_val_paz.iloc[:, 4], name="Alzate dalla sedia (30s)", mode="lines+markers", line=dict(width=3, color="green")))
                    fig_p1.add_trace(go.Scatter(x=storico_val_paz["Visualizzazione_X"], y=storico_val_paz.iloc[:, 11], name="Agilità nel Cammino (TUG - Secondi)", mode="lines+markers", line=dict(width=3, color="orange")))
                    fig_p1.update_layout(title="Miglioramento dell'Autonomia Motoria", xaxis_title="Evoluzione del mio percorso (Inizio ➔ Successive)", yaxis_title="Valori del test", legend_orientation="h")
                    st.plotly_chart(fig_p1, use_container_width=True)
                    
                with t2:
                    fig_p2 = go.Figure()
                    fig_p2.add_trace(go.Scatter(x=storico_val_paz["Visualizzazione_X"], y=storico_val_paz.iloc[:, 16], name="Forza Gamba Destra", mode="lines+markers"))
                    fig_p2.add_trace(go.Scatter(x=storico_val_paz["Visualizzazione_X"], y=storico_val_paz.iloc[:, 17], name="Forza Gamba Sinistra", mode="lines+markers"))
                    fig_p2.add_trace(go.Scatter(x=storico_val_paz["Visualizzazione_X"], y=storico_val_paz.iloc[:, 22], name="Forza Presa Mano Destra", mode="lines+markers", line=dict(dash="dash")))
                    fig_p2.add_trace(go.Scatter(x=storico_val_paz["Visualizzazione_X"], y=storico_val_paz.iloc[:, 23], name="Forza Presa Mano Sinistra", mode="lines+markers", line=dict(dash="dash")))
                    fig_p2.update_layout(title="Andamento della Forza Muscolare (Kg)", xaxis_title="Evoluzione del mio percorso (Inizio ➔ Successive)", yaxis_title="Forza (Kg)", legend_orientation="h")
                    st.plotly_chart(fig_p2, use_container_width=True)
                    
                with t3:
                    fig_p3 = go.Figure()
                    fig_p3.add_trace(go.Scatter(x=storico_val_paz["Visualizzazione_X"], y=storico_val_paz.iloc[:, 6], name="Frequenza Cardiaca Sotto Sforzo", mode="lines+markers", line=dict(color="red")))
                    fig_p3.add_trace(go.Scatter(x=storico_val_paz["Visualizzazione_X"], y=storico_val_paz.iloc[:, 7], name="Saturazione Ossigeno Post Test (%)", mode="lines+markers", line=dict(color="blue")))
                    fig_p3.update_layout(title="I miei Parametri di Efficienza Cardiovascolare", xaxis_title="Evoluzione del mio percorso (Inizio ➔ Successive)", yaxis_title="Valore misurato", legend_orientation="h")
                    st.plotly_chart(fig_p3, use_container_width=True)
                
                st.markdown("---")
                st.info("🎯 **Nota del Team Medico:** I tuoi grafici mostrano l'impegno che stai mettendo nelle sessioni riabilitative. Piccoli e costanti miglioramenti nel tempo rappresentano la chiave per conservare un'ottima autonomia e ridurre il rischio di cadute nelle attività di tutti i giorni. Continua così!")
            else:
                st.warning("I tuoi test clinici iniziali sono in fase di elaborazione. Saranno visibili non appena il fisioterapista completerà l'inserimento della prima sessione strumentale.")
        else:
            st.error("Codice Identificativo non trovato nel database dello studio. Verifica con il tuo terapeuta.")
