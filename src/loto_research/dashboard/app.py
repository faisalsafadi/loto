"""Tableau de bord (M5 + pages Tirages et Prédictions). Lancer : python -m loto_research.dashboard [--writable]
Par défaut : lecture seule (la base est ouverte sans droit d'écriture). Les écritures n'existent qu'avec --writable,
dans le module entry, avec les mêmes garde-fous que la ligne de commande."""
import os
import subprocess
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from loto_research.dashboard import data as D
from loto_research.dashboard import views as V
from loto_research.db.core import ValidationError
from loto_research.db.loader import load_draws_dataframe
from loto_research.prediction import store as PS

DB = os.environ.get("LOTO_DB", "data/loto.sqlite")
GAME = os.environ.get("LOTO_GAME", "Loto Maroc 6/49")
WRITABLE = os.environ.get("LOTO_WRITABLE") == "1"
if WRITABLE:
    from loto_research.dashboard import entry as E

PAGES = ["Données", "Fréquences", "Tirages", "Prédictions", "Tests", "Journal", "Simulateur et banc d'essai",
         "À propos"]
SCENARIOS = {
    "number": "Un numéro biaisé (hausse relative de sa fréquence)",
    "pair": "Une paire biaisée (multiplicateur de sa fréquence conjointe)",
    "dependence": "Dépendance entre tirages (probabilité de reprise ρ)",
    "rupture": "Rupture à mi-série (hausse relative sur la seconde moitié)",
}
TESTS = {
    "uniformity_global": "Uniformité globale",
    "per_number_holm": "Numéro par numéro (Holm)",
    "consecutive_overlap": "Recouvrement consécutif",
    "half_homogeneity": "Homogénéité entre moitiés",
}

st.set_page_config(page_title="Audit statistique du Loto", layout="wide")

if not Path(DB).exists():
    st.error(f"Base introuvable : {DB}. Lance le tableau de bord depuis la racine du dépôt "
             f"(python -m loto_research.dashboard --db CHEMIN).")
    st.stop()
MTIME = os.path.getmtime(DB)
PRED_DIR = str(Path(DB).resolve().parent / "predictions")


@st.cache_data(show_spinner=False)
def load_context(db, mtime, game_name):
    conn = D.open_readonly(db)
    try:
        game = D.get_game(conn, game_name)
        if game is None:
            return None
        df = load_draws_dataframe(conn, game["id"])
        return game, df, D.dataset_state(conn, game["id"])
    finally:
        conn.close()


def with_conn(fn, *args, **kwargs):
    conn = D.open_readonly(DB)
    try:
        return fn(conn, *args, **kwargs)
    finally:
        conn.close()


def git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True,
                                       cwd=Path(DB).resolve().parent.parent).strip()
    except Exception:
        return None


def show_table(df):
    """Tableau STATIQUE (non triable) : aucun classement des numéros n'est possible en un clic."""
    st.table(df.astype(object).where(df.notna(), "—").astype(str))


def freq_figure(tab, title):
    colors = ["#D1495B" if b else "#F2A65A" if a else "#8FA3B8" for a, b in zip(tab["outside95"], tab["outsideB"])]
    lo = min(tab["count"].min(), tab["loB"].iloc[0])
    hi = max(tab["count"].max(), tab["hiB"].iloc[0])
    pad = 0.08 * (hi - lo)
    fig = go.Figure()
    fig.add_hrect(y0=tab["lo95"].iloc[0], y1=tab["hi95"].iloc[0], fillcolor="#4CAF50", opacity=0.12, line_width=0)
    for y in (tab["loB"].iloc[0], tab["hiB"].iloc[0]):
        fig.add_hline(y=y, line_dash="dot", line_color="#D1495B")
    fig.add_hline(y=tab["expected"].iloc[0], line_color="black")
    fig.add_trace(go.Scatter(x=tab["numero"], y=tab["count"], mode="markers",
                             marker=dict(size=9, color=colors),
                             hovertemplate="n° %{x}<br>%{y} apparitions<extra></extra>"))
    fig.update_layout(title=title, showlegend=False, height=420, margin=dict(l=10, r=10, t=50, b=10),
                      xaxis=dict(title="Numéro (toujours dans l'ordre, jamais trié)", dtick=1),
                      yaxis=dict(title="Nombre d'apparitions", range=[lo - pad, hi + pad]))
    return fig


