import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Hub Clinico - Valutazione Anziani", layout="wide")

# ==============================================================================
# GESTIONE DELLO STATO (LOGIN PERSISTENTE)
# ==============================================================================
if "fiso_auth" not in st.session_state:
    st.session_state.fiso_auth = False

# ==============================================================================
# CONNESSIONE E FUNZIONI DI LETTURA
# ==============================================================================
conn = st.connection("gsheets", type=GSheetsConnection)
URL_FOGLIO = "https://docs.google.com/spreadsheets/d/1qbCAMeOUKI23gq3p8g95JSwESI6-tF7mvUp8Mg0Z4Jk/edit"

@st.cache_data(ttl=10)
def leggi_dati_paziente():
    return conn.read(spreadsheet=URL_FOGLIO, worksheet="Dati_Paziente")

@st.cache_data(ttl=10)
def leggi_dati_valutazioni():
    return conn.read(spreadsheet=URL_FOGLIO, worksheet="Valutazioni_Studio")

def genera_feedback_empatico(kinesiofobia, paura_cadute):
    indice_prudenza = (kinesiofobia + paura_cadute) / 2
    if indice_prudenza < 4:
        titolo, testo, tipo = "Hai una buona consapevolezza del tuo corpo!", "Continua a mantenerti attivo/a come stai facendo. La tua sicurezza nei movimenti è un ottimo punto di partenza per conservare l'autonomia.", "success"
    elif 4 <= indice_prudenza < 7:
        titolo, testo, tipo = "Alcuni aspetti richiedono attenzione", "Abbiamo notato che talvolta senti un po' di timore nel muoverti liberamente. È normale, ma possiamo lavorarci insieme. Una valutazione completa ci aiuterà a capire come farti sentire più sicuro/a in ogni situazione quotidiano.", "info"
    else:
        titolo, testo, tipo = "Costruiamo insieme la tua sicurezza", "Capiamo che muoversi possa sembrarti faticoso o rischioso in questo momento. Il nostro obiettivo è aiutarti a ritrovare fiducia nelle tue gambe. Ti suggeriamo vivamente un incontro per definire insieme piccoli passi verso una maggiore autonomia.", "warning"
    return titolo, testo, tipo

OPZIONI_FASE = ["Baseline (Prima Valutazione)", "Follow-up 3 Mesi", "Follow-up 6 Mesi", "Follow-up 9 Mesi", "Follow-up 12 Mesi"]

# ==============================================================================
# NAVIGAZIONE LATERALE
# ==============================================================================
st.sidebar.title("🩺 Gestione Studio")
modalita = st.sidebar.radio("Seleziona Interfaccia:", ["Screening Completo (Paziente)", "Pannello Analisi e Test (Fisioterapista)"])

