import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
import tempfile
import os
import kaleido

try:
    from fpdf import FPDF
except ImportError:
    pass # Gestito a runtime

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
# 1. ALGORITMO DI GENERAZIONE PROGRESSIONE E CARICHI REALI
# ==============================================================================
def genera_progressione_senior(dati_paziente, test_funzionali):
    patologie = dati_paziente.get('patologie', [])
    rischio_caduta = dati_paziente.get('rischio_caduta', 'basso')
    fragilita = dati_paziente.get('fragilita_percepita', 1)
    distress = dati_paziente.get('distress_emotivo', 1)
    esperienza = dati_paziente.get('esperienza_allenamento', 'novizio')
    
    piano = {
        "fase_allenamento": "",
        "intensita_perc": 0.5, # Valore numerico per calcoli
        "intensita_forza": "",
        "volume_forza": "",
        "allenamento_potenza_velocita": False,
        "parametri_potenza": {},
        "condizionamento_aerobico": {},
        "esercizi_consigliati": {},
        "scheda_carichi_reali": [],
        "recupero_tra_sedute": "48-72 ore",
        "note_sicurezza": [],
        "focus_fisioterapista": []
    }

    if "ipertensione" in patologie or "cardiopatia" in patologie:
        piano["note_sicurezza"].append("Evitare manovra di Valsalva. Mantenere ripetizioni > 8, niente sforzi massimali.")
    if "osteoporosi" in patologie:
        piano["note_sicurezza"].append("Includere esercizi multi-articolari per lo stimolo assiale.")
    if "artrosi" in patologie or "dolore_articolare" in patologie:
        piano["note_sicurezza"].append("Selezionare ROM senza dolore. Evitare decelerazioni improvvise.")

    if fragilita > 7 or distress > 7:
        piano["fase_allenamento"] = "Condizionamento di base / Adattamento Anatomico"
        piano["note_sicurezza"].append("Distress elevato: ridurre volume totale del 20-30% (Prevenzione overreaching).")
        esperienza = "novizio"

    if esperienza == "novizio":
        piano["intensita_perc"] = 0.5
        piano["intensita_forza"] = "50-60% 1RM (10-15 RM)"
        piano["volume_forza"] = "1-2 serie per gruppo, 10-15 ripetizioni"
        piano["focus_fisioterapista"].append("Focus su apprendimento motorio e controllo posturale.")
        if not piano["fase_allenamento"]: piano["fase_allenamento"] = "Adattamento Anatomico"
    elif esperienza == "intermedio":
        piano["intensita_perc"] = 0.7
        piano["intensita_forza"] = "60-80% 1RM (8-12 RM)"
        piano["volume_forza"] = "2-3 serie per gruppo, 8-12 ripetizioni"
        if not piano["fase_allenamento"]: piano["fase_allenamento"] = "Ipertrofia / Forza Generale"
    elif esperienza == "avanzato":
        piano["intensita_perc"] = 0.8
        piano["intensita_forza"] = "70-85% 1RM (6-10 RM)"
        piano["volume_forza"] = "3+ serie per gruppo, 6-10 ripetizioni"
        if not piano["fase_allenamento"]: piano["fase_allenamento"] = "Forza Massima Periodizzata"

    if rischio_caduta in ["medio", "alto"] and fragilita < 8:
        piano["allenamento_potenza_velocita"] = True
        piano["focus_fisioterapista"].append("Focus critico su Rate of Force Development (RFD). Massima accelerazione concentrica.")
        piano["parametri_potenza"] = {
            "intensita": "30-50% 1RM", "volume": "2-3 serie, 4-6 ripetizioni",
            "esecuzione": "Fase eccentrica controllata, concentrica esplosiva", "recupero": "2-3 minuti"
        }

    piano["esercizi_consigliati"] = {
        "Arti Inferiori": ["Squat su sedia (Sit-to-stand)", "Step-up frontale su gradino basso", "Ponte glutei bipodalico", "Abduzioni anca in piedi"],
        "Arti Superiori & Core": ["Push-up al muro", "Rematore con elastico/manubrio", "Plank su tavolo", "Bird-dog o estensioni incrociate"]
    }

    piano["condizionamento_aerobico"] = {
        "frequenza": "3-5 giorni a settimana",
        "intensita": "Moderata (RPE 4-6 su 10)",
        "volume": "150 minuti/settimana (es. blocchi da 15-30 min)",
        "potenza_aerobica": "Se SPPB >= 9: 1x/settimana Interval Training (1 min sprint / 2 min recupero attivo).",
        "modalita": "Cammino veloce, cyclette orizzontale."
    }

    # Calcolo Scheda Carichi Reali
    f_q_dx = test_funzionali.get("quad_dx", 0)
    f_q_sn = test_funzionali.get("quad_sn", 0)
    f_h_dx = test_funzionali.get("grip_dx", 0)
    perc = piano["intensita_perc"]
    
    if f_q_dx > 0:
        carico_le_dx = round(f_q_dx * perc, 1)
        piano["scheda_carichi_reali"].append({"Distretto": "Estensori Ginocchio DX", "Esercizio Macchina": "Leg Extension DX", "Carico Stimato": f"{carico_le_dx} Kg", "Serie x Rip": piano["volume_forza"]})
    if f_q_sn > 0:
        carico_le_sn = round(f_q_sn * perc, 1)
        piano["scheda_carichi_reali"].append({"Distretto": "Estensori Ginocchio SN", "Esercizio Macchina": "Leg Extension SN", "Carico Stimato": f"{carico_le_sn} Kg", "Serie x Rip": piano["volume_forza"]})
    if f_h_dx > 0:
        carico_trazione = round(f_h_dx * perc, 1)
        piano["scheda_carichi_reali"].append({"Distretto": "Tirata / Grip", "Esercizio Macchina": "Rowing / Lat Machine", "Carico Stimato": f"{carico_trazione} Kg", "Serie x Rip": piano["volume_forza"]})

    if test_funzionali.get("deficit_lower_body", False):
        piano["focus_fisioterapista"].append("Priorità all'ipertrofia arti inferiori: subiscono declino più rapido.")

    return piano