def freq_table_view(tab):
    v = tab[["numero", "count", "freq_pct", "exp_pct", "lo95_pct", "hi95_pct", "z"]].copy()
    v.columns = ["Numéro", "Apparitions", "Fréquence %", "Attendue %", "Bas 95 %", "Haut 95 %",
                 "Écart (en écarts-types)"]
    return v.round(2).set_index("Numéro")


def band_summary(tab, n_max):
    out95, outb = D.outside_counts(tab)
    exp95, expb = D.expected_outside(n_max)
    c1, c2, c3 = st.columns(3)
    c1.metric("Tirages analysés", f"{int(tab['count'].sum() / K)}")
    c2.metric("Numéros hors de la bande à 95 %", out95, help=f"Attendu par pur hasard : environ {exp95:.1f}")
    c3.metric("Numéros hors de la bande corrigée", outb, help=f"Attendu par pur hasard : environ {expb:.2f}")


def prob_figure(models):
    fig = go.Figure()
    fig.add_hline(y=K / N_MAX, line_color="black", annotation_text="hasard : 6/49")
    for name, color in (("frequency", "#4C78A8"), ("logistic", "#F58518")):
        fig.add_trace(go.Scatter(x=list(range(1, N_MAX + 1)), y=models[name]["probabilities"], mode="markers",
                                 name=V.MODEL_LABELS[name], marker=dict(size=8, color=color)))
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=30, b=10),
                      xaxis=dict(title="Numéro (toujours dans l'ordre)", dtick=1),
                      yaxis=dict(title="Probabilité estimée d'apparition"))
    return fig


ctx = load_context(DB, MTIME, GAME)
if ctx is None:
    st.error(f"Jeu introuvable : {GAME!r}.")
    st.stop()
game, df, state = ctx
K, N_MAX = game["k"], game["n_max"]

st.warning(D.banner_text(N_MAX, K))
missing = V.missing_expected_draws(df)
if missing:
    st.info(f"Il manque probablement {len(missing)} tirage(s) dans la base : "
            f"{', '.join(f'{V.weekday_fr(m)} {m}' for m in missing)} (rythme lundi, mercredi, samedi, à vérifier). "
            f"Ajoute-les dans la page Tirages : les prédictions et les tests ne comptent que les tirages saisis.")
st.sidebar.title("Audit statistique du Loto")
page = st.sidebar.radio("Page", PAGES)
if WRITABLE:
    st.sidebar.error("Mode écriture activé : ajout de tirages, corrections et gel de prédictions.")
else:
    st.sidebar.caption("Lecture seule : cet outil ne modifie jamais la base.")

if page == "Données":
    st.header("Données")
    c1, c2, c3 = st.columns(3)
    c1.metric("Tirages", f"{len(df)}")
    c2.metric("Premier tirage", df["date"].min().strftime("%Y-%m-%d"))
    c3.metric("Dernier tirage", df["date"].max().strftime("%Y-%m-%d"))
    st.caption(f"Empreinte des données (SHA256, début) : {state['hash'][:16]}. Elle change dès qu'un tirage ou une "
               f"correction est ajouté(e).")
    st.subheader("Tirages par année")
    st.bar_chart(D.draws_per_year(df).set_index("year"))
    st.subheader("Derniers tirages (ordre chronologique inverse)")
    show_table(D.last_draws(df, 10, K))
    st.subheader("Qualité des données")
    st.markdown(
        "- **Source déclarée :** le site officiel de la loterie (eloterie.ma, page des résultats), dont les tirages "
        "ont été récupérés puis rassemblés dans un fichier tableur.\n"
        "- Ce fichier a été **réparé à la main avant l'import, sans journal des modifications**.\n"
        "- 3 155 tirages ont été retenus au lieu des 3 159 annoncés (écart accepté).\n"
        "- Un recoupement systématique avec le site n'est **pas documenté** : la provenance est connue, "
        "l'exactitude de chaque numéro n'est pas démontrée.\n"
        "- Chaque tirage ajouté depuis porte sa source (voir la page Journal).")

