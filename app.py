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

# Helper robusto per trovare la colonna ID in base al nome
def get_id_col(df):
    for col in ["ID Paziente", "ID paziente", "ID_Paziente", "id paziente"]:
        if col in df.columns: return col
    return df.columns[2] if len(df.columns) > 2 else None

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
        "intensita_perc": 0.5,
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

    # Calcolo Scheda Carichi Reali basato su nomi di colonna
    perc = piano["intensita_perc"]
    f_q_dx = pd.to_numeric(test_funzionali.get("Estensori di Ginocchio (Quadricipite) - DX (Kg)", 0), errors='coerce')
    f_q_sn = pd.to_numeric(test_funzionali.get("Estensori di Ginocchio (Quadricipite) - SN (Kg)", 0), errors='coerce')
    f_h_dx = pd.to_numeric(test_funzionali.get("Handgrip mano destra", 0), errors='coerce')
    
    if pd.notna(f_q_dx) and f_q_dx > 0:
        piano["scheda_carichi_reali"].append({"Distretto": "Estensori Ginocchio DX", "Esercizio Macchina": "Leg Extension DX", "Carico Stimato": f"{round(f_q_dx * perc, 1)} Kg", "Serie x Rip": piano["volume_forza"]})
    if pd.notna(f_q_sn) and f_q_sn > 0:
        piano["scheda_carichi_reali"].append({"Distretto": "Estensori Ginocchio SN", "Esercizio Macchina": "Leg Extension SN", "Carico Stimato": f"{round(f_q_sn * perc, 1)} Kg", "Serie x Rip": piano["volume_forza"]})
    if pd.notna(f_h_dx) and f_h_dx > 0:
        piano["scheda_carichi_reali"].append({"Distretto": "Tirata / Grip", "Esercizio Macchina": "Rowing / Lat Machine", "Carico Stimato": f"{round(f_h_dx * perc, 1)} Kg", "Serie x Rip": piano["volume_forza"]})

    if pd.notna(f_q_dx) and pd.notna(f_q_sn) and max(f_q_dx, f_q_sn) > 0:
        if max(f_q_dx, f_q_sn) < 10 or abs(f_q_dx - f_q_sn) > max(f_q_dx, f_q_sn)*0.2:
            piano["focus_fisioterapista"].append("Priorità all'ipertrofia arti inferiori (Deficit rilevato).")

    return piano

def renderizza_sezione_fisioterapista(df_pazienti, df_valutazioni):
    st.header("🦾 Progressione Senior (NSCA & Aerobic Power)")
    
    if df_pazienti.empty:
        st.warning("Nessun dato paziente disponibile.")
        return

    col_id = get_id_col(df_pazienti)
    if not col_id: return
    
    paz_selezionato = st.selectbox("Seleziona Paziente:", df_pazienti[col_id].dropna().astype(str).str.strip().unique().tolist(), key="sb_nsca")
    
    if paz_selezionato:
        storico_paz = df_pazienti[df_pazienti[col_id].astype(str).str.strip() == paz_selezionato]
        col_id_val = get_id_col(df_valutazioni)
        storico_val = df_valutazioni[df_valutazioni[col_id_val].astype(str).str.strip() == paz_selezionato] if col_id_val and not df_valutazioni.empty else pd.DataFrame()

        if not storico_paz.empty:
            ult_paz = storico_paz.iloc[-1]
            ult_val = storico_val.iloc[-1] if not storico_val.empty else pd.Series()
            
            # Estrazione sicura usando i nomi esatti del CSV
            pat_raw = (str(ult_paz.get("Patologie Sistemiche", "")) + " " + str(ult_paz.get("Condizioni Meccaniche", ""))).lower()
            pat_attive = [p for p in ["ipertensione", "cardiopatia", "osteoporosi", "artrosi"] if p in pat_raw]

            frag_max = max(np.nan_to_num(pd.to_numeric(ult_paz.get("V12_Paura_Cadere", 0), errors='coerce')), 
                           np.nan_to_num(pd.to_numeric(ult_paz.get("V13_Instabilita_Gambe", 0), errors='coerce')))
            
            dist_max = max(np.nan_to_num(pd.to_numeric(ult_paz.get("V9_Paura_Danno_Esercizio", 0), errors='coerce')), 
                           np.nan_to_num(pd.to_numeric(ult_paz.get("Dolore NRS", 0), errors='coerce')))
            
            r_cad = "alto" if frag_max >= 7 else ("medio" if frag_max >= 4 else "basso")

            ris = genera_progressione_senior(
                {"patologie": pat_attive, "rischio_caduta": r_cad, "fragilita_percepita": frag_max, "distress_emotivo": dist_max, "esperienza_allenamento": "novizio"}, 
                ult_val
            )

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
    try:
        k = float(kinesiofobia)
        p = float(paura_cadute)
    except:
        k, p = 5, 5
    indice_prudenza = (k + p) / 2
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
    return 99

