import streamlit as st
import pandas as pd
import json
import plotly.express as px

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
    rischio_caduta = dati_paziente.get('rischio_caduta', 'basso') 
    fragilita = dati_paziente.get('fragilita_percepita', 1) 
    distress = dati_paziente.get('distress_emotivo', 1) 
    esperienza = dati_paziente.get('esperienza_allenamento', 'novizio') 
    
    # INIZIALIZZAZIONE DEL PIANO E REGOLE DI SICUREZZA
    piano_allenamento = {
        "fase_allenamento": "",
        "intensita_forza": "",
        "volume_forza": "",
        "allenamento_potenza_velocita": False,
        "parametri_potenza": {},
        "recupero_tra_sedute": "48-72 ore [cite: 452]",
        "note_sicurezza": [],
        "focus_fisioterapista": []
    }

    # GESTIONE PATOLOGIE (Vincoli medici e biomeccanici)
    if "ipertensione" in patologie or "cardiopatia" in patologie:
        piano_allenamento["note_sicurezza"].append("Assolutamente evitare la manovra di Valsalva per non aumentare la pressione intratoracica e arteriosa[cite: 265].")
        piano_allenamento["note_sicurezza"].append("Mantenere ripetizioni > 8 evitando sforzi massimali a cedimento (1-3 RM).")
    
    if "osteoporosi" in patologie:
        piano_allenamento["note_sicurezza"].append("Includere esercizi multi-articolari per lo stimolo assiale (es. step-up, pressa), evitando flessioni spinali sotto carico[cite: 404].")
    
    if "artrosi" in patologie or "dolore_articolare" in patologie:
        piano_allenamento["note_sicurezza"].append("Selezionare range di movimento (ROM) senza dolore. Evitare la decelerazione improvvisa del carico.")

    # GESTIONE FATICABILITA' E DISTRESS
    if fragilita > 7 or distress > 7:
        piano_allenamento["fase_allenamento"] = "Condizionamento di base / Adattamento Anatomico"
        piano_allenamento["note_sicurezza"].append("Livelli di distress e fragilità elevati: ridurre il volume totale del 20-30% per prevenire l'overreaching non funzionale[cite: 323].")
        esperienza = "novizio"

    # ASSEGNAZIONE PROGRESSIONE DI CARICO [cite: 432]
    if esperienza == "novizio":
        piano_allenamento["intensita_forza"] = "50-70% 1RM stimato (o 10-15 RM)"
        piano_allenamento["volume_forza"] = "1-2 serie per gruppo muscolare, 10-15 ripetizioni"
        piano_allenamento["focus_fisioterapista"].append("Focus su apprendimento motorio, coordinazione e controllo posturale.")
        
    elif esperienza == "intermedio":
        piano_allenamento["intensita_forza"] = "60-80% 1RM stimato (o 8-12 RM)"
        piano_allenamento["volume_forza"] = "2-3 serie per gruppo muscolare, 8-12 ripetizioni"
        piano_allenamento["focus_fisioterapista"].append("Iniziare a implementare il principio del sovraccarico progressivo (aumenti del 5-10%)[cite: 429].")
        
    elif esperienza == "avanzato":
        piano_allenamento["intensita_forza"] = "70-85% 1RM stimato (o 6-10 RM)"
        piano_allenamento["volume_forza"] = "3+ serie per gruppo muscolare, 6-10 ripetizioni"
        piano_allenamento["focus_fisioterapista"].append("Introdurre variazioni di carico ondulate per prevenire la monotonia e l'accommodation.")

    # MODULO PREVENZIONE CADUTE (Sviluppo della Potenza)
    if rischio_caduta in ["medio", "alto"] and fragilita < 8:
        piano_allenamento["allenamento_potenza_velocita"] = True
        piano_allenamento["focus_fisioterapista"].append("Importanza critica della Rate of Force Development (RFD). Richiedere massima intenzione di accelerazione nella fase concentrica[cite: 446].")
        
        piano_allenamento["parametri_potenza"] = {
            "intensita": "30-60% 1RM (carichi leggeri)",
            "volume": "1-3 serie, 3-6 ripetizioni (non arrivare mai a cedimento)",
            "esecuzione": "Fase eccentrica controllata, fase concentrica eseguita alla massima velocità possibile",
            "recupero_tra_serie": "2-3 minuti per rigenerazione ATP-CP"
        }

    # PERIODIZZAZIONE E FEEDBACK SUI TEST
    deficit_forza_lower = test_funzionali.get("deficit_lower_body", False)
    if deficit_forza_lower:
        piano_allenamento["focus_fisioterapista"].append("Priorità all'ipertrofia e forza degli arti inferiori (squat/pressa/step-up). Gli arti inferiori subiscono un declino di massa più rapido rispetto alla parte superiore[cite: 446].")

    return piano_allenamento