elif page == "Fréquences":
    st.header("Fréquences des numéros")
    label = st.selectbox("Période", list(D.PERIODS), help="Seules les périodes pré-enregistrées sont proposées : "
                         "choisir une fenêtre après coup fausserait la lecture.")
    sub = D.filter_period(df, label)
    tab = D.frequency_table(sub, K, N_MAX)
    band_summary(tab, N_MAX)
    st.plotly_chart(freq_figure(tab, f"Apparitions de chaque numéro — {label}"))
    st.markdown(
        "**Comment lire ce graphique.** La ligne noire est le nombre d'apparitions attendu pour un numéro. "
        "La zone verte est l'écart normal à 95 % : avec 49 numéros, **environ 2 numéros sortent de cette zone par "
        "pur hasard**. Les pointillés rouges sont la bande corrigée pour les 49 comparaisons : par hasard, un numéro "
        "en sort rarement (environ 1 fois sur 20 pour l'ensemble). Orange : hors de la zone à 95 %. Rouge : hors de "
        "la bande corrigée. Une fréquence passée ne dit rien sur le tirage suivant.")
    with st.expander("Voir le tableau (ordre des numéros, non triable)"):
        st.table(freq_table_view(tab))

elif page == "Tirages":
    st.header("Tirages")
    years = ["Toutes"] + [int(y) for y in sorted(df["year"].unique(), reverse=True)]
    choice = st.selectbox("Année", years)
    st.dataframe(V.draws_listing(df, None if choice == "Toutes" else choice, K), hide_index=True, height=380)
    st.caption("Liste des tirages, corrections appliquées. Les tirages d'origine ne sont jamais modifiés.")
    if not WRITABLE:
        st.info("Lecture seule. Pour ajouter ou corriger des tirages depuis cette page, relance : "
                "python -m loto_research.dashboard --writable")
    else:
        st.subheader("Ajouter des tirages")
        text = st.text_area("Colle ici les lignes copiées du site (N, 6 numéros, complémentaire, date)", height=180,
                            placeholder="130  42  3  28  12  31  17  15  2026-10-31")
        c1, c2 = st.columns(2)
        source = c1.text_input("Source (obligatoire)", value="site officiel (eloterie.ma/resultats)")
        source_ref = c2.text_input("Référence", value="https://www.eloterie.ma/resultats")
        if st.button("Vérifier les lignes collées"):
            st.session_state["paste"] = {"text": text, "source": source, "ref": source_ref,
                                         "result": E.preview_pasted(DB, GAME, text, source)}
        paste = st.session_state.get("paste")
        if paste:
            res = paste["result"]
            if res["errors"]:
                st.error("Rien ne peut être enregistré :\n\n" + "\n".join(f"- {e}" for e in res["errors"]))
            elif not res["new"]:
                st.info("Tous ces tirages sont déjà dans la base : rien à ajouter.")
            else:
                st.success(f"{len(res['new'])} nouveau(x) tirage(s) valide(s), "
                           f"{len(res['skipped'])} déjà présent(s) et ignoré(s).")
                show_table(pd.DataFrame(
                    [{"Date": r["date"], "Numéros": " · ".join(map(str, r["nums"])), "Compl.": r["bonus"],
                      "N° officiel": r["no"]} for r in res["new"]]))
                for note in res["notes"]:
                    st.info(note)
                ok = st.checkbox("Je confirme l'ajout de ces tirages (définitif : une erreur se corrige, "
                                 "elle ne s'efface pas).")
                if st.button("Enregistrer ces tirages", disabled=not ok):
                    try:
                        n_added = E.commit_pasted(DB, GAME, paste["text"], paste["source"], paste["ref"])
                        st.session_state.pop("paste", None)
                        st.cache_data.clear()
                        st.success(f"{n_added} tirage(s) ajouté(s). Recharge la page pour voir la liste à jour.")
                    except ValidationError as e:
                        st.error(str(e))
        st.subheader("Corriger un tirage")
        cdate = st.text_input("Date du tirage (AAAA-MM-JJ)")
        cchanges = st.text_input("Changements (ex. n3=17  ou  n3=17, n5=22  ou  bonus=9)")
        creason = st.text_input("Raison de la correction (obligatoire)")
        cauthor = st.text_input("Auteur (obligatoire)")
        if st.button("Vérifier la correction"):
            try:
                st.session_state["corr"] = {"date": cdate, "changes": cchanges, "reason": creason,
                                            "author": cauthor,
                                            "plan": E.preview_correction(DB, GAME, cdate, cchanges)}
            except ValidationError as e:
                st.session_state.pop("corr", None)
                st.error(str(e))
        corr = st.session_state.get("corr")
        if corr:
            plan = corr["plan"]
            st.write(f"Tirage du {plan['draw_date']} :")
            st.write(f"- avant : {plan['before'][0]}  + complémentaire {plan['before'][1]}")
            st.write(f"- après : {plan['after'][0]}  + complémentaire {plan['after'][1]}")
            ok_c = st.checkbox("Je confirme cette correction (le tirage d'origine reste visible dans le Journal).")
            if st.button("Enregistrer la correction", disabled=not ok_c):
                try:
                    E.apply_correction(DB, GAME, corr["date"], corr["changes"], corr["reason"], corr["author"])
                    st.session_state.pop("corr", None)
                    st.cache_data.clear()
                    st.success("Correction enregistrée. Recharge la page pour voir la liste à jour.")
                except ValidationError as e:
                    st.error(str(e))

