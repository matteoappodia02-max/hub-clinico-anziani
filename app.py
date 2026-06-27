import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px

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
    return df.dropna(how="all").reset_index(drop=True)

@st.cache_data(ttl=5)
def leggi_dati_valutazioni():
    df = conn.read(spreadsheet=URL_FOGLIO, worksheet="Valutazioni_Studio")
    return df.dropna(how="all").reset_index(drop=True)

# ==============================================================================
# 1. ALGORITMO DI GENERAZIONE PROGRESSIONE
# ==============================================================================
def genera_progressione_senior(dati_paziente, test_funzionali):
    patologie = dati_paziente.get('patologie', [])
    rischio_caduta = dati_paziente.get('rischio_caduta', 'basso')
    fragilita = dati_paziente.get('fragilita_percepita', 1)
    distress = dati_paziente.get('distress_emotivo', 1)
    esperienza = dati_paziente.get('esperienza_allenamento', 'novizio')
    
    piano_allenamento = {
        "fase_allenamento": "",
        "intensita_forza": "",
        "volume_forza": "",
        "allenamento_potenza_velocita": False,
        "parametri_potenza": {},
        "condizionamento_aerobico": {},
        "esercizi_consigliati": {},
        "recupero_tra_sedute": "48-72 ore",
        "note_sicurezza": [],
        "focus_fisioterapista": []
    }

    # Vincoli Patologici
    if "ipertensione" in patologie or "cardiopatia" in patologie:
        piano_allenamento["note_sicurezza"].append("Evitare manovra di Valsalva. Mantenere ripetizioni > 8, niente sforzi massimali.")
    if "osteoporosi" in patologie:
        piano_allenamento["note_sicurezza"].append("Includere esercizi multi-articolari per stimolo assiale. Evitare flessioni spinali sotto carico.")
    if "artrosi" in patologie or "dolore_articolare" in patologie:
        piano_allenamento["note_sicurezza"].append("Selezionare ROM senza dolore. Evitare decelerazioni improvvise.")

    if fragilita > 7 or distress > 7:
        piano_allenamento["fase_allenamento"] = "Condizionamento di base / Adattamento Anatomico"
        piano_allenamento["note_sicurezza"].append("Distress elevato: ridurre volume totale del 20-30% (Prevenzione overreaching).")
        esperienza = "novizio"

    # Prescrizione Forza
    if esperienza == "novizio":
        piano_allenamento["intensita_forza"] = "50-70% 1RM stimato (10-15 RM)"
        piano_allenamento["volume_forza"] = "1-2 serie per gruppo, 10-15 ripetizioni"
        piano_allenamento["focus_fisioterapista"].append("Focus su apprendimento motorio e controllo posturale.")
        if not piano_allenamento["fase_allenamento"]: piano_allenamento["fase_allenamento"] = "Adattamento Anatomico"
    elif esperienza == "intermedio":
        piano_allenamento["intensita_forza"] = "60-80% 1RM stimato (8-12 RM)"
        piano_allenamento["volume_forza"] = "2-3 serie per gruppo, 8-12 ripetizioni"
        if not piano_allenamento["fase_allenamento"]: piano_allenamento["fase_allenamento"] = "Ipertrofia / Forza Generale"
    elif esperienza == "avanzato":
        piano_allenamento["intensita_forza"] = "70-85% 1RM stimato (6-10 RM)"
        piano_allenamento["volume_forza"] = "3+ serie per gruppo, 6-10 ripetizioni"
        if not piano_allenamento["fase_allenamento"]: piano_allenamento["fase_allenamento"] = "Forza Massima Periodizzata"

    # Sviluppo Potenza
    if rischio_caduta in ["medio", "alto"] and fragilita < 8:
        piano_allenamento["allenamento_potenza_velocita"] = True
        piano_allenamento["focus_fisioterapista"].append("Focus critico su Rate of Force Development (RFD). Massima accelerazione concentrica.")
        piano_allenamento["parametri_potenza"] = {
            "intensita": "30-60% 1RM (carichi leggeri)",
            "volume": "1-3 serie, 3-6 ripetizioni",
            "esecuzione": "Fase eccentrica controllata, concentrica veloce",
            "recupero_tra_serie": "2-3 minuti"
        }

    # Esercizi a Corpo Libero Consigliati
    piano_allenamento["esercizi_consigliati"] = {
        "Arti Inferiori": [
            "Squat assistito con sedia (Sit-to-stand)", 
            "Step-up frontale su gradino basso", 
            "Ponte glutei (Glute bridge) bipodalico a terra", 
            "Abduzioni anca in stazione eretta (con appoggio)"
        ],
        "Arti Superiori & Core": [
            "Push-up facilitati al muro (Wall push-ups)", 
            "Rematore isometrico con asciugamano o elastico leggero", 
            "Plank frontale modificato (appoggio su muro o tavolo)", 
            "Bird-dog (Quadrupedia) o estensioni alternate da seduto"
        ]
    }

    # Condizionamento Aerobico / Potenza Aerobica
    piano_allenamento["condizionamento_aerobico"] = {
        "frequenza": "3-5 giorni a settimana",
        "intensita": "Moderata (RPE 4-6 su 10, percezione di lieve affanno ma capacità di parlare)",
        "volume": "150 minuti cumulativi a settimana (es. 5 blocchi da 30 min, o 10 da 15 min)",
        "potenza_aerobica": "Se SPPB >= 9: introdurre 1 volta a settimana Interval Training (1 min passo svelto / 2 min passo lento).",
        "modalita": "Cammino su piano, cyclette orizzontale, o ergometro a braccia (in caso di deficit arti inferiori)."
    }

    if test_funzionali.get("deficit_lower_body", False):
        piano_allenamento["focus_fisioterapista"].append("Priorità all'ipertrofia arti inferiori: subiscono un declino di massa più rapido.")

    return piano_allenamento

