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
    return conn.read(spreadsheet=URL_FOGLIO, worksheet="Dati_Paziente")

@st.cache_data(ttl=5)
def leggi_dati_valutazioni():
    return conn.read(spreadsheet=URL_FOGLIO, worksheet="Valutazioni_Studio")

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
        fase_completa = str(riga.iloc[25])
        
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
        v5 = st.slider("5. Quando mi arrabbio o mi spavento, fatico a calmarmi fisicamente", 1, 10, 5)
        v6 = st.slider("6. Quanto la fa sentire furioso/a l'idea di aver perso parte della sua mobilità?", 1, 10, 5)
        v7 = st.slider("7. Non avrei così tanto dolore se potessi controllare la mia mente", 1, 10, 5)
        v8 = st.slider("8. When si sente dolore, interrompe immediatamente qualsiasi attività?", 1, 10, 5)
        v9 = st.slider("9. Quanto crede che l'attività fisica sia sicura ed efficace per la sua salute?", 1, 10, 5)
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
        "📝 Registrazione Nuovi Test", 
        "📈 Analisi Longitudinale & Grafici", 
        "🧠 Analisi Multidimensionale (BPS)", 
        "🧫 Clinical Decision Support & Screening", 
        "💾 Export & Data Pipeline per la Ricerca"
    ], horizontal=True)
    st.markdown("---")

    df_paziente = leggi_dati_paziente()
    df_valutazioni = leggi_dati_valutazioni()
    
    lista_pazienti = df_paziente.iloc[:, 2].dropna().unique().tolist() if not df_paziente.empty else []

    if not lista_pazienti:
        st.warning("Nessun record presente nel database dei pazienti.")
    else:
        # ----------------------------------------------------------------------
        # SUB-AMBITO 1: REGISTRAZIONE NUOVI TEST CLINICI
        # ----------------------------------------------------------------------
        if sub_menu == "📝 Registrazione Nuovi Test":
            st.subheader("Inserimento Valutazione Funzionale Obiettiva")
            paz_scelto = st.selectbox("Seleziona ID Paziente target:", lista_pazienti)
            
            fc_max_tanaka = None
            storico_paz = df_paziente[df_paziente.iloc[:, 2] == paz_scelto]
            if not storico_paz.empty:
                sesso_paz = storico_paz.iloc[0, 5]
                eta_paz = int(storico_paz.iloc[0, 4])
                fc_max_tanaka = round(208 - (0.7 * eta_paz), 1)

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
                
                # INTEGRAZIONE COLONNE H e I DELLA FOTO CARICATA
                c_f4, c_f5, c_f6 = st.columns(3)
                with c_f4: tug = st.number_input("Timed Up & Go - TUG (secondi)", value=None, format="%.2f")
                with c_f5: sts_5x = st.number_input("5 Times Chair Stand - 5xSTS (secondi)", value=None, format="%.2f")
                with c_f6: sat_post = st.number_input("Saturazione O2 post test (%) [Col. H]", 50, 100, value=None)
                
                tempo_rec = st.number_input("Tempo di recupero (minuti) [Col. I]", value=None, step=1)

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
                # Strutturazione array rispettando: H=sat_post (7), I=tempo_rec (8), J="" (9, vuota per codice)
                riga_val_out = [
                    datetime.now().strftime("%d/%m/%Y %H.%M.%S"), pas, fc_rip, sat_rip, chair_30, step_30, fc_post, 
                    sat_post, tempo_rec, "", # <--- Indici 7, 8, 9 (Corrispondenti a H, I, J della foto)
                    paz_scelto, tug, sts_5x, sppb_eq, sppb_cam, sppb_ch, q_dx, q_sn, g_dx, g_sn, p_dx, p_sn, h_dx, h_sn, fc_max_tanaka, fase_test
                ]
                try:
                    df_aggiornato = pd.concat([df_valutazioni, pd.DataFrame([riga_val_out], columns=df_valutazioni.columns)], ignore_index=True)
                    conn.update(spreadsheet=URL_FOGLIO, worksheet="Valutazioni_Studio", data=df_aggiornato)
                    st.success("Test clinici memorizzati correttamente associando i dati ai rispettivi canali H, I, J.")
                    st.cache_data.clear()
                except Exception as e:
                    st.error(f"Errore nel salvataggio: {e}")

        # ----------------------------------------------------------------------
        # SUB-AMBITO 2: ANALISI LONGITUDINALE CON INDICATORI MDC
        # ----------------------------------------------------------------------
        elif sub_menu == "📈 Analisi Longitudinale & Grafici":
            st.subheader("Evoluzione Temporale e Verifica della Significatività Clinica (MDC)")
            paz_scelto = st.selectbox("Seleziona Patient da esaminare:", lista_pazienti)
            
            storico_val = df_valutazioni[df_valutazioni.iloc[:, 10] == paz_scelto].copy() if not df_valutazioni.empty else pd.DataFrame()
            
            if not storico_val.empty and len(storico_val) > 0:
                ordine_cronologico = {f: i for i, f in enumerate(OPZIONI_FASE)}
                storico_val["Ordine"] = storico_val.iloc[:, 25].map(ordine_cronologico)
                storico_val = storico_val.sort_values("Ordine")
                storico_val.index = storico_val.apply(formatta_asse_x, axis=1)
                
                val_baseline = storico_val.iloc[0]
                val_attuale = storico_val.iloc[-1]
                
                st.markdown("#### Verifiche del Cambiamento Clinico Rispetto alla Baseline")
                c_m1, c_m2, c_m3 = st.columns(3)
                
                sppb_base = sum([int(val_baseline.iloc[13]), int(val_baseline.iloc[14]), int(val_baseline.iloc[15])])
                sppb_att = sum([int(val_attuale.iloc[13]), int(val_attuale.iloc[14]), int(val_attuale.iloc[15])])
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

                tab_funz, tab_forza = st.tabs(["Performance Motorie", "Dinamometria di Forza"])
                with tab_funz:
                    st.write("**Evoluzione Test Funzionali Cronometrati (Secondi)**")
                    df_linee_tempi = storico_val.iloc[:, [11, 12]].copy()
                    df_linee_tempi.columns = ["Timed Up & Go (TUG)", "Test 5xSTS"]
                    st.line_chart(df_linee_tempi)
                with tab_forza:
                    st.write("**Evoluzione Forza Massima Isometrica (Kg)**")
                    df_linee_forza = storico_val.iloc[:, [16, 17, 22, 23]].copy()
                    df_linee_forza.columns = ["Quad DX (Kg)", "Quad SN (Kg)", "Handgrip DX (Kg)", "Handgrip SN (Kg)"]
                    st.line_chart(df_linee_forza)
            else:
                st.info("Dati insufficienti per generare analisi longitudinali per questo paziente.")

        # ----------------------------------------------------------------------
        # SUB-AMBITO 3: RAPPRESENTAZIONE GRAFICA MODELLO BIOPSICOSOCIALE (RADAR)
        # ----------------------------------------------------------------------
        elif sub_menu == "🧠 Analisi Multidimensionale (BPS)":
            st.subheader("Profilo Psicocomportamentale e Vissuto del Paziente")
            paz_scelto = st.selectbox("Seleziona ID Paziente:", lista_pazienti)
            
            storico_paz = df_paziente[df_paziente.iloc[:, 2] == paz_scelto].copy()
            if not storico_paz.empty:
                fasi_disponibili = storico_paz.iloc[:, 31].unique().tolist()
                fase_scelta = st.selectbox("Seleziona fase di screening da visualizzare:", fasi_disponibili)
                
                riga_mirata = storico_paz[storico_paz.iloc[:, 31] == fase_scelta].iloc[0]
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
                
                st.markdown("##### Interpretazione Clinica del Profilo:")
                if dimensioni["Kinesiofobia & Paura"] > 6:
                    st.warning("⚠️ **Livello elevato di Kinesiofobia:** Il paziente manifesta forti barriere cognitive al movimento. Priorità all'educazione neuroscientifica del dolore (PNE) e ad una progressione di carico altamente graduale (Graded Exposure).")
                if dimensioni["Accettazione (Framework ACT)"] < 4:
                    st.info("💡 **Bassa Accettazione Psicologica:** Sincronizzare l'allenamento con obiettivi di valore personali del paziente, integrando strategie di mindfulness e defusione per svincolare l'azione motoria dalla presenza del sintomo.")

        # ----------------------------------------------------------------------
        # SUB-AMBITO 4: ALGORITMI DI SCREENING AUTOMATIZZATI & CDS
        # ----------------------------------------------------------------------
        elif sub_menu == "🧫 Clinical Decision Support & Screening":
            st.subheader("Sistemi di Supporto Decisionale Clinico basati su Linee Guida")
            paz_scelto = st.selectbox("Seleziona Paziente:", lista_pazienti)
            
            storico_paz = df_paziente[df_paziente.iloc[:, 2] == paz_scelto]
            storico_val = df_valutazioni[df_valutazioni.iloc[:, 10] == paz_scelto]
            
            if not storico_paz.empty and not storico_val.empty:
                sesso_paz = storico_paz.iloc[0, 5]
                riga_ultima_val = storico_val.iloc[-1]
                
                esiti = esegui_screening_geriatrici(riga_ultima_val, sesso_paz)
                
                st.markdown("#### Stato delle Sindromi Geriatriche Intercettate")
                col_e1, col_e2, col_e3 = st.columns(3)
                with col_e1: st.error(f"**Sarcopenia (EWGSOP2):** \n\n {esiti['sarcopenia']}")
                with col_e2: st.warning(f"**Fenotipo Fragilità (Frailty):** \n\n {esiti['frailty']}")
                with col_e3: st.info(f"**Rischio Cadute:** \n\n {esiti['cadute']}")
                
                st.markdown("---")
                st.markdown("#### 📚 Suggerimenti per la Decisione Clinica (Evidence-Based Medicine)")
                sppb_punteggio = sum([int(riga_ultima_val.iloc[13]), int(riga_ultima_val.iloc[14]), int(riga_ultima_val.iloc[15])])
                
                if sppb_punteggio < 7:
                    st.markdown("> **⚠️ LIMITAZIONE FUNZIONALE GRAVE (SPPB < 7):** Le linee guida raccomandano l'impostazione immediata di un programma multicomponente focalizzato sulla sicurezza. Priorità assoluta ad esercizi di stabilità posturale e controllo dell'equilibrio in ambiente protetto, affiancati da rinforzo progressivo degli estensori di ginocchio sub-massimale.")
                elif 7 <= sppb_punteggio <= 9:
                    st.markdown("> **💡 LIMITAZIONE MODERATA (SPPB 7-9):** Indicazione clinica per allenamento di forza progressivo a medio-alta intensità (60-70% 1RM o RPE 7/10 sulla scala Borg). Integrare percorsi di cammino a velocità variabile ed ostacoli per stimolare la riserva motoria.")
                else:
                    st.markdown("> **✅ BUONA CAPACITÀ FUNZIONALE (SPPB >= 10):** Focus sul mantenimento e sulla prevenzione primaria. È possibile inserire esercizi di potenza ad alta velocità esecutiva (Power Training) e compiti complessi a doppio compito (Dual-Task) per ottimizzare la resilienza neuro-motoria.")

        # ----------------------------------------------------------------------
        # SUB-AMBITO 5: ESPORTAZIONE DATASET ANONIMIZZATO PER SOFTWARE STATISTICI
        # ----------------------------------------------------------------------
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
                        df_wide = df_ricerca_long.pivot(index="ID_Paziente_Anonimo", columns=df_ricerca_long.columns[25])
                        df_wide.columns = [f"{col[0]}_{col[1]}" for col in df_wide.columns]
                        df_wide.reset_index(inplace=True)
                        csv_data_wide = df_wide.to_csv(index=False).encode('utf-8')
                        st.download_button("📥 Scarica Dataset WIDE .CSV", data=csv_data_wide, file_name="dataset_ricerca_geriatrica_WIDE.csv", mime="text/csv")
                        st.dataframe(df_wide.head())
                    except Exception as e:
                        st.error(f"Errore nella strutturazione del formato WIDE (Verifica che non ci siano duplicati della stessa fase per lo stesso paziente): {e}")

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
        
        if not df_paziente.empty and id_input in df_paziente.iloc[:, 2].values:
            st.success("✅ Autenticazione riuscita! Benvenuto nella tua area personale.")
            st.markdown("---")
            
            storico_val_paz = df_valutazioni[df_valutazioni.iloc[:, 10] == id_input].copy() if not df_valutazioni.empty else pd.DataFrame()
            
            st.subheader("📈 L'Evoluzione dei tuoi Risultati nel Tempo")
            
            if not storico_val_paz.empty and len(storico_val_paz) > 0:
                ordine_cronologico = {f: i for i, f in enumerate(OPZIONI_FASE)}
                storico_val_paz["Ordine"] = storico_val_paz.iloc[:, 25].map(ordine_cronologico)
                storico_val_paz = storico_val_paz.sort_values("Ordine")
                
                def etichetta_paziente(riga):
                    fase = str(riga.iloc[25])
                    if "Baseline" in fase: return "Inizio Percorso"
                    elif "3" in fase: return "Dopo 3 Mesi"
                    elif "6" in fase: return "Dopo 6 Mesi"
                    elif "9" in fase: return "Dopo 9 Mesi"
                    elif "12" in fase: return "Dopo 12 Mesi"
                    return fase
                storico_val_paz.index = storico_val_paz.apply(etichetta_paziente, axis=1)
                
                c_p1, c_p2 = st.columns(2)
                
                with c_p1:
                    st.write("##### 🪑 Capacità di Alzarsi dalla Sedia (Più ripetizioni indicano più forza)")
                    df_sedia = storico_val_paz.iloc[:, [4]].copy()
                    df_sedia.columns = ["Numero di ripetizioni in 30 secondi"]
                    st.line_chart(df_sedia)
                    
                with c_p2:
                    st.write("##### 🚶 Velocità e Sicurezza nel Cammino (Meno secondi indicano maggiore agilità)")
                    df_tug_paz = storico_val_paz.iloc[:, [11]].copy()
                    df_tug_paz.columns = ["Tempo impiegato nei test (Secondi)"]
                    st.line_chart(df_tug_paz)
                
                st.markdown("---")
                st.info("🎯 **Nota del Team Medico:** I tuoi grafici mostrano l'impegno che stai mettendo nelle sessioni riabilitative. Piccoli e costanti miglioramenti nel tempo rappresentano la chiave per conservare un'ottima autonomia e ridurre il rischio di cadute nelle attività di tutti i giorni. Continua così!")
            else:
                st.warning("I tuoi test clinici iniziali sono in fase di elaborazione. Saranno visibili non appena il fisioterapista completerà l'inserimento della prima sessione.")
        else:
            st.error("Codice Identificativo non trovato nel database dello studio. Verifica con il tuo terapeuta.")
