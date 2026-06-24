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
        titolo, testo, tipo = "Alcuni aspetti richiedono attenzione", "Abbiamo notato che talvolta senti un po' di timore nel muoverti liberamente. È normale, ma possiamo lavorarci insieme. Una valutazione completa ci aiuterà a capire come farti sentire più sicuro/a in ogni situazione quotidiana.", "info"
    else:
        titolo, testo, tipo = "Costruiamo insieme la tua sicurezza", "Capiamo che muoversi possa sembrarti faticoso o rischioso in questo momento. Il nostro obiettivo è aiutarti a ritrovare fiducia nelle tue gambe. Ti suggeriamo vivamente un incontro per definire insieme piccoli passi verso una maggiore autonomia.", "warning"
    return titolo, testo, tipo

# ==============================================================================
# NAVIGAZIONE LATERALE
# ==============================================================================
st.sidebar.title("🩺 Gestione Studio")
modalita = st.sidebar.radio("Seleziona Interfaccia:", ["Screening Completo (Paziente)", "Pannello Analisi (Fisioterapista)"])

# ==============================================================================
# 1. INTERFACCIA PAZIENTE (SCREENING)
# ==============================================================================
if modalita == "Screening Completo (Paziente)":
    st.title("👵 Modulo di Valutazione del Movimento")
    
    df_paziente = leggi_dati_paziente()
    
    with st.form("form_paziente_totale"):
        st.subheader("📌 Sezione A: Identificazione")
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

        st.subheader("🧠 Sezione C: Vissuto del Movimento")
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
        v11 = st.slider("11. Sente che le attività quotidiane o la gestione della casa/ lavorative sono ormai troppo pesanti e faticose da gestire?", 1, 10, 5)
        v12 = st.slider("12. Quanto si sente spaventato/a, ansioso/a o insicuro/a all'idea di poter scivolare, inciampare o cadere durante la giornata?", 1, 10, 5)
        v13 = st.slider("13. Quando si trova in piedi (fermo o mentre cammina), quanto avverte una sensazione fisica di instabilità o debolezza nelle gambe?", 1, 10, 5)
        v14 = st.slider("14. Quanto si sente sicuro/a di poter condurre uno stile di vita normale e attivo nonostante il dolore?", 1, 10, 5)
        v15 = st.slider("15. Sente che il dolore fisico non è un problema insormontabile nella sua vita quotidiana?", 1, 10, 5)
        v16 = st.slider("16. Sente di riuscire a condurre una vita piena e soddisfacente anche se convive con un dolore cronico?", 1, 10, 5)
        v17 = st.slider("17. Pensa che prima di fare progetti importanti sia assolutamente necessario avere il totale controllo del proprio dolore?", 1, 10, 5)
        v18 = st.slider("18. Quanto si sente sicuro/a di poter portare a termine la sua terapia ed esercizi indipendentemente da come si sente emotivamente?", 1, 10, 5)

        submit_paziente = st.form_submit_button("Invia Valutazione")
        
        if submit_paziente:
            eta = datetime.now().year - anno_nascita
            id_gen = f"{iniziali}{str(anno_nascita)[-2:]}"
            
            # Mappatura pulita e compatta delle colonne per evitare sdoppiamenti su Google Sheets
            dati_mappati = {
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
                "V18_Aderenza_Terapia": v18
            }
            
            nuova_riga_paziente = pd.DataFrame([dati_mappati])
            
            conn.update(spreadsheet=URL_FOGLIO, worksheet="Dati_Paziente", data=pd.concat([df_paziente, nuova_riga_paziente], ignore_index=True))
            st.success("Valutazione salvata!")
            tit, txt, typ = genera_feedback_empatico((v9+v10)/2, (v12+v13)/2)
            if typ == "success": st.success(f"### {tit}\n{txt}")
            elif typ == "info": st.info(f"### {tit}\n{txt}")
            else: st.warning(f"### {tit}\n{txt}")