def renderizza_sezione_fisioterapista(df_pazienti, df_valutazioni):
    st.header("🦾 Progressione Senior (NSCA & Aerobic Power)")
    st.markdown("Genera un piano d'allenamento di forza e condizionamento aerobico basato sulle prove scientifiche.")
    
    if df_pazienti.empty:
        st.warning("Nessun dato paziente disponibile al momento.")
        return

    colonna_id = next((col for col in ["ID Paziente", "ID_Paziente", "id paziente"] if col in df_pazienti.columns), df_pazienti.columns[2] if len(df_pazienti.columns) > 2 else None)
    if not colonna_id: return
    
    lista_pazienti = df_pazienti[colonna_id].dropna().astype(str).str.strip().unique().tolist()
    paz_selezionato = st.selectbox("Seleziona Paziente per prescrizione allenamento:", lista_pazienti, key="sb_nsca_prog")
    
    if paz_selezionato:
        storico_paz = df_pazienti[df_pazienti[colonna_id].astype(str).str.strip() == paz_selezionato]
        
        col_id_val = next((col for col in ["ID Paziente", "ID_Paziente", "id paziente"] if col in df_valutazioni.columns), df_valutazioni.columns[10] if len(df_valutazioni.columns) > 10 else None)
        storico_val = df_valutazioni[df_valutazioni[col_id_val].astype(str).str.strip() == paz_selezionato] if col_id_val and not df_valutazioni.empty else pd.DataFrame()

        if not storico_paz.empty:
            ultimo_record = storico_paz.iloc[-1]
            
            # Mappatura Patologie
            col_pat_sist = next((col for col in storico_paz.columns if "Sistemiche" in col), storico_paz.columns[8] if len(storico_paz.columns) > 8 else None)
            col_cond_mecc = next((col for col in storico_paz.columns if "Meccaniche" in col), storico_paz.columns[7] if len(storico_paz.columns) > 7 else None)
            pat_raw = (str(ultimo_record.get(col_pat_sist, "")) + " " + str(ultimo_record.get(col_cond_mecc, ""))).lower()
            pat_attive = [p for p in ["ipertensione", "cardiopatia", "osteoporosi", "artrosi"] if p in pat_raw]

            # Mappatura Fragilità e Distress (Colonne 23, 24, 20, 21, 10 circa)
            v12 = pd.to_numeric(ultimo_record.iloc[23] if len(ultimo_record)>23 else 0, errors='coerce')
            v13 = pd.to_numeric(ultimo_record.iloc[24] if len(ultimo_record)>24 else 0, errors='coerce')
            v9 = pd.to_numeric(ultimo_record.iloc[20] if len(ultimo_record)>20 else 0, errors='coerce')
            v10 = pd.to_numeric(ultimo_record.iloc[21] if len(ultimo_record)>21 else 0, errors='coerce')
            dolore = pd.to_numeric(ultimo_record.iloc[10] if len(ultimo_record)>10 else 0, errors='coerce')
            
            frag_max = max(np.nan_to_num(v12), np.nan_to_num(v13))
            dist_max = max(np.nan_to_num(v9), np.nan_to_num(v10), np.nan_to_num(dolore))
            rischio_cad = "alto" if frag_max >= 7 else ("medio" if frag_max >= 4 else "basso")

            # Deficit Lower Body (Dinamometria)
            deficit_lower = False
            if not storico_val.empty:
                ult_val = storico_val.iloc[-1]
                f_dx = pd.to_numeric(ult_val.iloc[16] if len(ult_val)>16 else 0, errors='coerce')
                f_sn = pd.to_numeric(ult_val.iloc[17] if len(ult_val)>17 else 0, errors='coerce')
                f_dx, f_sn = np.nan_to_num(f_dx), np.nan_to_num(f_sn)
                if f_dx > 0 and f_sn > 0 and (max(f_dx, f_sn) < 10 or abs(f_dx - f_sn) > max(f_dx, f_sn)*0.2):
                    deficit_lower = True

            risultato = genera_progressione_senior(
                {"patologie": pat_attive, "rischio_caduta": rischio_cad, "fragilita_percepita": frag_max, "distress_emotivo": dist_max, "esperienza_allenamento": "novizio"},
                {"deficit_lower_body": deficit_lower}
            )

            st.markdown("---")
            c1, c2 = st.columns(2)
            with c1:
                st.info(f"**Intensità Forza:** {risultato['intensita_forza']}\n\n**Volume Forza:** {risultato['volume_forza']}")
            with c2:
                st.warning(f"**Fase Allenamento:** {risultato['fase_allenamento']}\n\n**Recupero:** {risultato['recupero_tra_sedute']}")

            if risultato["note_sicurezza"]:
                st.error("**⚠️ Sicurezza:**\n" + "\n".join([f"- {n}" for n in risultato["note_sicurezza"]]))
            
            # Esercizi Consigliati
            st.subheader("🏋️ Esercizi a Corpo Libero Suggeriti")
            col_es1, col_es2 = st.columns(2)
            with col_es1:
                st.markdown("**Arti Inferiori:**")
                for es in risultato["esercizi_consigliati"]["Arti Inferiori"]: st.markdown(f"- {es}")
            with col_es2:
                st.markdown("**Arti Superiori & Core:**")
                for es in risultato["esercizi_consigliati"]["Arti Superiori & Core"]: st.markdown(f"- {es}")

            # Condizionamento Aerobico
            st.subheader("🫀 Condizionamento Aerobico & Potenza")
            ca = risultato["condizionamento_aerobico"]
            st.markdown(f"- **Frequenza e Volume:** {ca['frequenza']}, {ca['volume']}")
            st.markdown(f"- **Intensità:** {ca['intensita']}")
            st.markdown(f"- **Modalità consigliate:** {ca['modalita']}")
            st.markdown(f"- **Potenza Aerobica:** {ca['potenza_aerobica']}")

            if risultato["allenamento_potenza_velocita"]:
                with st.expander("⚡ Sviluppo Potenza (Prevenzione Cadute)", expanded=True):
                    pp = risultato["parametri_potenza"]
                    st.write(f"- Intensità: {pp['intensita']} | Volume: {pp['volume']}")
                    st.write(f"- Esecuzione: {pp['esecuzione']} | Recupero: {pp['recupero_tra_serie']}")