elif page == "Prédictions":
    st.header("Prédictions exploratoires du prochain tirage")
    st.error(PS.NOTE)
    st.markdown(
        "Chaque prédiction concerne le **prochain tirage seulement**, se fige **avant** le jour du tirage et ne se "
        "modifie jamais. Trois modèles fixés d'avance (hasard uniforme, fréquence lissée, régression logistique) sont "
        "comparés au hasard après chaque tirage. Protocole : `docs/PREDICTIONS_PROTOCOL.md`.")
    fr = st.session_state.get("frozen_result")
    if fr:
        st.success(f"Prédiction figée (n° {fr['id']}). Fichier : {fr['path']}")
        st.code(f"SHA256 : {fr['sha256']}")
        st.warning("À faire avant le tirage : commiter le fichier et publier l'empreinte pour qu'elle porte une date "
                   "publique (voir docs/PREDICTIONS_PROTOCOL.md).")
    st.subheader("Prochaine prédiction")
    if st.button("Calculer la prédiction du prochain tirage"):
        with st.spinner("Calcul en cours (environ 20 secondes)..."):
            try:
                st.session_state["pred_payload"] = with_conn(PS.prepare_prediction, game["id"],
                                                             code_commit=git_commit())
                st.session_state.pop("pred_error", None)
                st.session_state.pop("frozen_result", None)
            except ValidationError as e:
                st.session_state.pop("pred_payload", None)
                st.session_state["pred_error"] = str(e)
    if st.session_state.get("pred_error"):
        st.warning(st.session_state["pred_error"])
    payload = st.session_state.get("pred_payload")
    if payload:
        t = payload["target_date"]
        st.markdown(f"**Tirage visé : {V.weekday_fr(t)} {t}** ({payload['n_draws']} tirages utilisés, "
                    f"dernier le {payload['last_draw_date']}). Date calculée d'après le rythme lundi, mercredi, "
                    f"samedi : vérifie-la avant de figer.")
        for note in payload["notes"]:
            st.info(note)
        st.table(V.variants_table(payload))
        st.caption("Ces combinaisons n'ont aucun avantage démontré : toute combinaison a 1 chance sur "
                   "13 983 816. Elles servent à mesurer, après le tirage, si un modèle fait mieux que le hasard.")
        st.plotly_chart(prob_figure(payload["models"]))
        if WRITABLE:
            ok = st.checkbox("Je comprends que figer est définitif : la prédiction sera évaluée telle quelle.")
            if st.button("Figer cette prédiction", disabled=not ok):
                try:
                    st.session_state["frozen_result"] = E.freeze(DB, GAME, payload)
                    st.session_state.pop("pred_payload", None)
                    st.cache_data.clear()
                    st.rerun()
                except ValidationError as e:
                    st.error(str(e))
        else:
            st.info("Lecture seule. Pour figer cette prédiction, relance : python -m loto_research.dashboard --writable")
    st.subheader("Historique des prédictions figées")
    hist = with_conn(V.prediction_history, game["id"])
    if hist.empty:
        st.info("Aucune prédiction figée pour l'instant.")
    else:
        show_table(hist)
    problems = with_conn(PS.verify_frozen, game["id"], PRED_DIR)
    st.caption("Intégrité : " + ("toutes les empreintes correspondent." if not problems
                                 else "ANOMALIES : " + " ; ".join(problems)))
    st.subheader("Évaluation après les tirages")
    ev, pending = with_conn(PS.evaluations, game["id"])
    summ = PS.cumulative_summary(ev)
    n_eval = int(summ["n"].max()) if not summ.empty else 0
    st.progress(min(1.0, n_eval / PS.H010_N_STAR),
                text=f"H010 : {n_eval} / {PS.H010_N_STAR} prédictions évaluées (le test confirmatoire ne se lit "
                     f"qu'à {PS.H010_N_STAR})")
    if summ.empty:
        st.info("Aucun tirage évalué pour l'instant. Après le tirage visé, ajoute-le dans la page Tirages.")
    else:
        show_table(V.summary_view(summ))
        st.caption("Écart de log loss au hasard : négatif = mieux que le hasard. Résumé DESCRIPTIF : aucun test n'est "
                   "lu avant 500 prédictions évaluées. Bons numéros attendus par hasard : 0,735 pour une "
                   "combinaison de 6.")