# ==============================================================================
# 1. INTERFACCIA PAZIENTE (SCREENING)
# ==============================================================================
if modalita == "Screening Completo (Paziente)":
    st.title("👵 Modulo di Valutazione del Movimento")
    df_paziente = leggi_dati_paziente()
    
    with st.form("form_paziente_totale"):
        st.subheader("📌 Sezione A: Identificazione e Tempistica")
        fase_paziente = st.selectbox("Fase della valutazione:", OPZIONI_FASE)
        col_consenso = st.selectbox("Consenso:", ["Ho letto l'informativa e acconsento liberamente al trattamento dei miei dati personali e sanitari per le finalità riabilitative descritte.", "Non acconsento."])
        col_compilatore = st.selectbox("Chi compila?", ["Paziente stesso", "Familiare", "Caregiver / Assistente"])
        col_ini, col_an, col_sesso = st.columns(3)
        with col_ini: iniziali = st.text_input("Iniziali:", max_chars=3).strip().upper()
        with col_an: anno_nascita = st.number_input("Anno Nascita:", 1920, 2015, 1950)
        with col_sesso: sesso = st.selectbox("Sesso:", ["Uomo", "Donna"])
        situazione_abitativa = st.selectbox("Situazione abitativa:", ["Vive da solo/a in totale autonomia", "Vive con familiari / coniuge", "Vive con un assistente continuo o badante"])
        
        st.subheader("🩺 Sezione B: Quadro Clinico")
        condizioni_mecc = st.multiselect("Condizioni meccaniche:", ["Artrosi Severa", "Osteoporosi", "Protesi d'anca", "Protesi di ginocchio", "Nessuna"])
        condizioni_sist = st.multiselect("Patologie sistemiche:", ["Ipertensione arteriosa (Pressione alta cronica)", "Diabete", "Cardiopatia", "Nessuna"])
        sintomi_red = st.multiselect("Sintomi:", ["Perdita di peso inspiegabile", "Febbre persistente", "Intorpidimento improvviso agli arti", "Nessuno di questi sintomi"])
        dolore_nrs = st.slider("Dolore (0-10):", 0, 10, 5)
        farmaci = st.text_input("Farmaci:")
        specifiche_cliniche = st.text_area("Note specifiche su sintomi, patologie o condizioni meccaniche (opzionale):", placeholder="Inserisci qui eventuali dettagli utili sul quadro clinico...")

        st.subheader("🧠 Sezione C: Vissuto del Movimento")
        v1 = st.slider("1. Nelle ultime 2 settimane...", 1, 10, 5)
        v2 = st.slider("2. Quanto spesso si sente contento/a...", 1, 10, 5)
        v3 = st.slider("3. Sente che alcuni pensieri...", 1, 10, 5)
        v4 = st.slider("4. Sente di avere un carattere...", 1, 10, 5)
        v5 = st.slider("5. Quando si arrabbia...", 1, 10, 5)
        v6 = st.slider("6. Quanto la fa sentire furioso/a...", 1, 10, 5)
        v7 = st.slider("7. Non avrei così tanto dolore...", 1, 10, 5)
        v8 = st.slider("8. Quando sente dolore...", 1, 10, 5)
        v9 = st.slider("9. Quanto crede che l'attività fisica...", 1, 10, 5)
        v10 = st.slider("10. Sente di non poter svolgere...", 1, 10, 5)
        v11 = st.slider("11. Sente che le attività quotidiane...", 1, 10, 5)
        v12 = st.slider("12. Quanto si sente spaventato/a...", 1, 10, 5)
        v13 = st.slider("13. Quando si trova in piedi...", 1, 10, 5)
        v14 = st.slider("14. Quanto si sente sicuro/a...", 1, 10, 5)
        v15 = st.slider("15. Sente che il dolore fisico...", 1, 10, 5)
        v16 = st.slider("16. Sente di riuscire a condurre...", 1, 10, 5)
        v17 = st.slider("17. Pensa che prima di fare progetti...", 1, 10, 5)
        v18 = st.slider("18. Quanto si sente sicuro/a...", 1, 10, 5)

        submit_paziente = st.form_submit_button("Invia Valutazione")
        
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
                st.success(f"Valutazione salvata correttamente per la fase: {fase_paziente}!")
                st.cache_data.clear()
            except Exception as e:
                st.error(f"Errore: {e}")