# ==============================================================================
# FUNZIONI DI SUPPORTO CLINICO
# ==============================================================================
OPZIONI_FASE = ["Baseline (Prima Valutazione)", "Follow-up 3 Mesi", "Follow-up 6 Mesi", "Follow-up 9 Mesi", "Follow-up 12 Mesi"]
MDC_SOGLIE = {"SPPB": 1.0, "TUG": -2.1, "STS_5X": -2.3, "HANDGRIP": 5.0}

def formatta_asse_x(riga):
    try:
        data_pulita = str(riga.iloc[0]).split()[0]
        fase_completa = str(riga.iloc[25]).strip()
        mappa = {"Baseline": ("1", "Baseline"), "3": ("2", "3M"), "6": ("3", "6M"), "9": ("4", "9M"), "12": ("5", "12M")}
        ord_num, f_breve = "6", fase_completa
        for k, (o, b) in mappa.items():
            if k in fase_completa:
                ord_num, f_breve = o, b
                break
        return f"{ord_num}. {data_pulita} ({f_breve})"
    except: return "N/D"

def calcola_dimensioni_biopsicosociali(riga_paziente):
    try:
        v = riga_paziente.iloc[12:30].astype(float).values
        kinesiofobia = np.nanmean([v[9], v[10], v[11], v[16]])
        accettazione = np.nanmean([v[2], v[6], v[7], v[14]])
        autoefficacia = np.nanmean([v[0], v[1], v[8], v[15]])
        impatto_dol = np.nanmean([v[12], v[13], v[17]])
        return {
            "Kinesiofobia & Paura": round(kinesiofobia, 2),
            "Accettazione (Approccio PACT)": round(accettazione, 2),
            "Autoefficacia Motoria": round(autoefficacia, 2),
            "Percezione Stato Funzionale": round(impatto_dol, 2)
        }
    except:
        return {"Kinesiofobia & Paura": 0, "Accettazione (Approccio PACT)": 0, "Autoefficacia Motoria": 0, "Percezione Stato Funzionale": 0}