elif page == "Tests":
    st.header("Tests enregistrés")
    c1, c2 = st.columns(2)
    c1.metric("Tests distincts enregistrés (par version des données)", state["tests"])
    st.caption("Chaque test réalisé augmente le risque de fausse alerte : les p-values brutes ne sont jamais à "
               "lire seules. Les résultats ci-dessous sont des résultats enregistrés, pas recalculés ici.")
    runs = with_conn(D.runs_table, game["id"])
    if runs.empty:
        st.info("Aucun lancement d'analyse enregistré. En ligne de commande : python -m loto_research.cli analyze")
    else:
        labels = {int(r.lancement): f"#{r.lancement} — {str(r.date_utc)[:19]} — {r.tirages} tirages"
                  for r in runs.itertuples()}
        run_id = st.selectbox("Lancement", list(labels), format_func=lambda i: labels[i])
        res = with_conn(D.results_table, game["id"], run_id).drop(columns="lancement")
        show_table(res.round(5).reset_index(drop=True))
    st.subheader("Registre d'hypothèses")
    hp = with_conn(D.hypotheses_progress, game["id"])
    if hp.empty:
        st.info("Aucune hypothèse enregistrée.")
    else:
        for r in hp.itertuples():
            if r.n_star:
                ratio = min(1.0, r.tirages_posterieurs / r.n_star)
                st.progress(ratio, text=f"{r.code} ({r.type}) : {r.tirages_posterieurs} / {int(r.n_star)} tirages "
                                        f"postérieurs au {r.enregistree_le}")
            else:
                st.write(f"{r.code} ({r.type}) : exploratoire, {r.tirages_posterieurs} tirages postérieurs")
        show_table(hp.reset_index(drop=True))
    st.caption("Aucun test confirmatoire ne se lance depuis cette page. En ligne de commande : "
               "python -m loto_research.cli hypothesis test NUMERO (un seul essai par hypothèse). "
               "H010 (prédictions) est décrite dans docs/PREDICTIONS_PROTOCOL.md.")

