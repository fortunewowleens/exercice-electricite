from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

DOSSIER = Path(__file__).parent / "donnees"

st.set_page_config(
    page_title="L'électricité dans 12 quartiers",
    page_icon="⚡",
    layout="wide",
)


@st.cache_data
def charger_donnees():
    return pd.read_csv(DOSSIER / "consommation_propre.csv")


donnees = charger_donnees()

st.title("L'électricité dans 12 quartiers")
st.caption("Relevés mensuels de janvier 2024 à décembre 2025. Données fictives.")
st.markdown(
    "Deux ans de relevés pour 12 quartiers de Port-au-Prince, Delmas, "
    "Pétion-Ville et Cap-Haïtien. La question du directeur : **la consommation "
    "suit-elle la chaleur, ou les heures de courant ?**"
)

communes = sorted(donnees["commune"].unique())
communes_choisies = st.sidebar.multiselect("Communes", communes, default=communes)
annees = sorted(donnees["annee"].unique(), reverse=True)
annee = st.sidebar.selectbox("Année", annees, index=0)
st.sidebar.caption(
    "L'année s'applique aux indicateurs et au tableau de données ; "
    "les onglets utilisent les deux années."
)

if not communes_choisies:
    st.warning("Choisissez au moins une commune dans la barre latérale.")
    st.stop()

donnees_communes = donnees[donnees["commune"].isin(communes_choisies)]
filtrees = donnees_communes[donnees_communes["annee"] == annee]

colonne_1, colonne_2, colonne_3 = st.columns(3)
colonne_1.metric(
    "Consommation totale",
    f"{filtrees['kwh'].sum() / 1_000_000:.2f} millions de kWh",
)
colonne_2.metric(
    "Consommation par abonné",
    f"{filtrees['kwh_par_abonne'].mean():.1f} kWh",
)
colonne_3.metric(
    "Heures de courant",
    f"{filtrees['heures_courant'].mean():.1f} h/jour",
)

onglet_quartiers, onglet_evolution, onglet_chaleur, onglet_coupures, onglet_hors_norme = (
    st.tabs(
        [
            "Quartiers",
            "Évolution",
            "Chaleur ou courant ?",
            "Coupures",
            "Relevés hors norme",
        ]
    )
)

with onglet_quartiers:
    classement = (
        donnees_communes.groupby("quartier")["kwh_par_abonne"]
        .mean()
        .sort_values(ascending=False)
        .round(1)
    )
    moyennes_type = (
        donnees_communes.groupby("type")["kwh_par_abonne"].mean().round(1)
    )

    figure, axe = plt.subplots(figsize=(8, 4))
    classement.sort_values().plot.barh(ax=axe, color="#4C72B0")
    axe.set_xlabel("kWh par abonné (moyenne 2024-2025)")
    axe.set_ylabel("")
    axe.set_title("Consommation moyenne par abonné, par quartier")
    plt.tight_layout()
    st.pyplot(figure)
    plt.close(figure)

    tete = ", ".join(
        f"{quartier} ({valeur:.1f})" for quartier, valeur in classement.head(3).items()
    )
    commercial = moyennes_type.get("Commercial", float("nan"))
    residentiel = moyennes_type.get("Résidentiel", float("nan"))
    if pd.isna(commercial) or pd.isna(residentiel):
        phrase_types = "La sélection ne contient pas les deux types de quartiers."
    else:
        phrase_types = (
            f"Les quartiers commerciaux consomment en moyenne "
            f"**{commercial:.1f} kWh** par abonné, contre "
            f"**{residentiel:.1f} kWh** pour les résidentiels."
        )
    st.markdown(f"{phrase_types} En tête : {tete}.")

with onglet_evolution:
    tableau = donnees_communes.pivot_table(
        index="commune", columns="annee", values="kwh", aggfunc="sum"
    )
    totaux_millions = (tableau / 1_000_000).round(2)
    courbes = (
        donnees_communes.groupby(["commune", "mois"])["kwh_par_abonne"]
        .mean()
        .unstack("commune")
    )

    figure, axe = plt.subplots(figsize=(10, 4))
    courbes.plot(ax=axe, marker="o", markersize=3)
    axe.set_xlabel("Mois")
    axe.set_ylabel("kWh par abonné")
    axe.set_title("Consommation moyenne par abonné, mois par mois")
    axe.tick_params(axis="x", rotation=90)
    axe.legend(title="Commune")
    plt.tight_layout()
    st.pyplot(figure)
    plt.close(figure)

    if {2024, 2025}.issubset(totaux_millions.columns):
        hausse = ((totaux_millions[2025] / totaux_millions[2024]) - 1) * 100
        premiere = hausse.idxmax()
        derniere = hausse.idxmin()
        st.markdown(
            f"De 2024 à 2025, **{premiere}** progresse le plus "
            f"(**{hausse[premiere]:.1f} %**, de "
            f"{totaux_millions.loc[premiere, 2024]:.2f} à "
            f"{totaux_millions.loc[premiere, 2025]:.2f} millions de kWh), "
            f"tandis que **{derniere}** ferme la marche "
            f"(**{hausse[derniere]:.1f} %**)."
        )