def esegui_screening_geriatrici(riga_valutazione, sesso_paziente):
    alert_sarcopenia, alert_frailty, alert_cadute = "Verde", "Verde", "Verde"
    try:
        hg_dx = pd.to_numeric(riga_valutazione.iloc[22], errors='coerce')
        hg_sn = pd.to_numeric(riga_valutazione.iloc[23], errors='coerce')
        max_hg = max(np.nan_to_num(hg_dx), np.nan_to_num(hg_sn))
        tug = pd.to_numeric(riga_valutazione.iloc[11], errors='coerce')
        sts = pd.to_numeric(riga_valutazione.iloc[12], errors='coerce')
        sppb = sum([np.nan_to_num(pd.to_numeric(riga_valutazione.iloc[13], errors='coerce')), 
                    np.nan_to_num(pd.to_numeric(riga_valutazione.iloc[14], errors='coerce')), 
                    np.nan_to_num(pd.to_numeric(riga_valutazione.iloc[15], errors='coerce'))])
        
        # Sarcopenia
        cutoff_hg = 27 if str(sesso_paziente).lower() == "uomo" else 16
        if max_hg > 0 and max_hg < cutoff_hg: alert_sarcopenia = "Rosso (Sarcopenia Sospetta - Richiesto approfondimento)"
        elif sts > 15: alert_sarcopenia = "Giallo (Forza muscolare ridotta alla sedia)"
        else: alert_sarcopenia = "Verde (Forza e massa nella norma)"
            
        # Fragilità
        punti = sum([1 if sppb < 9 else 0, 1 if (max_hg > 0 and max_hg < cutoff_hg) else 0, 1 if sts > 15 else 0])
        if punti >= 2: alert_frailty = "Rosso (Paziente Fragile - Rischio avverso elevato)"
        elif punti == 1: alert_frailty = "Giallo (Paziente Pre-Fragile)"
        else: alert_frailty = "Verde (Paziente Robusto)"
        
        # Cadute
        if tug > 12 or sppb < 10: alert_cadute = "Rosso (Rischio Cadute Elevato)"
        else: alert_cadute = "Verde (Basso Rischio Cadute)"
    except: pass
    return {"sarcopenia": alert_sarcopenia, "frailty": alert_frailty, "cadute": alert_cadute}

# ==============================================================================
# MENU LATERALE
# ==============================================================================
st.sidebar.title("🩺 Hub Clinico")
modalita_principale = st.sidebar.radio("Area Operativa:", [
    "📋 Screening Iniziale (Paziente)", 
    "📊 Pannello Analisi Avanzata (Fisioterapista)", 
    "🔐 Area Personale (Paziente)"
])