elif page == "Journal":
    st.header("Journal")
    st.subheader("Lancements d'analyse")
    runs = with_conn(D.runs_table, game["id"])
    show_table(runs) if not runs.empty else st.info("Aucun lancement enregistré.")
    st.subheader("Tirages ajoutés, par source")
    show_table(with_conn(D.ingestion_by_source, game["id"]))
    st.subheader("Corrections de tirages")
    corr_df = with_conn(D.corrections_table, game["id"])
    show_table(corr_df) if not corr_df.empty else st.info("Aucune correction enregistrée.")

elif page == "Simulateur et banc d'essai":
    st.header("Simulateur et banc d'essai")
    st.subheader("À quoi ressemble le hasard pur ?")
    c1, c2 = st.columns(2)
    label = c1.selectbox("Période comparée", list(D.PERIODS))
    seed = int(c2.number_input("Graine du hasard simulé", min_value=0, max_value=10**9, value=42, step=1))
    sub = D.filter_period(df, label)
    real = D.frequency_table(sub, K, N_MAX)
    sim = D.frequency_from_counts(D.simulate_counts(len(sub), seed, K, N_MAX), len(sub), K, N_MAX)
    left, right = st.columns(2)
    with left:
        st.markdown(f"**Tirages réels** ({len(sub)} tirages)")
        o95, ob = D.outside_counts(real)
        st.write(f"Hors bande 95 % : **{o95}** · hors bande corrigée : **{ob}**")
        st.plotly_chart(freq_figure(real, "Réel"))
    with right:
        st.markdown(f"**Hasard pur simulé** ({len(sub)} tirages, graine {seed})")
        s95, sb = D.outside_counts(sim)
        st.write(f"Hors bande 95 % : **{s95}** · hors bande corrigée : **{sb}**")
        st.plotly_chart(freq_figure(sim, f"Simulé (graine {seed})"))
    st.caption("Change la graine : le hasard pur produit lui aussi des numéros hors de la zone à 95 %, "
               "de l'ordre de 2 sur 49.")

    st.subheader("Banc d'essai du moteur de détection")
    bench = with_conn(D.bench_results)
    if bench.empty:
        st.info("Aucun banc d'essai enregistré. En ligne de commande : python scripts/m4_run_benchmark.py")
    else:
        st.markdown("Le banc injecte des biais **connus** dans des tirages simulés et mesure la part des cas "
                    "où chaque test les détecte (puissance), ainsi que ses fausses alertes sous hasard pur.")
        null = bench[bench["scenario"] == "null"].copy()
        if not null.empty:
            st.markdown("**Fausses alertes sous hasard pur (attendu : environ 5 %)**")
            v = null[["n", "test", "reps", "rate", "ci_low", "ci_high"]].copy()
            v["test"] = v["test"].map(lambda t: TESTS.get(t, "Au moins un des quatre (information)"))
            v["rate"], v["ci_low"], v["ci_high"] = 100 * v["rate"], 100 * v["ci_low"], 100 * v["ci_high"]
            v.columns = ["Tirages", "Test", "Répétitions", "Taux %", "IC bas %", "IC haut %"]
            show_table(v.round(1).reset_index(drop=True))
        c1, c2 = st.columns(2)
        scenario = c1.selectbox("Scénario de biais", [s for s in SCENARIOS if s in set(bench["scenario"])],
                                format_func=lambda s: SCENARIOS[s])
        sizes = sorted(bench[bench["scenario"] == scenario]["n"].unique())
        n = c2.selectbox("Nombre de tirages", sizes)
        sub_b = bench[(bench["scenario"] == scenario) & (bench["n"] == n)]
        fig = go.Figure()
        for t, name in TESTS.items():
            s = sub_b[sub_b["test"] == t].sort_values("level")
            if s.empty:
                continue
            fig.add_trace(go.Scatter(
                x=s["level"], y=100 * s["rate"], mode="lines+markers", name=name,
                error_y=dict(type="data", symmetric=False, array=100 * (s["ci_high"] - s["rate"]),
                             arrayminus=100 * (s["rate"] - s["ci_low"]))))
        fig.add_hline(y=80, line_dash="dash", line_color="grey", annotation_text="80 % de puissance")
        fig.update_layout(height=420, xaxis_title="Niveau du biais", yaxis_title="Détection (%)",
                          xaxis_type="log" if scenario == "dependence" else "linear",
                          yaxis=dict(range=[0, 105]), margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig)
        piv = sub_b[sub_b["test"].isin(TESTS)].pivot(index="level", columns="test", values="rate") * 100
        piv = piv.rename(columns=TESTS).round(1)
        piv.index.name = "Niveau"
        st.table(piv)
        st.caption("Un niveau où la détection atteint 100 % ne permet pas d'estimer le biais minimal détectable. "
                   "Le banc mesure la sensibilité du moteur, pas un pouvoir prédictif.")

