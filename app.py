import streamlit as st
import pandas as pd
import math
import re

st.set_page_config(page_title="Diagnostic Moteur", layout="centered")
st.title("🛠️ Diagnostic Fréquentiel de Défauts Moteur")

# --- Fonction utilitaire ---
def presque_egal(a, b, tol=0.05):
    return abs(a - b) / b < tol if b != 0 else False

# --- Lecture et traitement des formules ---
def interpreter_formule(formule):
    f = formule.strip().lower()
    try:
        if "1 à 4" in f and "fr" in f:
            return lambda fr, **kwargs: [fr * i for i in range(1, 5)]
        elif re.search(r"(2[\*⋅x]fr)", f):
            return lambda fr, **kwargs: [2 * fr]
        elif re.search(r"z[\*⋅x]fr", f):
            return lambda fr, Z, **kwargs: [Z * fr]
        elif "fs ± fr" in f or "fe ± fr" in f:
            return lambda fr, fs, **kwargs: [fs + fr, fs - fr]
        elif "z * fr ± fr" in f:
            return lambda fr, Z, **kwargs: [Z * fr + fr, Z * fr - fr]
        elif "0.4 * fr" in f:
            return lambda fr, **kwargs: [0.4 * fr]
        elif "0.42" in f and "fr" in f:
            return lambda fr, **kwargs: [fr * 0.42, fr * 0.48]
        elif "= fr" in f or f.strip() == "fr":
            return lambda fr, **kwargs: [fr]
        elif "2 * fs" in f:
            return lambda fs, **kwargs: [2 * fs]
        elif "50" in f and "1 à 4" in f:
            return lambda **kwargs: [50 * i for i in range(1, 5)]
        elif "fp" in f:
            return lambda fp, **kwargs: [fp]
        else:
            return lambda **kwargs: []
    except Exception:
        return lambda **kwargs: []

# --- Chargement des défauts depuis Excel ---
@st.cache_data
def charger_defauts_depuis_excel(path):
    df = pd.read_excel(path)
    df = df.rename(columns=lambda x: x.strip())
    df = df.dropna(subset=["Anomalie", "Fréquence typique"])
    df = df[["Anomalie", "Fréquence typique", "Direction", "Remarques / Signature fréquentielle (vibratoire et/ou courant)"]]
    df.columns = ["nom", "frequence_typique", "direction", "cause"]

    defauts = []
    for _, row in df.iterrows():
        formule = interpreter_formule(str(row["frequence_typique"]))
        defauts.append({
            "nom": row["nom"],
            "formule": formule,
            "direction": row["direction"],
            "cause": row["cause"]
        })
    return defauts

# --- Charger les défauts ---
defauts = charger_defauts_depuis_excel("pannes_moteurs.xlsx")

# --- Saisie utilisateur ---
with st.form("diagnostic_form"):
    st.subheader("📊 Paramètres moteur (facultatif)")
    fr = st.number_input("Fréquence de rotation (fr)", value=50.0)
    fs = st.number_input("Fréquence d'alimentation (fs)", value=50.0)
    Z = st.number_input("Nombre de dents (Z)", value=30, step=1)
    Nb = st.number_input("Nombre de billes (Nb)", value=8, step=1)
    Db = st.number_input("Diamètre bille (Db, m)", value=0.008)
    Dp = st.number_input("Diamètre primitif (Dp, m)", value=0.04)
    theta_deg = st.number_input("Angle de contact θ (°)", value=15.0)
    theta = math.radians(theta_deg)
    f_critique = st.number_input("Fréquence critique (facultatif)", value=80.0)
    fp = st.number_input("Fréquence de passage courroie (fp)", value=10.0)
    g = st.number_input("Glissement (g)", value=0.02)
    Nr = st.number_input("Nombre de paires de pôles (Nr)", value=2)
    f_aubes = st.number_input("Fréquence de passage des aubes", value=120.0)

    st.subheader("📈 Données de vibration")
    frequences_str = st.text_input("Fréquences mesurées (Hz, séparées par des virgules)", "50,100,80")
    direction = st.selectbox("Direction de la vibration mesurée", ["Axiale", "Radiale", "Axiale et radiale"])

    submitted = st.form_submit_button("Diagnostiquer")

# --- Exécution du diagnostic ---
if submitted:
    try:
        frequences_mesurees = [float(x.strip()) for x in frequences_str.split(",") if x.strip()]
    except ValueError:
        st.error("Veuillez entrer des fréquences valides (ex: 50, 100.5, 80)")
        st.stop()

    caracteristiques = {
        "fr": fr, "fs": fs, "Z": Z, "Nb": Nb, "Db": Db,
        "Dp": Dp, "theta": theta, "f_critique": f_critique,
        "fp": fp, "g": g, "Nr": Nr, "f_aubes": f_aubes
    }

    resultats = []
    for f in frequences_mesurees:
        for d in defauts:
            try:
                f_calc = d["formule"](**caracteristiques)
                if any(presque_egal(f, fc) for fc in f_calc):
                    if direction.lower() in d["direction"].lower() or "et" in d["direction"].lower():
                        resultats.append({
                            "frequence": f,
                            "defaut": d["nom"],
                            "frequences_typiques": f_calc,
                            "cause": d["cause"]
                        })
            except:
                continue

    st.subheader("🔍 Résultats")
    if resultats:
        for r in resultats:
            st.success(f"Défaut détecté : **{r['defaut']}** à **{r['frequence']} Hz**")
            st.markdown(f"- Fréquences typiques : `{r['frequences_typiques']}`")
            st.markdown(f"- Cause probable : {r['cause']}")
    else:
        st.warning("Aucun défaut connu détecté dans les fréquences mesurées.")