def renderizza_sezione_fisioterapista(df_pazienti, df_valutazioni):
    st.header("🦾 Progressione Senior (NSCA & Aerobic Power)")
    
    if df_pazienti.empty:
        st.warning("Nessun dato paziente disponibile.")
        return

    col_id = next((col for col in ["ID Paziente", "ID_Paziente"] if col in df_pazienti.columns), df_pazienti.columns[2] if len(df_pazienti.columns)>2 else None)
    if not col_id: return
    
    paz_selezionato = st.selectbox("Seleziona Paziente:", df_pazienti[col_id].dropna().astype(str).str.strip().unique().tolist(), key="sb_nsca")
    
    if paz_selezionato:
        storico_paz = df_pazienti[df_pazienti[col_id].astype(str).str.strip() == paz_selezionato]
        col_id_val = next((col for col in ["ID Paziente", "ID_Paziente"] if col in df_valutazioni.columns), df_valutazioni.columns[10] if len(df_valutazioni.columns)>10 else None)
        storico_val = df_valutazioni[df_valutazioni[col_id_val].astype(str).str.strip() == paz_selezionato] if col_id_val and not df_valutazioni.empty else pd.DataFrame()

        if not storico_paz.empty:
            ult_paz = storico_paz.iloc[-1]
            
            c_pat = next((c for c in storico_paz.columns if "Sistemiche" in c), storico_paz.columns[8] if len(storico_paz.columns)>8 else None)
            c_mec = next((c for c in storico_paz.columns if "Meccaniche" in c), storico_paz.columns[7] if len(storico_paz.columns)>7 else None)
            pat_raw = (str(ult_paz.get(c_pat, "")) + " " + str(ult_paz.get(c_mec, ""))).lower()
            pat_attive = [p for p in ["ipertensione", "cardiopatia", "osteoporosi", "artrosi"] if p in pat_raw]

            frag_max = max(np.nan_to_num(pd.to_numeric(ult_paz.iloc[23] if len(ult_paz)>23 else 0, errors='coerce')), np.nan_to_num(pd.to_numeric(ult_paz.iloc[24] if len(ult_paz)>24 else 0, errors='coerce')))
            dist_max = max(np.nan_to_num(pd.to_numeric(ult_paz.iloc[20] if len(ult_paz)>20 else 0, errors='coerce')), np.nan_to_num(pd.to_numeric(ult_paz.iloc[10] if len(ult_paz)>10 else 0, errors='coerce')))
            r_cad = "alto" if frag_max >= 7 else ("medio" if frag_max >= 4 else "basso")

            dati_test = {"deficit_lower_body": False, "quad_dx": 0, "quad_sn": 0, "grip_dx": 0}
            if not storico_val.empty:
                uv = storico_val.iloc[-1]
                q_dx, q_sn = np.nan_to_num(pd.to_numeric(uv.iloc[16], errors='coerce')), np.nan_to_num(pd.to_numeric(uv.iloc[17], errors='coerce'))
                g_dx = np.nan_to_num(pd.to_numeric(uv.iloc[22], errors='coerce'))
                dati_test.update({"quad_dx": q_dx, "quad_sn": q_sn, "grip_dx": g_dx})
                if q_dx > 0 and q_sn > 0 and (max(q_dx, q_sn) < 10 or abs(q_dx - q_sn) > max(q_dx, q_sn)*0.2): dati_test["deficit_lower_body"] = True

            ris = genera_progressione_senior({"patologie": pat_attive, "rischio_caduta": r_cad, "fragilita_percepita": frag_max, "distress_emotivo": dist_max, "esperienza_allenamento": "novizio"}, dati_test)

            st.markdown("---")
            c1, c2 = st.columns(2)
            with c1: st.info(f"**Intensità Forza:** {ris['intensita_forza']}\n\n**Volume:** {ris['volume_forza']}")
            with c2: st.warning(f"**Fase:** {ris['fase_allenamento']}\n\n**Recupero:** {ris['recupero_tra_sedute']}")

            if ris["note_sicurezza"]: st.error("**⚠️ Sicurezza:**\n" + "\n".join([f"- {n}" for n in ris["note_sicurezza"]]))
            
            # Scheda Parametri Reali
            if ris["scheda_carichi_reali"]:
                st.subheader("📋 Scheda Progressioni (Calcolo Reale su Baseline/Ultimo Test)")
                st.table(pd.DataFrame(ris["scheda_carichi_reali"]))

            st.subheader("🏋️ Esercizi a Corpo Libero Suggeriti")
            col_es1, col_es2 = st.columns(2)
            with col_es1:
                st.markdown("**Arti Inferiori:**")
                for es in ris["esercizi_consigliati"]["Arti Inferiori"]: st.markdown(f"- {es}")
            with col_es2:
                st.markdown("**Arti Superiori & Core:**")
                for es in ris["esercizi_consigliati"]["Arti Superiori & Core"]: st.markdown(f"- {es}")

            st.subheader("🫀 Condizionamento Aerobico & Potenza")
            ca = ris["condizionamento_aerobico"]
            st.markdown(f"- **Volume/Freq:** {ca['frequenza']} | {ca['volume']}\n- **Intensità:** {ca['intensita']}\n- **Potenza Aerobica:** {ca['potenza_aerobica']}")