elif page == "À propos":
    st.header("À propos")
    st.markdown(
        "**Ce que c'est.** Une boîte à outils ouverte pour auditer statistiquement les tirages d'une loterie "
        "« k numéros parmi N » : stocker les tirages, les tester avec des garde-fous (comparaisons multiples, "
        "hypothèses déclarées avant les données, aucune fuite temporelle) et vérifier les détecteurs sur des "
        "tirages simulés dont on connaît la vérité.\n\n"
        "**Ce que ce n'est pas.** Ce n'est pas un outil de pronostic. Aucune combinaison n'est recommandée, aucun "
        "numéro n'est jugé plus ou moins probable qu'un autre. Aucune conclusion de fraude n'est tirée : les sorties "
        "possibles sont « aucune anomalie détectée », « anomalie statistique » ou « anomalie robuste nécessitant une "
        "investigation complémentaire ».")
    st.subheader("Résultat de l'audit du Loto Maroc 6/49 (3 155 tirages, 2001-03-17 à 2026-09-26)")
    st.markdown(
        "**Aucune structure statistique exploitable n'a été détectée et aucun pouvoir prédictif n'a été mesuré.** "
        "Uniformité des numéros, dépendance entre tirages, ruptures, paires, triplets et modèles testés hors "
        "échantillon : aucun écart robuste. Un seul résultat isolé, sur le complémentaire, n'a pas survécu aux "
        "contrôles. Détail : `reports/FINAL.md`.")
    st.markdown(
        "**Limites.** Absence de preuve n'est pas preuve d'absence : le banc d'essai mesure qu'un biais d'un seul "
        "numéro doit atteindre environ 22 % de sa fréquence pour être détecté dans 80 % des cas (3 155 tirages). "
        "Le fichier source, récupéré sur le site officiel, a été réparé à la main sans journal, et un recoupement "
        "systématique avec le site n'est pas documenté. "
        "Aucune information physique sur la machine de tirage. Seuls le hasard, la fréquence et la régression "
        "logistique ont été testés comme modèles.")
    st.subheader("Prédictions exploratoires")
    st.markdown(
        "La page Prédictions fige, avant chaque tirage, les probabilités de trois modèles fixés d'avance et les "
        "évalue après le tirage. Statut : **non validé**, aucun modèle ne bat le hasard dans l'audit. L'hypothèse "
        "H010, pré-enregistrée, sera testée une seule fois à 500 prédictions évaluées. Détail : "
        "`docs/PREDICTIONS_PROTOCOL.md`.")
    st.subheader("Piste exploratoire H009")
    st.markdown(
        "Une faible autocorrélation du complémentaire pour les valeurs 2 et 49 a été repérée **après** avoir regardé "
        "les données : c'est une piste, pas un résultat. Elle est testée sur des tirages futurs uniquement "
        "(H009R-2 et H009R-49, 2 400 tirages, un seul essai), soit environ 15 ans. Détail : "
        "`docs/H009_PREREGISTRATION.md`.")
    st.subheader("Jeux d'argent")
    st.markdown(
        "Jouer comporte un risque de perte. Ces analyses ne changent pas l'espérance de gain d'un ticket. Si le jeu "
        "devient un problème, parlez-en à un professionnel de santé.")