# ==============================================================================
# 2. PANNELLO FISIOTERAPISTA (VALUTAZIONE FUNZIONALE)
# ==============================================================================
elif modalita == "Pannello Analisi (Fisioterapista)":
    
    if not st.session_state.fiso_auth:
        st.title("🔒 Accesso Area Clinica")
        st.write("Inserisci il PIN per accedere al modulo delle valutazioni funzionali.")
        pin = st.text_input("PIN:", type="password")
        if st.button("Accedi"):
            if pin == "1234":
                st.session_state.fiso_auth = True
                st.rerun()
            else:
                st.error("PIN errato. Riprova.")
    
    else:
        st.sidebar.markdown("---")
        if st.sidebar.button("🚪 Esci dall'Area Clinica"):
            st.session_state.fiso_auth = False
            st.rerun()

        st.title("📊 Hub Valutazione Funzionale")
        st.info("Compila solo i test che hai eseguito. I campi lasciati vuoti rimarranno tali nel database.")

        df_paziente = leggi_dati_paziente()
        lista_pazienti = []
        if "ID paziente" in df_paziente.columns:
            lista_pazienti = df_paziente["ID paziente"].dropna().unique().tolist()
            lista_pazienti = [p for p in lista_pazienti if str(p).strip() != ""] 

        if not lista_pazienti:
            st.warning("Nessun paziente trovato. Fai compilare prima il modulo paziente.")
        else:
            df_valutazioni = leggi_dati_valutazioni()

            with st.form("form_valutazione_funzionale"):
                st.subheader("Associazione Paziente")
                paziente_selezionato = st.selectbox("Seleziona ID Paziente:", lista_pazienti)
                
                st.markdown("---")
                st.subheader("🩺 Parametri Emodinamici a Riposo")
                col_em1, col_em2, col_em3 = st.columns(3)
                with col_em1: pas = st.number_input("PAS a riposo (mmHg)", min_value=50, max_value=250, value=None, step=1)
                with col_em2: fc_rip = st.number_input("FC a riposo (bpm)", min_value=30, max_value=200, value=None, step=1)
                with col_em3: sat_rip = st.number_input("SatO2 a riposo (%)", min_value=50, max_value=100, value=None, step=1)

                st.markdown("---")
                st.subheader("🏃 Test di Tolleranza allo Sforzo")
                col_sf1, col_sf2 = st.columns(2)
                with col_sf1: chair_30s = st.number_input("30-Sec Chair Stand (n°rep)", min_value=0, value=None, step=1)
                with col_sf2: step_30s = st.number_input("30-Sec Step Test (n°rep)", min_value=0, value=None, step=1)
                
                col_rec1, col_rec2, col_rec3 = st.columns(3)
                with col_rec1: fc_post = st.number_input("FC post test (bpm)", min_value=30, max_value=250, value=None, step=1)
                with col_rec2: sat_post = st.number_input("SatO2 post test (%)", min_value=50, max_value=100, value=None, step=1)
                with col_rec3: t_recupero = st.text_input("Tempo di recupero (es. '2 min')")

                st.markdown("---")
                st.subheader("⚖️ Test Funzionali e Mobilità")
                col_fm1, col_fm2 = st.columns(2)
                with col_fm1: tug = st.number_input("Time Up&Go - TUG (sec)", min_value=0.0, value=None, step=0.1, format="%.1f")
                with col_fm2: sts_5x = st.number_input("5xSTS (sec)", min_value=0.0, value=None, step=0.1, format="%.1f")
                
                st.write("**SPPB (Short Physical Performance Battery)**")
                col_sp1, col_sp2, col_sp3 = st.columns(3)
                with col_sp1: sppb_eq = st.number_input("SPPB [Test di Equilibrio Totale]", min_value=0, max_value=4, value=None, step=1)
                with col_sp2: sppb_cam = st.number_input("SPPB [Velocità del Cammino 4m]", min_value=0, max_value=4, value=None, step=1)
                with col_sp3: sppb_chair = st.number_input("SPPB [Chair Stand Test]", min_value=0, max_value=4, value=None, step=1)

                st.markdown("---")
                st.subheader("🏋️ Forza Muscolare - Dinamometria (Kg)")
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    quad_dx = st.number_input("Quadricipite DX (Kg)", min_value=0.0, value=None, step=0.5)
                    gluteo_dx = st.number_input("Medio Gluteo DX (Kg)", min_value=0.0, value=None, step=0.5)
                    psoas_dx = st.number_input("Iliopsoas DX (Kg)", min_value=0.0, value=None, step=0.5)
                    hand_dx = st.number_input("Handgrip DX (Kg)", min_value=0.0, value=None, step=0.5)
                with col_d2:
                    quad_sn = st.number_input("Quadricipite SN (Kg)", min_value=0.0, value=None, step=0.5)
                    gluteo_sn = st.number_input("Medio Gluteo SN (Kg)", min_value=0.0, value=None, step=0.5)
                    psoas_sn = st.number_input("Iliopsoas SN (Kg)", min_value=0.0, value=None, step=0.5)
                    hand_sn = st.number_input("Handgrip SN (Kg)", min_value=0.0, value=None, step=0.5)

                submit_fisio = st.form_submit_button("Salva Valutazione Funzionale")

                if submit_fisio:
                    nuova_riga_valutazione = pd.DataFrame([{
                        "Informazioni cronologiche": datetime.now().strftime("%d/%m/%Y %H.%M.%S"),
                        "Pressione Arteriosa Sistolica a riposo (mmHg)": pas,
                        "Frequenza Cardiaca a Riposo": fc_rip,
                        "Saturazione O2 a riposo": sat_rip,
                        "30-Second Chair stand test (n°rep)": chair_30s,
                        "30-Second Step test (n°rep)": step_30s,
                        "Frequenza cardiaca post test": fc_post,
                        "Saturazione O2 post test (%)": sat_post,
                        "Tempo di recupero": t_recupero,
                        "Colonna 9": "",
                        "ID Paziente": paciente_selezionato,
                        "Tempo di esecuzione del Time Up&Go (TUG)": tug,
                        "Tempo di esecuzione del 5xSTS (in secondi)": sts_5x,
                        "SPPB [Test di Equilibrio Totale]": sppb_eq,
                        "SPPB [Velocità del Cammino su 4 metri]": sppb_cam,
                        "SPPB [Chair Stand Test]": sppb_chair,
                        "Estensori di Ginocchio (Quadricipite) - DX (Kg)": quad_dx,
                        "Estensori di Ginocchio (Quadricipite) - SN (Kg)": quad_sn,
                        "Abduttori d'Anca (Medio Gluteo) - DX (Kg)": gluteo_dx,
                        "Abduttori d'Anca (Medio Gluteo) - SN (Kg)": gluteo_sn,
                        "Flessori d'Anca (Iliopsoas) - DX (Kg)": psoas_dx,
                        "Flessori d'Anca (Iliopsoas) - SN (Kg)": psoas_sn,
                        "Handgrip mano destra": hand_dx,
                        "Handgrip mano sinistra": hand_sn
                    }])

                    conn.update(spreadsheet=URL_FOGLIO, worksheet="Valutazioni_Studio", data=pd.concat([df_valutazioni, nuova_riga_valutazione], ignore_index=True))
                    st.success(f"Valutazione funzionale per il paziente {paziente_selezionato} salvata con successo!")