# ==============================================================================
# FUNZIONI DI SUPPORTO CLINICO E PDF
# ==============================================================================
OPZIONI_FASE = ["Baseline (Prima Valutazione)", "Follow-up 3 Mesi", "Follow-up 6 Mesi", "Follow-up 9 Mesi", "Follow-up 12 Mesi"]

def genera_feedback_empatico(kinesiofobia, paura_cadute):
    indice_prudenza = (kinesiofobia + paura_cadute) / 2
    if indice_prudenza < 4:
        return "Hai una buona consapevolezza del tuo corpo!", "Continua a mantenerti attivo/a come stai facendo. La tua sicurezza nei movimenti è un ottimo punto di partenza per conservare l'autonomia.", "success"
    elif 4 <= indice_prudenza < 7:
        return "Alcuni aspetti richiedono attenzione", "Abbiamo notato che talvolta senti un po' di timore nel muoverti liberamente. È normale, ma possiamo lavorarci insieme. Una valutazione ci aiuterà a farti sentire più sicuro/a.", "info"
    else:
        return "Costruiamo insieme la tua sicurezza", "Capiamo che muoversi possa sembrarti faticoso o rischioso. Il nostro obiettivo è aiutarti a ritrovare fiducia nelle tue gambe. Ti suggeriamo un incontro per definire piccoli passi verso l'autonomia.", "warning"

def estrai_ordine(fase_str):
    fase_str = str(fase_str).lower()
    if "baseline" in fase_str: return 1
    if "3" in fase_str: return 2
    if "6" in fase_str: return 3
    if "9" in fase_str: return 4
    if "12" in fase_str: return 5
    return 99 # Per eventuali errori

def formatta_asse_x(riga):
    try:
        data = str(riga.iloc[0]).split()[0]
        fase = str(riga.iloc[25]).strip()
        ord_num = estrai_ordine(fase)
        mappa = {"Baseline": "Baseline", "3": "3M", "6": "6M", "9": "9M", "12": "12M"}
        f_brev = next((b for k, b in mappa.items() if k in fase), fase)
        return f"{ord_num}. {data} ({f_brev})"
    except: return "N/D"