# ==========================================
# 2. SEZIONE FISIOTERAPISTA (Integrazione UI Streamlit)
# ==========================================
def sezione_fisioterapista(df_pazienti, df_valutazioni):
    st.header("Sezione Fisioterapista: Analisi e Progressione Clinica")
    
    # Selezione del Paziente tramite ID o Nome
    lista_pazienti = df_pazienti['ID Paziente'].unique()
    paziente_selezionato = st.selectbox("Seleziona ID Paziente", lista_pazienti)
    
    if paziente_selezionato:
        # Estrazione storico per i grafici (sostituzione degli iloc)
        storico_paz = df_pazienti[df_pazienti['ID Paziente'] == paziente_selezionato]
        storico_val = df_valutazioni[df_valutazioni['ID Paziente'] == paziente_selezionato]
        
        st.subheader("Storico Andamento Clinico")
        
        # Creazione di un grafico sicuro basato sui NOMI DELLE COLONNE
        if not storico_paz.empty and "V12_Paura_Cadere" in storico_paz.columns:
            fig = px.line(storico_paz, x="Timestamp", y="V12_Paura_Cadere", markers=True, title="Andamento Paura di Cadere")
            st.plotly_chart(fig, use_container_width=True)
            
        if not storico_val.empty and "30-Second Chair stand test (n°rep)" in storico_val.columns:
            fig2 = px.bar(storico_val, x="Timestamp", y="30-Second Chair stand test (n°rep)", title="Andamento 30s Chair Stand Test")
            st.plotly_chart(fig2, use_container_width=True)

        # ---------------------------------------------------------
        # 3. MAPPATURA DINAMICA DEI DATI PER L'ALGORITMO
        # ---------------------------------------------------------
        if not storico_paz.empty:
            ultimo_record_paz = storico_paz.iloc[-1]
            
            # Mappatura Patologie
            patologie_raw = str(ultimo_record_paz.get("Patologie Sistemiche", "")) + " " + str(ultimo_record_paz.get("Condizioni Meccaniche", ""))
            patologie_raw = patologie_raw.lower()
            patologie_attive = []
            if "ipertensione" in patologie_raw or "pressione alta" in patologie_raw: patologie_attive.append("ipertensione")
            if "cuore" in patologie_raw or "cardiopatia" in patologie_raw: patologie_attive.append("cardiopatia")
            if "osteoporosi" in patologie_raw: patologie_attive.append("osteoporosi")
            if "artrosi" in patologie_raw or "protesi" in patologie_raw: patologie_attive.append("artrosi")

            # Mappatura Fragilità e Distress (Estrazione valori convertiti in numero)
            paura_cadere = pd.to_numeric(ultimo_record_paz.get("V12_Paura_Cadere", 0), errors='coerce')
            instabilita = pd.to_numeric(ultimo_record_paz.get("V13_Instabilita_Gambe", 0), errors='coerce')
            
            paura_danno = pd.to_numeric(ultimo_record_paz.get("V9_Paura_Danno_Esercizio", 0), errors='coerce')
            evitamento = pd.to_numeric(ultimo_record_paz.get("V10_Evitamento_Dolore", 0), errors='coerce')
            dolore_nrs = pd.to_numeric(ultimo_record_paz.get("Dolore NRS", 0), errors='coerce')

            fragilita_max = max(paura_cadere, instabilita)
            distress_max = max(paura_danno, evitamento, dolore_nrs)

            rischio_cad = "basso"
            if fragilita_max >= 7:
                rischio_cad = "alto"
            elif 4 <= fragilita_max < 7:
                rischio_cad = "medio"

            # Creazione dizionario Paziente per Algoritmo
            dati_algoritmo_paz = {
                "patologie": patologie_attive,
                "rischio_caduta": rischio_cad,
                "fragilita_percepita": fragilita_max,
                "distress_emotivo": distress_max,
                "esperienza_allenamento": "novizio" # Impostazione cautelativa di default
            }

            # Mappatura Test Fisioterapista (Se disponibili)
            dati_algoritmo_test = {"deficit_lower_body": False}
            if not storico_val.empty:
                ultimo_test = storico_val.iloc[-1]
                forza_dx = pd.to_numeric(ultimo_test.get("Estensori di Ginocchio (Quadricipite) - DX (Kg)", 0), errors='coerce')
                forza_sn = pd.to_numeric(ultimo_test.get("Estensori di Ginocchio (Quadricipite) - SN (Kg)", 0), errors='coerce')
                
                # Regola: se la forza scende sotto i 10kg o c'è un'asimmetria severa
                if (forza_dx < 10 and forza_sn < 10) or abs(forza_dx - forza_sn) > (max(forza_dx, forza_sn) * 0.20):
                    dati_algoritmo_test["deficit_lower_body"] = True

            # ---------------------------------------------------------
            # 4. ESECUZIONE ALGORITMO E RENDERIZZAZIONE UI
            # ---------------------------------------------------------
            risultato_progressione = genera_progressione_senior(dati_algoritmo_paz, dati_algoritmo_test)

            st.markdown("---")
            st.subheader("⚙️ Programmazione del Carico (Zatsiorsky & NSCA)")
            
            # Renderizzazione visiva dei risultati
            col1, col2 = st.columns(2)
            with col1:
                st.info(f"**Intensità Forza:** {risultato_progressione['intensita_forza']}")
                st.info(f"**Volume Forza:** {risultato_progressione['volume_forza']}")
            with col2:
                st.warning(f"**Fase Allenamento:** {risultato_progressione.get('fase_allenamento', 'Condizionamento Attivo')}")
                st.warning(f"**Recupero Consigliato:** {risultato_progressione['recupero_tra_sedute']}")

            if risultato_progressione["note_sicurezza"]:
                st.error("**⚠️ Note di Sicurezza (Patologie e Distress):**\n" + 
                         "\n".join([f"- {nota}" for nota in risultato_progressione["note_sicurezza"]]))

            if risultato_progressione["focus_fisioterapista"]:
                st.success("**🎯 Focus e Priorità Cliniche:**\n" + 
                           "\n".join([f"- {focus}" for focus in risultato_progressione["focus_fisioterapista"]]))

            if risultato_progressione["allenamento_potenza_velocita"]:
                with st.expander("⚡ Protocollo Prevenzione Cadute (Potenza/RFD)", expanded=True):
                    param_pot = risultato_progressione["parametri_potenza"]
                    st.write(f"- **Intensità:** {param_pot['intensita']}")
                    st.write(f"- **Volume:** {param_pot['volume']}")
                    st.write(f"- **Esecuzione:** {param_pot['esecuzione']}")
                    st.write(f"- **Recupero:** {param_pot['recupero_tra_serie']}")
