import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Hub Clinico - Valutazione Anziani", layout="centered")

# ==============================================================================
# CONNESSIONE E FUNZIONE FEEDBACK
# ==============================================================================
conn = st.connection("gsheets", type=GSheetsConnection)
URL_FOGLIO = "https://docs.google.com/spreadsheets/d/1qbCAMeOUKI23gq3p8g95JSwESI6-tF7mvUp8Mg0Z4Jk/edit"

@st.cache_data(ttl=10)
def leggi_dati():
    return conn.read(spreadsheet=URL_FOGLIO, worksheet="Dati_Paziente")

def genera_feedback_empatico(kinesiofobia, paura_cadute):
    indice_prudenza = (kinesiofobia + paura_cadute) / 2
    if indice_prudenza < 4:
        titolo, testo, tipo = "Hai una buona consapevolezza del tuo corpo!", "Continua a mantenerti attivo/a come stai facendo. La tua sicurezza nei movimenti è un ottimo punto di partenza per conservare l'autonomia.", "success"
    elif 4 <= indice_prudenza < 7:
        titolo, testo, tipo = "Alcuni aspetti richiedono attenzione", "Abbiamo notato che talvolta senti un po' di timore nel muoverti liberamente. È normale, ma possiamo lavorarci insieme. Una valutazione completa ci aiuterà a capire come farti sentire più sicuro/a in ogni situazione quotidiana.", "info"
    else:
        titolo, testo, tipo = "Costruiamo insieme la tua sicurezza", "Capiamo che muoversi possa sembrarti faticoso o rischioso in questo momento. Il nostro obiettivo è aiutarti a ritrovare fiducia nelle tue gambe. Ti suggeriamo vivamente un incontro per definire insieme piccoli passi verso una maggiore autonomia.", "warning"
    return titolo, testo, tipo

df_paziente = leggi_dati()

# ==============================================================================
# INTERFACCIA PAZIENTE
# ==============================================================================
st.sidebar.title("🩺 Gestione Studio")
modalita = st.sidebar.radio("Seleziona Interfaccia:", ["Screening Completo (Paziente)", "Pannello Analisi (Fisioterapista)"])

if modalita == "Screening Completo (Paziente)":
    st.title("👵 Modulo di Valutazione del Movimento")
    
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
        # Slider con testi armonizzati
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

        submit = st.form_submit_button("Invia Valutazione")
        
        if submit:
            eta = datetime.now().year - anno_nascita
            id_gen = f"{iniziali}{str(anno_nascita)[-2:]}"
            nuova_riga = pd.DataFrame([{
                "Informazioni cronologiche": datetime.now().strftime("%d/%m/%Y %H.%M.%S"),
                "Consenso al trattamento dei dati sanitari:": col_consenso,
                "ID paziente": id_gen,
                "Chi sta compilando questo modulo?": col_compilatore,
                "Età del paziente": eta,
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
                "   Vissuto del movimento, umore e stabilità   [Pensa che prima di fare progetti importanti sia assolutamente necessario avere il totale controllo del proprio dolore?]": v17,
                "   Vissuto del movimento, umore e stabilità   [Quanto si sente sicuro/a di poter portare a termine la sua terapia ed esercizi indipendentemente da come si sente emotivamente?]": v18
            }])
            
            conn.update(spreadsheet=URL_FOGLIO, worksheet="Dati_Paziente", data=pd.concat([df_paziente, nuova_riga], ignore_index=True))
            st.success("Valutazione salvata!")
            tit, txt, typ = genera_feedback_empatico((v9+v10)/2, (v12+v13)/2)
            if typ == "success": st.success(f"### {tit}\n{txt}")
            elif typ == "info": st.info(f"### {tit}\n{txt}")
            else: st.warning(f"### {tit}\n{txt}")

elif modalita == "Pannello Analisi (Fisioterapista)":
    if st.text_input("PIN:", type="password") == "1234":
        st.write("Accesso consentito.")