def formatta_asse_x(riga):
    try:
        data = str(riga.get("Informazioni cronologiche", riga.iloc[0])).split()[0]
        fase = str(riga.get("Fase_Valutazione", "N/D")).strip()
        ord_num = estrai_ordine(fase)
        mappa = {"baseline": "Baseline", "3": "3M", "6": "6M", "9": "9M", "12": "12M"}
        f_brev = next((b for k, b in mappa.items() if k in fase.lower()), fase)
        return f"{ord_num}. {data} ({f_brev})"
    except: return "N/D"

def calcola_dimensioni_biopsicosociali(riga):
    try:
        # Estrazione diretta dai nomi colonna CSV
        kinesio = np.nanmean([pd.to_numeric(riga.get("V10_Evitamento_Dolore", np.nan), errors='coerce'), pd.to_numeric(riga.get("V11_Fatica_Quotidiana", np.nan), errors='coerce'), pd.to_numeric(riga.get("V12_Paura_Cadere", np.nan), errors='coerce'), pd.to_numeric(riga.get("V17_Controllo_Totale_Dolore", np.nan), errors='coerce')])
        accet = np.nanmean([pd.to_numeric(riga.get("V3_Pensieri_Insignificanti", np.nan), errors='coerce'), pd.to_numeric(riga.get("V7_Credenza_Pericolo_Corpo", np.nan), errors='coerce'), pd.to_numeric(riga.get("V8_Ruminazione_Dolore", np.nan), errors='coerce'), pd.to_numeric(riga.get("V15_Dolore_Non_Insurmontabile", np.nan), errors='coerce')])
        autof = np.nanmean([pd.to_numeric(riga.get("V1_Appetito", np.nan), errors='coerce'), pd.to_numeric(riga.get("V2_Serenita", np.nan), errors='coerce'), pd.to_numeric(riga.get("V9_Paura_Danno_Esercizio", np.nan), errors='coerce'), pd.to_numeric(riga.get("V16_Vita_Piena_Dolore", np.nan), errors='coerce')])
        impatto = np.nanmean([pd.to_numeric(riga.get("V13_Instabilita_Gambe", np.nan), errors='coerce'), pd.to_numeric(riga.get("V14_Autoefficacia_Attiva", np.nan), errors='coerce'), pd.to_numeric(riga.get("V18_Aderenza_Terapia", np.nan), errors='coerce')])
        
        return {
            "Kinesiofobia": round(kinesio, 2),
            "Accettazione PACT": round(accet, 2),
            "Autoefficacia": round(autof, 2),
            "Percezione Stato": round(impatto, 2)
        }
    except: return {"Kinesiofobia": 0, "Accettazione PACT": 0, "Autoefficacia": 0, "Percezione Stato": 0}