# ==============================================================================
# AREA 1: SCREENING INIZIALE PAZIENTE (Codice Invariato)
# ==============================================================================
if modalita_principale == "📋 Screening Iniziale (Paziente)":
    st.title("👵 Modulo Integrato di Valutazione del Movimento")
    df_paziente = leggi_dati_paziente()
    
    with st.form("form_paziente_totale"):
        st.subheader("📌 Sezione A: Identificazione")
        fase_paziente = st.selectbox("Fase della valutazione:", OPZIONI_FASE)
        col_consenso = st.selectbox("Consenso GDPR:", ["Acconsento", "Non acconsento"])
        col_compilatore = st.selectbox("Compilato da:", ["Paziente stesso", "Familiare", "Caregiver"])
        c1, c2, c3 = st.columns(3)
        with c1: ini = st.text_input("Iniziali (Max 3):", max_chars=3).strip().upper()
        with c2: anno = st.number_input("Anno di Nascita:", 1920, 2016, 1950)
        with c3: sesso = st.selectbox("Sesso Biologico:", ["Uomo", "Donna"])
        sit = st.selectbox("Contesto abitativo:", ["Autonomia", "Con familiari", "Con badante"])
        
        st.subheader("🩺 Sezione B: Anamnesi")
        c_mecc = st.multiselect("Limitazioni meccaniche:", ["Artrosi Severa", "Osteoporosi", "Protesi d'anca", "Protesi di ginocchio", "Nessuna"])
        c_sist = st.multiselect("Comorbilità sistemiche:", ["Ipertensione arteriosa", "Diabete", "Cardiopatia", "Nessuna"])
        red = st.multiselect("Red Flags:", ["Perdita di peso", "Febbre", "Intorpidimento", "Nessuno"])
        nrs = st.slider("Dolore medio (0-10):", 0, 10, 5)
        farmaci = st.text_input("Farmaci:")
        spec = st.text_area("Note:")

        st.subheader("🧠 Sezione C: Vissuto Psicocomportamentale")
        v = [st.slider(f"Q{i}", 1, 10, 5) for i in range(1, 19)]

        if st.form_submit_button("Salva Screening"):
            id_gen = f"{ini}{str(anno)[-2:]}"
            riga = [datetime.now().strftime("%d/%m/%Y %H.%M.%S"), col_consenso, id_gen, col_compilatore, datetime.now().year - anno, sesso, sit,
                    ", ".join(c_mecc), ", ".join(c_sist), ", ".join(red), nrs, farmaci] + v + [spec, fase_paziente]
            try:
                conn.update(spreadsheet=URL_FOGLIO, worksheet="Dati_Paziente", data=pd.concat([df_paziente, pd.DataFrame([riga], columns=df_paziente.columns)], ignore_index=True))
                st.success(f"Salvato. ID: {id_gen}")
                st.cache_data.clear()
            except Exception as e: st.error(e)