with onglet_chaleur:
    residentiel = donnees_communes[
        donnees_communes["type"] == "Résidentiel"
    ]
    if residentiel.empty:
        st.info("Aucun quartier résidentiel dans la sélection.")
    else:
        figure, axes = plt.subplots(1, 2, figsize=(11, 4))
        axes[0].scatter(
            residentiel["heures_courant"],
            residentiel["kwh_par_abonne"],
            alpha=0.6,
            color="#DD8452",
        )
        axes[0].set_xlabel("Heures de courant par jour")
        axes[0].set_ylabel("kWh par abonné")
        axes[0].set_title("Heures de courant")
        axes[1].scatter(
            residentiel["temperature_c"],
            residentiel["kwh_par_abonne"],
            alpha=0.6,
            color="#4C72B0",
        )
        axes[1].set_xlabel("Température (°C)")
        axes[1].set_ylabel("kWh par abonné")
        axes[1].set_title("Température")
        plt.tight_layout()
        st.pyplot(figure)
        plt.close(figure)

        correlation_heures = residentiel["kwh_par_abonne"].corr(
            residentiel["heures_courant"]
        )
        correlation_temperature = residentiel["kwh_par_abonne"].corr(
            residentiel["temperature_c"]
        )
        st.markdown(
            f"Dans les quartiers résidentiels, la consommation par abonné est "
            f"corrélée à **{correlation_heures:.2f}** avec les heures de courant, "
            f"mais seulement à **{correlation_temperature:.2f}** avec la "
            f"température. C'est donc la disponibilité du courant, bien plus que "
            f"la chaleur, qui accompagne la consommation."
        )

with onglet_coupures:
    statistiques = (
        donnees_communes.groupby("commune")["heures_courant"]
        .agg(
            mediane="median",
            q1=lambda serie: serie.quantile(0.25),
            q3=lambda serie: serie.quantile(0.75),
        )
        .round(1)
    )

    cap_haitien = donnees_communes[
        donnees_communes["commune"] == "Cap-Haïtien"
    ]
    if cap_haitien.empty:
        cap_haitien = donnees_communes
        titre = "Heures de courant dans les communes choisies"
    else:
        titre = "Cap-Haïtien : distribution des heures de courant"

    figure, axe = plt.subplots(figsize=(7, 4))
    axe.hist(cap_haitien["heures_courant"], bins=12, color="#55A868", edgecolor="white")
    axe.set_xlabel("Heures de courant par jour")
    axe.set_ylabel("Nombre de relevés")
    axe.set_title(titre)
    plt.tight_layout()
    st.pyplot(figure)
    plt.close(figure)

    st.dataframe(statistiques, width="stretch")

    faibles = donnees_communes[
        (donnees_communes["annee"] == 2025)
        & (donnees_communes["heures_courant"] < 8)
    ]
    details = ", ".join(
        f"{ligne.quartier} en {ligne.mois} ({ligne.heures_courant:.1f} h)"
        for ligne in faibles.itertuples()
    )
    commune_min = statistiques["mediane"].idxmin()
    mediane_min = statistiques.loc[commune_min, "mediane"]
    autres = statistiques.drop(index=commune_min)["mediane"]
    if autres.empty:
        comparaison = ""
    else:
        comparaison = (
            f", contre {autres.min():.1f} à {autres.max():.1f} heures ailleurs"
        )
    complement = f" : {details}." if details else "."
    st.markdown(
        f"**{commune_min}** est la commune la plus mal servie "
        f"(médiane **{mediane_min:.1f} h/jour**{comparaison}). "
        f"En 2025, **{len(faibles)} relevé(s)** passent sous 8 heures"
        f"{complement}"
    )

with onglet_hors_norme:
    plus_gros = donnees_communes.nlargest(3, "kwh")[
        ["mois", "quartier", "type", "kwh"]
    ]

    figure, axe = plt.subplots(figsize=(8, 3))
    etiquettes = plus_gros["quartier"] + " (" + plus_gros["mois"] + ")"
    axe.barh(etiquettes, plus_gros["kwh"], color="#C44E52")
    axe.set_xlabel("kWh")
    axe.invert_yaxis()
    plt.tight_layout()
    st.pyplot(figure)
    plt.close(figure)

    st.dataframe(plus_gros, hide_index=True, width="stretch")
    premier = plus_gros.iloc[0]
    st.markdown(
        f"Le plus gros relevé est **{premier['quartier']} en {premier['mois']}** "
        f"avec **{premier['kwh']:,.0f} kWh** (type {premier['type']})."
    )

st.markdown(
    """
## Conclusion

La consommation suit davantage les heures de courant que la chaleur : dans les
quartiers résidentiels, la corrélation entre les kWh par abonné et les heures de
courant atteint **0,76**, contre **-0,15** avec la température. Autrement dit, ce
n'est pas la chaleur qui tire la demande, mais la disponibilité du réseau ;
Cap-Haïtien, mal servi, progresse pourtant le plus. Une corrélation n'établit pas
une causalité : elle ne dit pas si c'est le courant qui fait consommer ou
l'inverse, et d'autres facteurs peuvent jouer.
"""
)

with st.expander("Voir les données filtrées"):
    st.write(
        f"{len(filtrees)} lignes pour {annee} et "
        f"{len(communes_choisies)} commune(s)."
    )
    st.dataframe(filtrees, hide_index=True, width="stretch")