def calcola_dimensioni_biopsicosociali(riga):
    try:
        v = riga.iloc[12:30].astype(float).values
        return {
            "Kinesiofobia": round(np.nanmean([v[9], v[10], v[11], v[16]]), 2),
            "Accettazione PACT": round(np.nanmean([v[2], v[6], v[7], v[14]]), 2),
            "Autoefficacia": round(np.nanmean([v[0], v[1], v[8], v[15]]), 2),
            "Percezione Stato": round(np.nanmean([v[12], v[13], v[17]]), 2)
        }
    except: return {"Kinesiofobia": 0, "Accettazione PACT": 0, "Autoefficacia": 0, "Percezione Stato": 0}

def esegui_screening_geriatrici(riga_val, sesso):
    out = {"sarcopenia": "Verde", "frailty": "Verde", "cadute": "Verde"}
    try:
        max_hg = max(np.nan_to_num(pd.to_numeric(riga_val.iloc[22], errors='coerce')), np.nan_to_num(pd.to_numeric(riga_val.iloc[23], errors='coerce')))
        tug = pd.to_numeric(riga_val.iloc[11], errors='coerce')
        sts = pd.to_numeric(riga_val.iloc[12], errors='coerce')
        sppb = sum([np.nan_to_num(pd.to_numeric(riga_val.iloc[i], errors='coerce')) for i in [13,14,15]])
        
        cutoff_hg = 27 if str(sesso).lower() == "uomo" else 16
        if 0 < max_hg < cutoff_hg: out["sarcopenia"] = "Rosso (Sarcopenia Sospetta)"
        elif sts > 15: out["sarcopenia"] = "Giallo (Forza sedia ridotta)"
            
        punti = sum([1 if sppb < 9 else 0, 1 if (0 < max_hg < cutoff_hg) else 0, 1 if sts > 15 else 0])
        if punti >= 2: out["frailty"] = "Rosso (Paziente Fragile)"
        elif punti == 1: out["frailty"] = "Giallo (Pre-Fragile)"
        
        if tug > 12 or sppb < 10: out["cadute"] = "Rosso (Rischio Elevato)"
    except: pass
    return out

def salva_fig_temp(fig):
    try:
        fd, path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        fig.write_image(path, engine="kaleido")
        return path
    except: return None