# ==============================================================================
# AREA 2: PANNELLO FISIOTERAPISTA
# ==============================================================================
elif modalita_principale == "📊 Pannello Analisi Avanzata (Fisioterapista)":
    if not st.session_state.fiso_auth:
        st.title("🔒 Accesso Riservato")
        if st.button("Autentica") if st.text_input("PIN:", type="password") == "1234" else False:
            st.session_state.fiso_auth = True
            st.rerun()
        st.stop()

    if st.sidebar.button("🚪 Esci Sessione"): st.session_state.fiso_auth, _ = False, st.rerun()

    st.title("👨‍⚕️ Dashboard Clinica Avanzata")
    sub_menu = st.radio("Ambito Operativo:", [
        "🦾 Progressione Senior (NSCA)",
        "📝 Registrazione Nuovi Test", 
        "🧠 Analisi Multidimensionale & Longitudinale", 
        "💾 Export Dati"
    ], horizontal=True)
    st.markdown("---")

    df_paz = leggi_dati_paziente()
    df_val = leggi_dati_valutazioni()
    col_id = next((c for c in ["ID Paziente", "ID_Paziente"] if c in df_paz.columns), df_paz.columns[2] if len(df_paz.columns)>2 else None)
    lista_paz = df_paz[col_id].dropna().astype(str).str.strip().unique().tolist() if not df_paz.empty and col_id else []

    # --- SOTTO-PAGINA 1: PROGRESSIONE ---
    if sub_menu == "🦾 Progressione Senior (NSCA)":
        renderizza_sezione_fisioterapista(df_paz, df_val)

    # --- SOTTO-PAGINA 2: TEST CLINICI ---
    elif sub_menu == "📝 Registrazione Nuovi Test":
        if not lista_paz: st.warning("Nessun paziente.")
        else:
            p_scelto = st.selectbox("Paziente:", lista_paz)
            storico = df_paz[df_paz[col_id].astype(str).str.strip() == p_scelto]
            fc_max = round(208 - (0.7 * int(storico.iloc[0, 4])), 1) if not storico.empty else None

            with st.form("form_val"):
                fase = st.selectbox("Fase:", OPZIONI_FASE)
                c1, c2, c3 = st.columns(3)
                with c1: pas = st.number_input("PAS (mmHg)", value=None)
                with c2: fc = st.number_input("FC Riposo", value=None)
                with c3: sat = st.number_input("SatO2 %", value=None)
                
                c4, c5, c6 = st.columns(3)
                with c4: ch30 = st.number_input("30s Chair Stand", value=None)
                with c5: step = st.number_input("30s Step", value=None)
                with c6: fcp = st.number_input("FC Post-Test", value=None)
                
                c7, c8, c9 = st.columns(3)
                with c7: tug = st.number_input("TUG (s)", value=None)
                with c8: sts5 = st.number_input("5xSTS (s)", value=None)
                with c9: satp = st.number_input("SatO2 Post %", value=None)
                
                rec = st.number_input("Recupero (min)", value=None)
                
                c10, c11, c12 = st.columns(3)
                with c10: seq = st.number_input("SPPB Equilibrio", value=None)
                with c11: scam = st.number_input("SPPB Cammino", value=None)
                with c12: sch = st.number_input("SPPB Chair", value=None)
                
                c13, c14 = st.columns(2)
                with c13:
                    qdx = st.number_input("Forza Quad DX", value=None)
                    gdx = st.number_input("Forza Gluteo DX", value=None)
                    pdx = st.number_input("Forza Psoas DX", value=None)
                    hdx = st.number_input("Handgrip DX", value=None)
                with c14:
                    qsn = st.number_input("Forza Quad SN", value=None)
                    gsn = st.number_input("Forza Gluteo SN", value=None)
                    psn = st.number_input("Forza Psoas SN", value=None)
                    hsn = st.number_input("Handgrip SN", value=None)

                if st.form_submit_button("Salva Test"):
                    r = [datetime.now().strftime("%d/%m/%Y %H.%M.%S"), pas, fc, sat, ch30, step, fcp, satp, rec, "",
                         p_scelto, tug, sts5, seq, scam, sch, qdx, qsn, gdx, gsn, pdx, psn, hdx, hsn, fc_max, fase]
                    try:
                        conn.update(spreadsheet=URL_FOGLIO, worksheet="Valutazioni_Studio", data=pd.concat([df_val, pd.DataFrame([r], columns=df_val.columns)], ignore_index=True))
                        st.success("Test Salvato.")
                        st.cache_data.clear()
                    except Exception as e: st.error(e)

    # --- SOTTO-PAGINA 3: UNIFICATA MULTIDIMENSIONALE, BPS E LONGITUDINALE ---
    elif sub_menu == "🧠 Analisi Multidimensionale & Longitudinale":
        st.subheader("Pannello di Analisi Clinica Integrata")
        if not lista_paz:
            st.warning("Nessun paziente registrato.")
        else:
            paz_scelto = st.selectbox("Seleziona Paziente da analizzare:", lista_paz, key="sb_multi")
            
            st_paz = df_paz[df_paz[col_id].astype(str).str.strip() == paz_scelto]
            col_id_v = next((c for c in ["ID Paziente", "ID_Paziente"] if c in df_val.columns), df_val.columns[10] if len(df_val.columns)>10 else None)
            df_v_clean = df_val.dropna(subset=[df_val.columns[10], df_val.columns[25]]) if not df_val.empty else pd.DataFrame()
            st_val = df_v_clean[df_v_clean[col_id_v].astype(str).str.strip() == paz_scelto].copy() if not df_v_clean.empty else pd.DataFrame()

            tab_bps, tab_cds, tab_long = st.tabs(["🧠 Radar Biopsicosociale (PACT)", "🧫 Screening Sindromi Geriatriche", "📈 Grafici Forza & Funzione"])
            
            # TAB 1: RADAR BPS
            with tab_bps:
                st.markdown("#### Mappatura Psicocomportamentale")
                if not st_paz.empty:
                    fase_scelta = st.selectbox("Fase Screening BPS:", st_paz.iloc[:, 31].dropna().unique())
                    riga_mirata = st_paz[st_paz.iloc[:, 31] == fase_scelta].iloc[0]
                    dim = calcola_dimensioni_biopsicosociali(riga_mirata)
                    
                    # Costruzione dati per grafico polare chiuso
                    cat = list(dim.keys())
                    val = list(dim.values())
                    cat += cat[:1]
                    val += val[:1]
                    
                    fig_radar = go.Figure(go.Scatterpolar(r=val, theta=cat, fill='toself', line_color="#1f77b4"))
                    fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 10])), showlegend=False, height=400)
                    st.plotly_chart(fig_radar, use_container_width=True)
                    
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Kinesiofobia", f"{dim['Kinesiofobia & Paura']}/10")
                    c2.metric("Accettazione PACT", f"{dim['Accettazione (Approccio PACT)']}/10")
                    c3.metric("Autoefficacia", f"{dim['Autoefficacia Motoria']}/10")
                    c4.metric("Percezione Stato", f"{dim['Percezione Stato Funzionale']}/10")
                else: st.info("Dati BPS assenti.")

            # TAB 2: SCREENING CDS (BOX COLORATI)
            with tab_cds:
                st.markdown("#### Esito Algoritmi Decision Support (Linee Guida)")
                if not st_paz.empty and not st_val.empty:
                    sesso = st_paz.iloc[-1, 5] if len(st_paz.columns) > 5 else "Donna"
                    esiti = esegui_screening_geriatrici(st_val.iloc[-1], sesso)
                    
                    # Sarcopenia
                    if "Rosso" in esiti["sarcopenia"]: st.error(f"**Sarcopenia:** {esiti['sarcopenia']}")
                    elif "Giallo" in esiti["sarcopenia"]: st.warning(f"**Sarcopenia:** {esiti['sarcopenia']}")
                    else: st.success(f"**Sarcopenia:** {esiti['sarcopenia']}")
                    
                    # Fragilità
                    if "Rosso" in esiti["frailty"]: st.error(f"**Fragilità (Frailty):** {esiti['frailty']}")
                    elif "Giallo" in esiti["frailty"]: st.warning(f"**Fragilità (Frailty):** {esiti['frailty']}")
                    else: st.success(f"**Fragilità (Frailty):** {esiti['frailty']}")
                    
                    # Cadute
                    if "Rosso" in esiti["cadute"]: st.error(f"**Rischio Cadute:** {esiti['cadute']}")
                    else: st.success(f"**Rischio Cadute:** {esiti['cadute']}")
                else:
                    st.info("Necessari test funzionali completi per eseguire lo screening.")

            # TAB 3: GRAFICI LONGITUDINALI
            with tab_long:
                st.markdown("#### Evoluzione Temporale Parametri Fisici")
                if not st_val.empty and len(st_val) > 0:
                    st_val["Asse_X"] = st_val.apply(formatta_asse_x, axis=1)
                    st_val = st_val.sort_values("Asse_X")
                    
                    c_f, c_p = st.columns(2)
                    with c_f:
                        fig_f = go.Figure()
                        fig_f.add_trace(go.Scatter(x=st_val["Asse_X"], y=st_val.iloc[:, 16], name="Quad DX", mode='lines+markers'))
                        fig_f.add_trace(go.Scatter(x=st_val["Asse_X"], y=st_val.iloc[:, 17], name="Quad SN", mode='lines+markers'))
                        fig_f.add_trace(go.Scatter(x=st_val["Asse_X"], y=st_val.iloc[:, 22], name="Grip DX", mode='lines+markers', line=dict(dash='dash')))
                        fig_f.add_trace(go.Scatter(x=st_val["Asse_X"], y=st_val.iloc[:, 23], name="Grip SN", mode='lines+markers', line=dict(dash='dash')))
                        fig_f.update_layout(title="Andamento Forza (Kg)", legend_orientation="h")
                        st.plotly_chart(fig_f, use_container_width=True)
                    with c_p:
                        fig_p = go.Figure()
                        fig_p.add_trace(go.Scatter(x=st_val["Asse_X"], y=st_val.iloc[:, 11], name="TUG (s)", mode='lines+markers'))
                        fig_p.add_trace(go.Scatter(x=st_val["Asse_X"], y=st_val.iloc[:, 12], name="5xSTS (s)", mode='lines+markers'))
                        fig_p.update_layout(title="Test Funzionali Cronometrati", legend_orientation="h")
                        st.plotly_chart(fig_p, use_container_width=True)
                else: st.info("Dati longitudinali insufficienti.")

    # --- SOTTO-PAGINA 4: EXPORT ---
    elif sub_menu == "💾 Export Dati":
        st.download_button("Export Anagrafiche CSV", df_paz.to_csv(index=False), "pazienti.csv", "text/csv")
        st.download_button("Export Valutazioni CSV", df_val.to_csv(index=False), "valutazioni.csv", "text/csv")