# ==============================================================================
# 2. PANNELLO FISIOTERAPISTA (DASHBOARD + INSERIMENTO INSIEME)
# ==============================================================================
elif modalita == "Pannello Analisi e Test (Fisioterapista)":
    if not st.session_state.fiso_auth:
        st.title("🔒 Accesso Area Clinica")
        pin = st.text_input("PIN:", type="password")
        if st.button("Accedi"):
            if pin == "1234":
                st.session_state.fiso_auth = True
                st.rerun()
            else:
                st.error("PIN errato.")
        st.stop()

    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Esci dall'Area Clinica"):
        st.session_state.fiso_auth = False
        st.rerun()

    st.title("📊 Hub Clinico: Monitoraggio & Nuovi Test")
    
    df_paziente = leggi_dati_paziente()
    df_valutazioni = leggi_dati_valutazioni()
    
    # Recupero robusto ID Pazienti dalle colonne tramite indice numerico (colonna 3 del foglio Pazienti)
    lista_pazienti = []
    if not df_paziente.empty and len(df_paziente.columns) >= 3:
        lista_pazienti = df_paziente.iloc[:, 2].dropna().unique().tolist()

    if not lista_pazienti:
        st.warning("Nessun paziente registrato nel database.")
    else:
        paziente_selezionato = st.selectbox("🎯 Seleziona il Paziente da analizzare o aggiornare:", lista_pazienti)
        
        # ==========================================
        # PARTE A: VISUALIZZAZIONE GRAFICI STORICI
        # ==========================================
        st.markdown("## 📈 Storico ed Evoluzione Clinica")
        
        # Filtro robusto usando gli indici di posizione delle colonne per evitare KeyError
        storico_paz = df_paziente[df_paziente.iloc[:, 2] == paziente_selezionato].copy() if len(df_paziente.columns) >= 3 else pd.DataFrame()
        storico_val = df_valutazioni[df_valutazioni.iloc[:, 10] == paziente_selezionato].copy() if len(df_valutazioni.columns) >= 11 else pd.DataFrame()
        
        ordine_cronologico = {f: i for i, f in enumerate(OPZIONI_FASE)}
        
        # Ordiniamo i record secondo la sequenza temporale corretta
        if not storico_val.empty and len(storico_val.columns) >= 26:
            storico_val["Ordine"] = storico_val.iloc[:, 25].map(ordine_cronologico)
            storico_val = storico_val.sort_values("Ordine")
            
            # Usiamo la Fase come indice per i grafici
            fasi_presenti = storico_val.iloc[:, 25].tolist()
            storico_val.index = fasi_presenti
            
            # Tab a comparsa per non occupare spazio verticale infinito
            tab_emo, tab_funz, tab_forza = st.tabs(["🩺 Emodinamica", "🏃 Performance & Cammino", "🏋️ Forza Muscolare"])
            
            with tab_emo:
                c1, c2 = st.columns(2)
                with c1:
                    st.write("**Frequenza Cardiaca (bpm)**")
                    campi_fc = [c for c in ["FC a riposo (bpm)", "FC post test (bpm)", "FC_Max_Teorica_Tanaka"] if c in storico_val.columns]
                    if campi_fc: st.line_chart(storico_val[campi_fc])
                with c2:
                    st.write("**Pressione Sistolica (mmHg)**")
                    if "PAS a riposo (mmHg)" in storico_val.columns: st.line_chart(storico_val[["PAS a riposo (mmHg)"]])
                    
            with tab_funz:
                c3, c4 = st.columns(2)
                with c3:
                    st.write("**Tempi di Esecuzione (sec) - *Meno è meglio***")
                    campi_tempo = [c for c in ["Time Up&Go - TUG (sec)", "5xSTS (sec)"] if c in storico_val.columns]
                    if campi_tempo: st.line_chart(storico_val[campi_tempo])
                with c4:
                    st.write("**Punteggi Batteria SPPB (Max 4)**")
                    campi_sppb = [c for c in ["SPPB [Test di Equilibrio Totale]", "SPPB [Velocità del Cammino 4m]", "SPPB [Chair Stand Test]"] if c in storico_val.columns]
                    if campi_sppb: st.bar_chart(storico_val[campi_sppb])
                    
            with tab_forza:
                distretto = st.selectbox("Scegli muscolo:", ["Quadricipite", "Medio Gluteo", "Iliopsoas", "Handgrip"])
                mappa_muscoli = {
                    "Quadricipite": ["Quadricipite DX (Kg)", "Quadricipite SN (Kg)"],
                    "Medio Gluteo": ["Medio Gluteo DX (Kg)", "Medio Gluteo SN (Kg)"],
                    "Iliopsoas": ["Iliopsoas DX (Kg)", "Iliopsoas SN (Kg)"],
                    "Handgrip": ["Handgrip DX (Kg)", "Handgrip SN (Kg)"]
                }
                campi_f = [c for c in mappa_muscoli[distretto] if c in storico_val.columns]
                if len(campi_f) == 2:
                    st.line_chart(storico_val[campi_f])
                    ult_rec = storico_val.iloc[-1]
                    v_dx, v_sn = ult_rec[campi_f[0]], ult_rec[campi_f[1]]
                    if pd.notna(v_dx) and pd.notna(v_sn) and v_dx > 0:
                        st.caption(f"⚖️ Asimmetria ultimo controllo: **{abs(v_dx - v_sn)/max(v_dx, v_sn)*100:.1f}%** (DX: {v_dx}kg | SN: {v_sn}kg)")
        else:
            st.info("ℹ️ Nessun test funzionale precedentemente registrato per questo paziente. Visualizzerai i grafici non appena salverai il primo test.")

        # ==========================================
        # PARTE B: MODULO DI INSERIMENTO NUOVO TEST
        # ==========================================
        st.markdown("---")
        st.markdown("## 📝 Inserisci Nuova Valutazione / Follow-up")
        
        # Calcolo Tanaka automatico
        fc_max_tanaka = None
        if not storico_paz.empty and len(storico_paz.columns) >= 5:
            eta_paziente = int(storico_paz.iloc[0, 4])
            fc_max_tanaka = round(208 - (0.7 * eta_paziente), 1)

        with st.form("form_unificato_fisio"):
            fase_valutazione_fisio = st.selectbox("Seleziona la fase temporale del test attuale:", OPZIONI_FASE)
            
            st.subheader("🩺 Parametri Emodinamici a Riposo")
            if fc_max_tanaka: st.caption(f"💡 Target FC Max Teorica (Tanaka): **{fc_max_tanaka} bpm**")
            col_em1, col_em2, col_em3 = st.columns(3)
            with col_em1: pas = st.number_input("PAS a riposo (mmHg)", min_value=50, max_value=250, value=None, step=1)
            with col_em2: fc_rip = st.number_input("FC a riposo (bpm)", min_value=30, max_value=200, value=None, step=1)
            with col_em3: sat_rip = st.number_input("SatO2 a riposo (%)", min_value=50, max_value=100, value=None, step=1)

            st.subheader("🏃 Test Funzionali")
            col_sf1, col_sf2 = st.columns(2)
            with col_sf1: chair_30s = st.number_input("30-Sec Chair Stand (n°rep)", value=None, step=1)
            with col_sf2: step_30s = st.number_input("30-Sec Step Test (n°rep)", value=None, step=1)
            col_rec1, col_rec2 = st.columns(2)
            with col_rec1: fc_post = st.number_input("FC post test (bpm)", value=None, step=1)
            with col_rec2: tug = st.number_input("TUG (sec)", value=None, format="%.1f")
            sts_5x = st.number_input("5xSTS (sec)", value=None, format="%.1f")

            st.write("**Punteggi parziali SPPB**")
            c_s1, c_s2, c_s3 = st.columns(3)
            with c_s1: sppb_eq = st.number_input("Equilibrio (0-4)", 0, 4, value=None, step=1)
            with c_s2: sppb_cam = st.number_input("Cammino 4m (0-4)", 0, 4, value=None, step=1)
            with c_s3: sppb_chair = st.number_input("Chair Stand (0-4)", 0, 4, value=None, step=1)

            st.subheader("🏋️ Dinamometria (Kg)")
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                quad_dx = st.number_input("Quadricipite DX", value=None, step=0.5)
                gluteo_dx = st.number_input("Gluteo DX", value=None, step=0.5)
                psoas_dx = st.number_input("Iliopsoas DX", value=None, step=0.5)
                hand_dx = st.number_input("Handgrip DX", value=None, step=0.5)
            with col_d2:
                quad_sn = st.number_input("Quadricipite SN", value=None, step=0.5)
                gluteo_sn = st.number_input("Gluteo SN", value=None, step=0.5)
                psoas_sn = st.number_input("Iliopsoas SN", value=None, step=0.5)
                hand_sn = st.number_input("Handgrip SN", value=None, step=0.5)

            submit_fisio = st.form_submit_button("💾 Salva Dati nel Database")

        if submit_fisio:
            riga_valutazione_valori = [
                datetime.now().strftime("%d/%m/%Y %H.%M.%S"), pas, fc_rip, sat_rip, chair_30s, step_30s, fc_post, 100, "", "",
                paziente_selezionato, tug, sts_5x, sppb_eq, sppb_cam, sppb_chair, quad_dx, quad_sn, gluteo_dx, gluteo_sn, psoas_dx, psoas_sn, hand_dx, hand_sn, fc_max_tanaka, fase_valutazione_fisio
            ]
            try:
                nuovo_record_df = pd.DataFrame([riga_valutazione_valori], columns=df_valutazioni.columns)
                conn.update(spreadsheet=URL_FOGLIO, worksheet="Valutazioni_Studio", data=pd.concat([df_valutazioni, nuovo_record_df], ignore_index=True))
                st.success(f"✅ Test per la fase '{fase_valutazione_fisio}' registrato ed inserito nei grafici!")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Errore nel salvataggio: {e}")