def genera_pdf_report(paz_id, df_paz, df_val, figure_grafici=None):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"Report Clinico Riabilitativo - ID: {paz_id}", ln=True, align='C')
    pdf.ln(5)
    
    sesso = "Donna"
    if not df_paz.empty:
        rec = df_paz.iloc[-1]
        sesso = rec.iloc[5]
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 8, "1. Dati Anagrafici e Clinici:", ln=True)
        pdf.set_font("Arial", '', 11)
        pdf.cell(0, 6, f"Sesso: {sesso} | Eta': {rec.iloc[4]}", ln=True)
        pdf.cell(0, 6, f"Patologie: {rec.iloc[8]}", ln=True)
        pdf.ln(5)
        
    if not df_val.empty:
        rec = df_val.iloc[-1]
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 8, "2. Ultima Valutazione Funzionale:", ln=True)
        pdf.set_font("Arial", '', 11)
        pdf.cell(0, 6, f"Data: {rec.iloc[0]} | TUG: {rec.iloc[11]} s | 5xSTS: {rec.iloc[12]} s", ln=True)
        pdf.cell(0, 6, f"Quadricipite (DX/SN): {rec.iloc[16]} / {rec.iloc[17]} Kg", ln=True)
        pdf.ln(5)
        
        esiti = esegui_screening_geriatrici(rec, sesso)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 8, "3. Screening Geriatrico:", ln=True)
        pdf.set_font("Arial", '', 11)
        pdf.cell(0, 6, f"Sarcopenia: {esiti['sarcopenia']}", ln=True)
        pdf.cell(0, 6, f"Fragilita': {esiti['frailty']}", ln=True)
        pdf.cell(0, 6, f"Rischio Cadute: {esiti['cadute']}", ln=True)
        pdf.ln(5)

    # Iniezione Immagini Grafici nel PDF
    if figure_grafici:
        for fig in figure_grafici:
            img_path = salva_fig_temp(fig)
            if img_path:
                pdf.add_page()
                pdf.image(img_path, x=10, w=190)
                os.remove(img_path) # Pulizia file temporaneo
            else:
                pdf.set_font("Arial", 'I', 10)
                pdf.cell(0, 6, "(Per includere i grafici nel PDF e' necessaria la libreria 'kaleido')", ln=True)
                break

    try: return pdf.output(dest='S').encode('latin-1')
    except: return bytes(pdf.output(dest='S'))

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
# AREA 1: SCREENING INIZIALE PAZIENTE
# ==============================================================================
if modalita_principale == "📋 Screening Iniziale (Paziente)":
    st.title("👵 Modulo Integrato di Valutazione del Movimento")
    df_paziente = leggi_dati_paziente()
    
    with st.form("form_paziente_totale"):
        st.subheader("📌 Sezione A: Identificazione e Tempistica")
        fase_paziente = st.selectbox("Fase della valutazione:", OPZIONI_FASE)
        col_consenso = st.selectbox("Consenso GDPR:", ["Acconsento al trattamento dati", "Non acconsento"])
        col_compilatore = st.selectbox("Compilatore:", ["Paziente stesso", "Familiare", "Caregiver"])
        c1, c2, c3 = st.columns(3)
        with c1: iniziali = st.text_input("Iniziali (Max 3):", max_chars=3).strip().upper()
        with c2: anno_nascita = st.number_input("Anno di Nascita:", 1920, 2016, 1950)
        with c3: sesso = st.selectbox("Sesso:", ["Uomo", "Donna"])
        situazione_abitativa = st.selectbox("Contesto abitativo:", ["Autonomia totale", "Con familiari", "Con badante"])
        
        st.subheader("🩺 Sezione B: Anamnesi Generale")
        condizioni_mecc = st.multiselect("Limitazioni meccaniche:", ["Artrosi Severa", "Osteoporosi", "Protesi d'anca", "Protesi di ginocchio", "Nessuna"])
        condizioni_sist = st.multiselect("Comorbilità:", ["Ipertensione", "Diabete", "Cardiopatia", "Nessuna"])
        sintomi_red = st.multiselect("Red Flags:", ["Perdita di peso", "Febbre persistente", "Intorpidimento arti", "Nessuno"])
        dolore_nrs = st.slider("Dolore medio 24h (0-10):", 0, 10, 5)
        farmaci = st.text_input("Farmaci:")
        specifiche_cliniche = st.text_area("Note cliniche:")

        st.subheader("🧠 Sezione C: Vissuto Psicocomportamentale")
        st.caption("Da 1 (Mai / In disaccordo) a 10 (Sempre / D'accordo)")
        v1 = st.slider("1. Nelle ultime 2 settimane mi sono sentito energico", 1, 10, 5)
        v2 = st.slider("2. Contento della routine quotidiana", 1, 10, 5)
        v3 = st.slider("3. Pensieri o preoccupazioni bloccano le mie azioni", 1, 10, 5)
        v4 = st.slider("4. Carattere resiliente di fronte alle difficoltà", 1, 10, 5)
        v5 = st.slider("5. Quando mi spavento fatico a calmarmi", 1, 10, 5)
        v6 = st.slider("6. Furioso per aver perso parte della mobilità", 1, 10, 5)
        v7 = st.slider("7. Non avrei dolore se controllassi la mente", 1, 10, 5)
        v8 = st.slider("8. Con il dolore interrompo subito ogni attività", 1, 10, 5)
        v9 = st.slider("9. L'attività fisica è sicura ed efficace", 1, 10, 5)
        v10 = st.slider("10. Evito i compiti domestici per paura di lesioni", 1, 10, 5)
        v11 = st.slider("11. Le attività quotidiane aumentano l'usura articolare", 1, 10, 5)
        v12 = st.slider("12. Spaventato all'idea di cadere", 1, 10, 5)
        v13 = st.slider("13. In piedi percepisco instabilità/debolezza", 1, 10, 5)
        v14 = st.slider("14. Sicuro nel fare le scale", 1, 10, 5)
        v15 = st.slider("15. Il dolore definisce la mia identità", 1, 10, 5)
        v16 = st.slider("16. Conduco una vita di significato nonostante i sintomi", 1, 10, 5)
        v17 = st.slider("17. Obbligatorio eliminare il dolore per fare progetti", 1, 10, 5)
        v18 = st.slider("18. Sicuro nell'alzarsi dalla sedia senza braccia", 1, 10, 5)

        if st.form_submit_button("Salva Screening"):
            eta = datetime.now().year - anno_nascita
            id_gen = f"{iniziali}{str(anno_nascita)[-2:]}"
            riga = [datetime.now().strftime("%d/%m/%Y %H.%M.%S"), col_consenso, id_gen, col_compilatore, eta, sesso, situazione_abitativa,
                    ", ".join(condizioni_mecc), ", ".join(condizioni_sist), ", ".join(sintomi_red), dolore_nrs, farmaci,
                    v1, v2, v3, v4, v5, v6, v7, v8, v9, v10, v11, v12, v13, v14, v15, v16, v17, v18, specifiche_cliniche, fase_paziente]
            try:
                conn.update(spreadsheet=URL_FOGLIO, worksheet="Dati_Paziente", data=pd.concat([df_paziente, pd.DataFrame([riga], columns=df_paziente.columns)], ignore_index=True))
                st.success(f"Screening salvato correttamente. ID Paziente: {id_gen}")
                
                t_titolo, t_testo, t_tipo = genera_feedback_empatico(v10, v12)
                if t_tipo == "success": st.success(f"**{t_titolo}**\n\n{t_testo}")
                elif t_tipo == "info": st.info(f"**{t_titolo}**\n\n{t_testo}")
                else: st.warning(f"**{t_titolo}**\n\n{t_testo}")
                
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
    sub_menu = st.radio("Ambito Operativo:", ["🦾 Progressione Senior (NSCA)", "📝 Registrazione Nuovi Test", "🧠 Analisi Multidimensionale & Longitudinale", "💾 Export Dati & Report PDF"], horizontal=True)
    st.markdown("---")

    df_paz = leggi_dati_paziente()
    df_val = leggi_dati_valutazioni()
    col_id = next((c for c in ["ID Paziente", "ID_Paziente"] if c in df_paz.columns), df_paz.columns[2] if len(df_paz.columns)>2 else None)
    lista_paz = df_paz[col_id].dropna().astype(str).str.strip().unique().tolist() if not df_paz.empty and col_id else []

    if sub_menu == "🦾 Progressione Senior (NSCA)": renderizza_sezione_fisioterapista(df_paz, df_val)

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
                
                c13, c14 = st.columns(2)
                with c13:
                    qdx = st.number_input("Forza Quad DX", value=None)
                    gdx = st.number_input("Forza Gluteo DX", value=None)
                    hdx = st.number_input("Handgrip DX", value=None)
                with c14:
                    qsn = st.number_input("Forza Quad SN", value=None)
                    gsn = st.number_input("Forza Gluteo SN", value=None)
                    hsn = st.number_input("Handgrip SN", value=None)

                if st.form_submit_button("Salva Test"):
                    r = [datetime.now().strftime("%d/%m/%Y %H.%M.%S"), pas, fc, sat, ch30, step, fcp, satp, 0, "", p_scelto, tug, sts5, 0, 0, 0, qdx, qsn, gdx, gsn, 0, 0, hdx, hsn, fc_max, fase]
                    try:
                        conn.update(spreadsheet=URL_FOGLIO, worksheet="Valutazioni_Studio", data=pd.concat([df_val, pd.DataFrame([r], columns=df_val.columns)], ignore_index=True))
                        st.success("Test Salvato."); st.cache_data.clear()
                    except Exception as e: st.error(e)

    elif sub_menu == "🧠 Analisi Multidimensionale & Longitudinale":
        if not lista_paz: st.warning("Nessun paziente registrato.")
        else:
            paz_scelto = st.selectbox("Analizza Paziente:", lista_paz, key="sb_multi")
            st_paz = df_paz[df_paz[col_id].astype(str).str.strip() == paz_scelto]
            
            col_id_v = next((c for c in ["ID Paziente", "ID_Paziente"] if c in df_val.columns), df_val.columns[10] if len(df_val.columns)>10 else None)
            df_v_clean = df_val.dropna(subset=[df_val.columns[10], df_val.columns[25]]) if not df_val.empty else pd.DataFrame()
            st_val = df_v_clean[df_v_clean[col_id_v].astype(str).str.strip() == paz_scelto].copy() if not df_v_clean.empty else pd.DataFrame()

            t_bps, t_cds, t_long = st.tabs(["🧠 Radar PACT", "🧫 Screening", "📈 Evoluzione Funzionale"])
            
            with t_bps:
                if not st_paz.empty:
                    f_scelta = st.selectbox("Fase BPS:", st_paz.iloc[:, 31].dropna().unique())
                    dim = calcola_dimensioni_biopsicosociali(st_paz[st_paz.iloc[:, 31] == f_scelta].iloc[0])
                    cat, val = list(dim.keys()) + [list(dim.keys())[0]], list(dim.values()) + [list(dim.values())[0]]
                    
                    fig = go.Figure(go.Scatterpolar(r=val, theta=cat, fill='toself'))
                    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 10])))
                    st.plotly_chart(fig, use_container_width=True)
                else: st.info("Dati assenti.")

            with t_cds:
                if not st_paz.empty and not st_val.empty:
                    esiti = esegui_screening_geriatrici(st_val.iloc[-1], st_paz.iloc[-1, 5] if len(st_paz.columns)>5 else "Donna")
                    for cat, v in esiti.items():
                        if "Rosso" in v: st.error(f"**{cat.upper()}:** {v}")
                        elif "Giallo" in v: st.warning(f"**{cat.upper()}:** {v}")
                        else: st.success(f"**{cat.upper()}:** {v}")
                else: st.info("Servono test completi.")

            with t_long:
                if not st_val.empty and len(st_val) > 0:
                    st_val["Ordine_X"] = st_val.iloc[:, 25].apply(estrai_ordine)
                    st_val = st_val.sort_values("Ordine_X")
                    st_val["Asse_X"] = st_val.apply(formatta_asse_x, axis=1)
                    
                    # Logica Filtraggio Asse X con Baseline fissa
                    fasi_disp = st_val["Asse_X"].unique().tolist()
                    baseline_label = next((f for f in fasi_disp if "Baseline" in f), fasi_disp[0])
                    fasi_followup = [f for f in fasi_disp if f != baseline_label]
                    
                    scelte_fu = st.multiselect("Seleziona Follow-up da confrontare:", fasi_followup, default=fasi_followup)
                    fasi_filtro = [baseline_label] + scelte_fu
                    
                    st_v_filt = st_val[st_val["Asse_X"].isin(fasi_filtro)]
                    
                    # Calcolo Delta Percentuale sulla riga Baseline (indice 0 del dataframe intero)
                    base_row = st_val.iloc[0]
                    st_perc = st_v_filt.copy()
                    
                    for c in [11, 12, 16, 17, 22, 23]:
                        bv = pd.to_numeric(base_row.iloc[c], errors='coerce')
                        st_perc.iloc[:, c] = ((pd.to_numeric(st_v_filt.iloc[:, c], errors='coerce') - bv) / bv * 100) if pd.notna(bv) and bv != 0 else 0.0

                    c_f, c_p = st.columns(2)
                    with c_f:
                        fig_f = go.Figure()
                        fig_f.add_trace(go.Scatter(x=st_perc["Asse_X"], y=st_perc.iloc[:, 16], name="Quad DX", mode='lines+markers'))
                        fig_f.add_trace(go.Scatter(x=st_perc["Asse_X"], y=st_perc.iloc[:, 22], name="Grip DX", mode='lines+markers', line=dict(dash='dash')))
                        fig_f.update_xaxes(categoryorder='array', categoryarray=fasi_filtro)
                        fig_f.update_layout(title="Variazione Forza (Delta %)", yaxis_title="%")
                        st.plotly_chart(fig_f, use_container_width=True)
                    with c_p:
                        fig_p = go.Figure()
                        fig_p.add_trace(go.Scatter(x=st_perc["Asse_X"], y=st_perc.iloc[:, 11], name="TUG (Tempo)", mode='lines+markers'))
                        fig_p.add_trace(go.Scatter(x=st_perc["Asse_X"], y=st_perc.iloc[:, 12], name="5xSTS", mode='lines+markers'))
                        fig_p.update_xaxes(categoryorder='array', categoryarray=fasi_filtro)
                        
                        # INVERSIONE ASSE Y (Variazione Funzionale Fisioterapista)
                        fig_p.update_yaxes(autorange="reversed")
                        fig_p.update_layout(title="Variazione Tempi Funzionali (Delta %)", yaxis_title="% Tempo (Linea su = Più veloce)")
                        st.plotly_chart(fig_p, use_container_width=True)

    elif sub_menu == "💾 Export Dati & Report PDF":
        st.subheader("Report e Database")
        c1, c2 = st.columns(2)
        with c1:
            st.download_button("Export Pazienti", df_paz.to_csv(index=False), "paz.csv", "text/csv")
            st.download_button("Export Valutazioni", df_val.to_csv(index=False), "val.csv", "text/csv")
        with c2:
            if lista_paz:
                p_pdf = st.selectbox("Paziente per PDF:", lista_paz)
                if st.button("Genera PDF"):
                    col_id_v = next((c for c in ["ID Paziente", "ID_Paziente"] if c in df_val.columns), df_val.columns[10] if len(df_val.columns)>10 else None)
                    paz = df_paz[df_paz[col_id].astype(str).str.strip() == p_pdf]
                    val = df_val[df_val[col_id_v].astype(str).str.strip() == p_pdf] if col_id_v and not df_val.empty else pd.DataFrame()
                    
                    figure_da_stampare = []
                    # Se ci sono dati, genero i grafici per il PDF in background
                    if not val.empty and len(val) > 0:
                        val["Ordine_X"] = val.iloc[:, 25].apply(estrai_ordine)
                        val = val.sort_values("Ordine_X")
                        val["Asse_X"] = val.apply(formatta_asse_x, axis=1)
                        f_pdf = go.Figure()
                        f_pdf.add_trace(go.Scatter(x=val["Asse_X"], y=pd.to_numeric(val.iloc[:, 16], errors='coerce'), name="Quad DX", mode='lines+markers'))
                        f_pdf.update_layout(title="Andamento Storico Quadricipite (Kg)")
                        figure_da_stampare.append(f_pdf)
                    
                    st.download_button("📥 Scarica Report PDF", data=genera_pdf_report(p_pdf, paz, val, figure_da_stampare), file_name=f"Report_{p_pdf}.pdf", mime="application/pdf")