# ==============================================================================
# AREA 3: PORTALE PAZIENTE
# ==============================================================================
elif modalita_principale == "🔐 Area Personale (Paziente)":
    st.title("🔐 Il tuo Spazio Riabilitativo")
    df_paziente = leggi_dati_paziente()
    df_valutazioni = leggi_dati_valutazioni()
    
    if df_paziente.empty:
        st.warning("Sistema in aggiornamento.")
    else:
        col_id_paz = next((c for c in ["ID Paziente", "ID_Paziente"] if c in df_paziente.columns), df_paziente.columns[2])
        lista_id = df_paziente[col_id_paz].dropna().astype(str).str.strip().unique().tolist()
        
        paz_id = st.text_input("Inserisci il tuo codice identificativo (es. RM50):").strip().upper()
        if paz_id:
            if paz_id in lista_id:
                st.success(f"Benvenuto/a, ID {paz_id}!")
                
                col_id_val = next((c for c in ["ID Paziente", "ID_Paziente"] if c in df_valutazioni.columns), df_valutazioni.columns[10])
                st_val = df_valutazioni[df_valutazioni[col_id_val].astype(str).str.strip() == paz_id].copy()
                
                if not st_val.empty and len(st_val) > 0:
                    st_val["Asse_X"] = st_val.apply(formatta_asse_x, axis=1)
                    st_val = st_val.sort_values("Asse_X")
                    
                    # Box Riassuntivo Algoritmico
                    if len(st_val) > 1:
                        prima_seduta = st_val.iloc[0]
                        ultima_seduta = st_val.iloc[-1]
                        tug_inizio = pd.to_numeric(prima_seduta.iloc[11], errors='coerce')
                        tug_fine = pd.to_numeric(ultima_seduta.iloc[11], errors='coerce')
                        
                        if pd.notna(tug_inizio) and pd.notna(tug_fine):
                            delta = tug_inizio - tug_fine
                            if delta > 1.0:
                                st.info("🎉 **Ottimo lavoro!** L'analisi dei tuoi dati mostra un netto miglioramento nella tua agilità e nel tuo equilibrio. Stai riducendo significativamente il rischio di cadute. Continua con questo impegno costante negli esercizi!")
                            elif delta < -1.0:
                                st.warning("💡 **Mantieni la rotta:** I parametri indicano una lieve stanchezza o variazione nell'agilità. Parlane con il fisioterapista alla prossima seduta per calibrare al meglio gli esercizi.")
                            else:
                                st.success("✅ **Stabilità confermata:** Stai mantenendo i tuoi livelli di forza ed equilibrio. La costanza è la chiave per proteggere la tua autonomia nel tempo.")

                    st.markdown("---")
                    st.subheader("📈 I tuoi Progressi Visivi")
                    
                    # Grafici Paziente
                    c_p1, c_p2 = st.columns(2)
                    with c_p1:
                        fig_m = go.Figure()
                        fig_m.add_trace(go.Scatter(x=st_val["Asse_X"], y=st_val.iloc[:, 11], name="Agilità (TUG)", mode="lines+markers", line=dict(color="orange")))
                        fig_m.add_trace(go.Scatter(x=st_val["Asse_X"], y=st_val.iloc[:, 4], name="Forza Gambe (Sedia)", mode="lines+markers", line=dict(color="green")))
                        fig_m.update_layout(title="Miglioramento dell'Autonomia", legend_orientation="h")
                        st.plotly_chart(fig_m, use_container_width=True)
                    with c_p2:
                        fig_f = go.Figure()
                        fig_f.add_trace(go.Scatter(x=st_val["Asse_X"], y=st_val.iloc[:, 22], name="Presa Mano DX", mode="lines+markers"))
                        fig_f.add_trace(go.Scatter(x=st_val["Asse_X"], y=st_val.iloc[:, 23], name="Presa Mano SN", mode="lines+markers"))
                        fig_f.update_layout(title="Forza delle Braccia (Kg)", legend_orientation="h")
                        st.plotly_chart(fig_f, use_container_width=True)
                        
                else: st.info("I tuoi test clinici sono in fase di elaborazione. Saranno visibili a breve.")
            else: st.error("Codice ID non trovato. Riprova o contatta il fisioterapista.")