def esegui_screening_geriatrici(riga_val, sesso):
    out = {"sarcopenia": "Verde", "frailty": "Verde", "cadute": "Verde"}
    try:
        hg_dx = pd.to_numeric(riga_val.get("Handgrip mano destra", 0), errors='coerce')
        hg_sn = pd.to_numeric(riga_val.get("Handgrip mano sinistra", 0), errors='coerce')
        max_hg = max(np.nan_to_num(hg_dx), np.nan_to_num(hg_sn))
        
        tug = pd.to_numeric(riga_val.get("Tempo di esecuzione del Time Up&Go (TUG)", 0), errors='coerce')
        sts = pd.to_numeric(riga_val.get("Tempo di esecuzione del 5xSTS (in secondi)", 0), errors='coerce')
        
        sppb = sum([
            np.nan_to_num(pd.to_numeric(riga_val.get("SPPB [Test di Equilibrio Totale]", 0), errors='coerce')), 
            np.nan_to_num(pd.to_numeric(riga_val.get("SPPB [Velocità del Cammino su 4 metri]", 0), errors='coerce')), 
            np.nan_to_num(pd.to_numeric(riga_val.get("SPPB [Chair Stand Test]", 0), errors='coerce'))
        ])
        
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
        sesso = str(rec.get("Sesso Biologico", "Donna"))
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 8, "1. Dati Anagrafici e Clinici:", ln=True)
        pdf.set_font("Arial", '', 11)
        pdf.cell(0, 6, f"Sesso: {sesso} | Eta': {rec.get('Età del paziente', 'N/D')}", ln=True)
        pdf.cell(0, 6, f"Patologie: {rec.get('Patologie Sistemiche', 'N/D')}", ln=True)
        pdf.ln(5)
        
    if not df_val.empty:
        rec = df_val.iloc[-1]
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 8, "2. Ultima Valutazione Funzionale:", ln=True)
        pdf.set_font("Arial", '', 11)
        pdf.cell(0, 6, f"Data: {rec.get('Informazioni cronologiche', 'N/D')} | TUG: {rec.get('Tempo di esecuzione del Time Up&Go (TUG)', 'N/D')} s | 5xSTS: {rec.get('Tempo di esecuzione del 5xSTS (in secondi)', 'N/D')} s", ln=True)
        pdf.cell(0, 6, f"Quadricipite (DX/SN): {rec.get('Estensori di Ginocchio (Quadricipite) - DX (Kg)', 'N/D')} / {rec.get('Estensori di Ginocchio (Quadricipite) - SN (Kg)', 'N/D')} Kg", ln=True)
        pdf.ln(5)
        
        esiti = esegui_screening_geriatrici(rec, sesso)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 8, "3. Screening Geriatrico:", ln=True)
        pdf.set_font("Arial", '', 11)
        pdf.cell(0, 6, f"Sarcopenia: {esiti['sarcopenia']}", ln=True)
        pdf.cell(0, 6, f"Fragilita': {esiti['frailty']}", ln=True)
        pdf.cell(0, 6, f"Rischio Cadute: {esiti['cadute']}", ln=True)
        pdf.ln(5)

    if figure_grafici:
        for fig in figure_grafici:
            img_path = salva_fig_temp(fig)
            if img_path:
                pdf.add_page()
                pdf.image(img_path, x=10, w=190)
                os.remove(img_path) 
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
        with c3: sesso = st.selectbox("Sesso Biologico:", ["Uomo", "Donna"])
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
            
            # Utilizzo dizionario con i NOMI esatti delle colonne del database
            riga_dict = {
                "Informazioni cronologiche": datetime.now().strftime("%d/%m/%Y %H.%M.%S"),
                "Consenso al trattamento dei dati sanitari:": col_consenso,
                "ID paziente": id_gen,
                "Chi sta compilando questo modulo?": col_compilatore,
                "Età del paziente": eta,
                "Sesso Biologico": sesso,
                "Situazione abitativa": situazione_abitativa,
                "Condizioni Meccaniche": ", ".join(condizioni_mecc),
                "Patologie Sistemiche": ", ".join(condizioni_sist),
                "Sintomi Red Flags": ", ".join(sintomi_red),
                "Dolore NRS": dolore_nrs,
                "Farmaci": farmaci,
                "V1_Appetito": v1,
                "V2_Serenita": v2,
                "V3_Pensieri_Insignificanti": v3,
                "V4_Carattere_Irascibile": v4,
                "V5_Perdita_Controllo": v5,
                "V6_Disagio_Critiche": v6,
                "V7_Credenza_Pericolo_Corpo": v7,
                "V8_Ruminazione_Dolore": v8,
                "V9_Paura_Danno_Esercizio": v9,
                "V10_Evitamento_Dolore": v10,
                "V11_Fatica_Quotidiana": v11,
                "V12_Paura_Cadere": v12,
                "V13_Instabilita_Gambe": v13,
                "V14_Autoefficacia_Attiva": v14,
                "V15_Dolore_Non_Insurmontabile": v15,
                "V16_Vita_Piena_Dolore": v16,
                "V17_Controllo_Totale_Dolore": v17,
                "V18_Aderenza_Terapia": v18,
                "Specifiche_Quadro_Clinico": specifiche_cliniche,
                "Fase_Valutazione": fase_paziente
            }

            try:
                # Creazione nuovo dataframe solo con le colonne necessarie
                nuova_riga_df = pd.DataFrame([riga_dict])
                df_aggiornato = pd.concat([df_paziente, nuova_riga_df], ignore_index=True)
                df_aggiornato = df_aggiornato[df_paziente.columns] # Allinea perfettamente le colonne
                
                conn.update(spreadsheet=URL_FOGLIO, worksheet="Dati_Paziente", data=df_aggiornato)
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
    col_id = get_id_col(df_paz)
    lista_paz = df_paz[col_id].dropna().astype(str).str.strip().unique().tolist() if not df_paz.empty and col_id else []

    if sub_menu == "🦾 Progressione Senior (NSCA)": renderizza_sezione_fisioterapista(df_paz, df_val)

    elif sub_menu == "📝 Registrazione Nuovi Test":
        if not lista_paz: st.warning("Nessun paziente.")
        else:
            p_scelto = st.selectbox("Paziente:", lista_paz)
            storico = df_paz[df_paz[col_id].astype(str).str.strip() == p_scelto]
            fc_max = round(208 - (0.7 * int(storico.iloc[0].get("Età del paziente", 0))), 1) if not storico.empty else None

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
                    hsn = st.number_input("Handgrip SN", value=None)
                    fasn = st.number_input("Forza flessori anca SN", value=None)
                    easn = st.number_input("Forza estensori anca SN", value=None)
                    absn = st.number_input("Forza abduttori anca SN", value=None)
                    estgsn = st.number_input("Forza estensori ginocchio SN", value=None)
                    fgsn = st.number_input("Forza flessori ginocchio SN", value=None)
                    fdsn = st.number_input("Forza flessori dorsali SN", value=None)
                    fpsn = st.number_input("Forza flessori plantari SN", value=None)
                with c14:
                    hdx = st.number_input("Handgrip DX", value=None)
                    fadx = st.number_input("Forza flessori anca DX", value=None)
                    eadx = st.number_input("Forza estensori anca DX", value=None)
                    abdx = st.number_input("Forza abduttori anca DX", value=None)
                    estgdx = st.number_input("Forza estensori ginocchio DX", value=None)
                    fgdx = st.number_input("Forza flessori ginocchio DX", value=None)
                    fddx = st.number_input("Forza flessori dorsali DX", value=None)
                    fpdx = st.number_input("Forza flessori plantari DX", value=None)

                if st.form_submit_button("Salva Test"):
                    # Mappatura Esatta dei Nomi Colonna
                    val_dict = {
                        "Informazioni cronologiche": datetime.now().strftime("%d/%m/%Y %H.%M.%S"),
                        "Pressione Arteriosa Sistolica a riposo (mmHg)": pas,
                        "Frequenza Cardiaca a Riposo": fc,
                        "Saturazione O2 a riposo": sat,
                        "30-Second Chair stand test (n°rep)": ch30,
                        "30-Second Step test (n°rep)": step,
                        "Frequenza cardiaca post test": fcp,
                        "Saturazione O2 post test (%)": satp,
                        "Tempo di recupero": rec,
                        "ID Paziente": p_scelto,
                        "Tempo di esecuzione del Time Up&Go (TUG)": tug,
                        "Tempo di esecuzione del 5xSTS (in secondi)": sts5,
                        "SPPB [Test di Equilibrio Totale]": seq,
                        "SPPB [Velocità del Cammino su 4 metri]": scam,
                        "SPPB [Chair Stand Test]": sch,
                        "Estensori di Ginocchio (Quadricipite) - DX (Kg)": estgdx,
                        "Estensori di Ginocchio (Quadricipite) - SN (Kg)": estgsn,
                        "Abduttori d'Anca (Medio Gluteo) - DX (Kg)": abdx,
                        "Abduttori d'Anca (Medio Gluteo) - SN (Kg)": absn,
                        "Flessori d'Anca (Iliopsoas) - DX (Kg)": fadx,
                        "Flessori d'Anca (Iliopsoas) - SN (Kg)": fasn,
                        "Estensori d'anca - DX (Kg)": eadx,
                        "Estensori d'anca - SN (Kg)": easn,
                        "Flessori ginocchio - DX (Kg)": fgdx,
                        "Flessori ginocchio - SN (Kg)": fgsn,
                        "Flessori dorsali - DX (Kg)": fddx,
                        "Flessori dorsali - SN (Kg)": fdsn,
                        "Flessori plantari - DX (Kg)": fpdx,
                        "Flessori plantari - SN (Kg)": fpsn,
                        "Handgrip mano sinistra": hsn,
                        "Handgrip mano destra": hdx,
                        "FC_Max_Teorica_Tanaka": fc_max,
                        "Fase_Valutazione": fase
                    }

                    try:
                        nuova_riga_val_df = pd.DataFrame([val_dict])
                        df_val_aggiornato = pd.concat([df_val, nuova_riga_val_df], ignore_index=True)
                        df_val_aggiornato = df_val_aggiornato[df_val.columns] # Allinea
                        
                        conn.update(spreadsheet=URL_FOGLIO, worksheet="Valutazioni_Studio", data=df_val_aggiornato)
                        st.success("Test Salvato."); st.cache_data.clear()
                    except Exception as e: st.error(e)

    elif sub_menu == "🧠 Analisi Multidimensionale & Longitudinale":
        if not lista_paz: st.warning("Nessun paziente registrato.")
        else:
            paz_scelto = st.selectbox("Analizza Paziente:", lista_paz, key="sb_multi")
            st_paz = df_paz[df_paz[col_id].astype(str).str.strip() == paz_scelto]
            
            col_id_v = get_id_col(df_val)
            df_v_clean = df_val.dropna(subset=[col_id_v, "Fase_Valutazione"]) if not df_val.empty else pd.DataFrame()
            st_val = df_v_clean[df_v_clean[col_id_v].astype(str).str.strip() == paz_scelto].copy() if not df_v_clean.empty else pd.DataFrame()

            t_bps, t_cds, t_long = st.tabs(["🧠 Radar PACT", "🧫 Screening", "📈 Evoluzione Funzionale"])
            
            with t_bps:
                if not st_paz.empty:
                    f_scelta = st.selectbox("Fase BPS:", st_paz.get("Fase_Valutazione", pd.Series()).dropna().unique())
                    dim = calcola_dimensioni_biopsicosociali(st_paz[st_paz["Fase_Valutazione"] == f_scelta].iloc[0])
                    cat, val = list(dim.keys()) + [list(dim.keys())[0]], list(dim.values()) + [list(dim.values())[0]]
                    
                    fig = go.Figure(go.Scatterpolar(r=val, theta=cat, fill='toself'))
                    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 10])))
                    st.plotly_chart(fig, use_container_width=True)
                else: st.info("Dati assenti.")

            with t_cds:
                if not st_paz.empty and not st_val.empty:
                    esiti = esegui_screening_geriatrici(st_val.iloc[-1], st_paz.iloc[-1].get("Sesso Biologico", "Donna"))
                    for cat, v in esiti.items():
                        if "Rosso" in v: st.error(f"**{cat.upper()}:** {v}")
                        elif "Giallo" in v: st.warning(f"**{cat.upper()}:** {v}")
                        else: st.success(f"**{cat.upper()}:** {v}")
                else: st.info("Servono test completi.")

            with t_long:
                if not st_val.empty and len(st_val) > 0:
                    st_val["Ordine_X"] = st_val["Fase_Valutazione"].apply(estrai_ordine)
                    st_val = st_val[st_val["Ordine_X"] != 99].sort_values("Ordine_X")
                    st_val["Asse_X"] = st_val.apply(formatta_asse_x, axis=1)
                    
                    fasi_disp = st_val["Asse_X"].unique().tolist()
                    b_label = next((f for f in st_val[st_val["Ordine_X"] == 1]["Asse_X"]), fasi_disp[0] if fasi_disp else "")
                    fasi_followup = [f for f in fasi_disp if f != b_label]
                    
                    scelte_fu = st.multiselect("Seleziona Follow-up da confrontare:", fasi_followup, default=fasi_followup)
                    fasi_filtro = [b_label] + scelte_fu
                    
                    st_v_filt = st_val[st_val["Asse_X"].isin(fasi_filtro)]
                    
                    if not st_v_filt.empty:
                        base_row = st_val[st_val["Ordine_X"] == 1].iloc[0] if len(st_val[st_val["Ordine_X"] == 1]) > 0 else st_v_filt.iloc[0]
                        st_perc = st_v_filt.copy()
                        
                        col_analisi = {
                            "Flessori d'Anca (Iliopsoas) - DX (Kg)": "Flex Anca DX",
                            "Flessori d'Anca (Iliopsoas) - SN (Kg)": "Flex Anca SN",
                            "Estensori d'anca - DX (Kg)": "Est Anca DX",
                            "Estensori d'anca - SN (Kg)": "Est Anca SN",
                            "Abduttori d'Anca (Medio Gluteo) - DX (Kg)": "Abd Anca DX",
                            "Abduttori d'Anca (Medio Gluteo) - SN (Kg)": "Abd Anca SN",
    
                            # Dinamometria - Ginocchio
                            "Estensori di Ginocchio (Quadricipite) - DX (Kg)": "Est g DX",
                            "Estensori di Ginocchio (Quadricipite) - SN (Kg)": "Est g SN",
                            "Flessori ginocchio - DX (Kg)": "Flex g DX",
                            "Flessori ginocchio - SN (Kg)": "Flex g SN",
    
                            # Dinamometria - Caviglia
                            "Flessori dorsali - DX (Kg)": "Flex dors DX",
                            "Flessori dorsali - SN (Kg)": "Flex dors SN",
                            "Flessori plantari - DX (Kg)": "Flex plan DX",
                            "Flessori plantari - SN (Kg)": "Flex plan SN",
                            
                            "Handgrip mano destra": "Grip DX",
                            "Handgrip mano sinistra": "Grip SN",
                            
                            
                        }

                        col_analisi2 = {
                            "Tempo di esecuzione del Time Up&Go (TUG)": "TUG",
                            "Tempo di esecuzione del 5xSTS (in secondi)": "STS"
                        }
                        
                        
                        for c_name in col_analisi.keys():
                            bv = pd.to_numeric(base_row.get(c_name, np.nan), errors='coerce')
                            if pd.notna(bv) and bv != 0:
                                st_perc[c_name] = ((pd.to_numeric(st_v_filt[c_name], errors='coerce') - bv) / bv * 100)
                            else:
                                st_perc[c_name] = 0.0

                        c_f, c_p = st.columns(2)
                        with c_f:
                            fig_f = go.Figure()
    
                            # Ciclo automatico su tutte le variabili e targhette definite in col_analisi
                            for col_excel, targhetta in col_analisi.items():
                                if col_excel in st_perc.columns:
                                    fig_f.add_trace(
                                        go.Scatter(
                                            x=st_perc["Asse_X"], 
                                            y=pd.to_numeric(st_perc[col_excel], errors='coerce'), 
                                            name=targhetta, 
                                            mode='lines+markers'
                                        )
                                    )
    
                        # Configurazione degli assi e del layout
                        fig_f.update_xaxes(categoryorder='array', categoryarray=fasi_filtro)
                        fig_f.update_layout(
                            title="Variazione Forza Muscolare", 
                            yaxis_title="%",
                            legend_orientation="h",  # Posiziona la legenda in orizzontale sotto al grafico per non stringere lo spazio
                            legend=dict(y=-0.2, x=0.5, xanchor='center')
                        )
    
                        # Mostra il grafico su Streamlit
                        st.plotly_chart(fig_f, use_container_width=True)

                        with c_p:
                            fig_p = go.Figure()
    
                            # Ciclo automatico sulle variabili di tempo definite in col_analisi2
                            for col_excel, targhetta in col_analisi2.items():
                                if col_excel in st_perc.columns:
                                    fig_p.add_trace(
                                        go.Scatter(
                                            x=st_perc["Asse_X"], 
                                            y=pd.to_numeric(st_perc[col_excel], errors='coerce'), 
                                            name=targhetta, 
                                            mode='lines+markers'
                                        )
                                    )
    
                            # Configurazione assi e layout specifico per i tempi
                            fig_p.update_xaxes(categoryorder='array', categoryarray=fasi_filtro)
                            fig_p.update_yaxes(autorange="reversed")  # Meno tempo = grafico va verso l'alto
    
                            fig_p.update_layout(
                                title="Variazione Tempi Funzionali (Delta %)", 
                                yaxis_title="% Tempo (Linea in alto = Più veloce)",
                                legend_orientation="h",
                                legend=dict(y=-0.2, x=0.5, xanchor='center')
                            )
    
                            # Mostra il grafico su Streamlit
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
                    col_id_v = get_id_col(df_val)
                    paz = df_paz[df_paz[col_id].astype(str).str.strip() == p_pdf]
                    val = df_val[df_val[col_id_v].astype(str).str.strip() == p_pdf] if col_id_v and not df_val.empty else pd.DataFrame()
                    
                    figure_da_stampare = []
                    if not val.empty and len(val) > 0:
                        val["Ordine_X"] = val.get("Fase_Valutazione", pd.Series()).apply(estrai_ordine)
                        val = val[val["Ordine_X"] != 99].sort_values("Ordine_X")
                        val["Asse_X"] = val.apply(formatta_asse_x, axis=1)
                        f_pdf = go.Figure()
                        f_pdf.add_trace(go.Scatter(x=val["Asse_X"], y=pd.to_numeric(val.get("Estensori di Ginocchio (Quadricipite) - DX (Kg)", 0), errors='coerce'), name="Quad DX", mode='lines+markers'))
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
        cid = get_id_col(df_p)
        l_id = df_p[cid].dropna().astype(str).str.strip().unique().tolist()
        
        pid = st.text_input("Il tuo ID (es. RM50):").strip().upper()
        if pid in l_id:
            st.success(f"Benvenuto, {pid}!")
            cv = get_id_col(df_v)
            sv = df_v[df_v[cv].astype(str).str.strip() == pid].copy() if cv and not df_v.empty else pd.DataFrame()
            
            if not sv.empty and len(sv) > 0:
                sv["Ordine_X"] = sv.get("Fase_Valutazione", pd.Series()).apply(estrai_ordine)
                sv = sv[sv["Ordine_X"] != 99].sort_values("Ordine_X")
                sv["Asse_X"] = sv.apply(formatta_asse_x, axis=1)
                
                fasi_disp = sv["Asse_X"].unique().tolist()
                b_label = next((f for f in sv[sv["Ordine_X"] == 1]["Asse_X"]), fasi_disp[0] if fasi_disp else "")
                fu_disp = [f for f in fasi_disp if f != b_label]
                
                scelte = st.multiselect("Confronta la Baseline con i tuoi follow-up:", fu_disp, default=fu_disp)
                fasi_grafici = [b_label] + scelte
                sv_filt = sv[sv["Asse_X"].isin(fasi_grafici)]
                
                c_1, c_2 = st.columns(2)
                with c_1:
                    fig_m = go.Figure()
                    fig_m.add_trace(go.Scatter(x=sv_filt["Asse_X"], y=pd.to_numeric(sv_filt.get("Tempo di esecuzione del Time Up&Go (TUG)", 0), errors='coerce'), name="Agilità (TUG)", mode="lines+markers"))
                    fig_m.update_xaxes(categoryorder='array', categoryarray=fasi_grafici)
                    fig_m.update_yaxes(autorange="reversed")
                    fig_m.update_layout(title="La tua Autonomia (Sempre più in alto!)")
                    st.plotly_chart(fig_m, use_container_width=True)
                with c_2:
                    fig_f = go.Figure()
                    fig_f.add_trace(go.Scatter(x=sv_filt["Asse_X"], y=pd.to_numeric(sv_filt.get("Handgrip mano destra", 0), errors='coerce'), name="Presa DX", mode="lines+markers"))
                    fig_f.update_xaxes(categoryorder='array', categoryarray=fasi_grafici)
                    fig_f.update_layout(title="La Forza delle tue Braccia (Kg)")
                    st.plotly_chart(fig_f, use_container_width=True)
            else: st.info("Dati in elaborazione.")
        elif pid: st.error("ID non valido.")