# ==============================================================================
# AREA 3: PORTALE PAZIENTE
# ==============================================================================
elif modalita_principale == "🔐 Area Personale (Paziente)":
    st.title("🔐 Spazio Riabilitativo")
    df_p = leggi_dati_paziente()
    df_v = leggi_dati_valutazioni()
    
    if df_p.empty: st.warning("In aggiornamento.")
    else:
        cid = next((c for c in ["ID Paziente", "ID_Paziente"] if c in df_p.columns), df_p.columns[2])
        l_id = df_p[cid].dropna().astype(str).str.strip().unique().tolist()
        
        pid = st.text_input("Il tuo ID (es. RM50):").strip().upper()
        if pid in l_id:
            st.success(f"Benvenuto, {pid}!")
            cv = next((c for c in ["ID Paziente", "ID_Paziente"] if c in df_v.columns), df_v.columns[10])
            sv = df_v[df_v[cv].astype(str).str.strip() == pid].copy()
            
            if not sv.empty:
                sv["Ordine_X"] = sv.iloc[:, 25].apply(estrai_ordine)
                sv = sv.sort_values("Ordine_X")
                sv["Asse_X"] = sv.apply(formatta_asse_x, axis=1)
    
                # Pulizia: rimuoviamo righe con ordine 99 o senza data valida
                sv = sv[sv["Ordine_X"] != 99]
    
                fasi_disp = sv["Asse_X"].unique().tolist()
                # Cerchiamo la Baseline tra le fasi disponibili usando l'ordine
                b_label = next((f for f in sv[sv["Ordine_X"] == 1]["Asse_X"]), fasi_disp[0] if fasi_disp else "")
                fu_disp = [f for f in fasi_disp if f != b_label]

                scelte = st.multiselect("Confronta la Baseline con i tuoi follow-up:", fu_disp, default=fu_disp)
                fasi_grafici = [b_label] + scelte
                sv_filt = sv[sv["Asse_X"].isin(fasi_grafici)]
                
                c_1, c_2 = st.columns(2)
                with c_1:
                    fig_m = go.Figure()
                    fig_m.add_trace(go.Scatter(x=sv_filt["Asse_X"], y=pd.to_numeric(sv_filt.iloc[:, 11], errors='coerce'), name="Agilità (TUG)", mode="lines+markers"))
                    fig_m.update_xaxes(categoryorder='array', categoryarray=fasi_grafici)
                    fig_m.update_yaxes(autorange="reversed") # TUG Invertito (Meno tempo = più alto)
                    fig_m.update_layout(title="La tua Autonomia (Sempre più in alto!)")
                    st.plotly_chart(fig_m, use_container_width=True)
                with c_2:
                    fig_f = go.Figure()
                    fig_f.add_trace(go.Scatter(x=sv_filt["Asse_X"], y=pd.to_numeric(sv_filt.iloc[:, 22], errors='coerce'), name="Presa DX", mode="lines+markers"))
                    fig_f.update_xaxes(categoryorder='array', categoryarray=fasi_grafici)
                    fig_f.update_layout(title="La Forza delle tue Braccia (Kg)")
                    st.plotly_chart(fig_f, use_container_width=True)
            else: st.info("Dati in elaborazione.")
        elif pid: st.error("ID non valido.")
