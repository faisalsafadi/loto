### Phase 0 — Initialisation du projet
STATUT : BLOCKED (partiel — dependances)

Ce qui a ete teste : conformite de l'arborescence, de la config, des registres, de l'environnement Python et des dependances.
Methode : verification programmatique (existence des dossiers, parsing YAML/JSON/TOML, imports Python).
Resultats :
- Arborescence : conforme (0 dossier manquant). Ecart assume : sous-paquets dans src/loto_research/ (et non src/ directement) afin que `python -m loto_research.pipeline` (spec 62-66) soit possible.
- Python 3.12.3 : OK (>= 3.12).
- default.yaml, research_audit.json, pyproject.toml : valides. registry.csv : en-tetes conformes a spec 45.
- HYPOTHESES.md : H000-H008 + H008-b presentes (pre-enregistrees avant toute donnee).
- Git : depot initialise, premier commit e6e487fa520f2bf29437fe7f73fc1b1b63f9fddc.
- Dependances installees : pandas 3.0.2, numpy 2.4.4, scipy 1.17.1, scikit-learn 1.8.0, openpyxl 3.1.5, matplotlib 3.10.8, PyYAML 6.0.3, seaborn 0.13.2.
- Dependances MANQUANTES : statsmodels, pyarrow, pytest, ruptures. Cause : reseau desactive dans l'environnement, `pip install` echoue.
Interpretation : le critere GO "dependances installees et verrouillees" n'est pas atteint. Le verrouillage (requirements.lock.txt) est PARTIEL : il ne liste que les paquets reellement installes ; aucune version n'a ete inventee pour les manquants.
Limitations : sans pyarrow, pas de Parquet (Phase 2) ; sans pytest, pas de tests automatises (Phase 2+) ; sans statsmodels, pas d'autocorrelation (Phase 5) ; sans ruptures, pas de change-point (Phase 5).
Explication alternative envisagee : aucune (probleme purement logistique, sans lien avec les donnees).
Fichiers produits : voir le depot (pyproject.toml, configs/default.yaml, HYPOTHESES.md, experiments/registry.csv, research_audit.json, requirements.lock.txt, docs/).
Decision : Phase 1 (import RAW, SHA256, comptage) n'exige que pandas+openpyxl, deja disponibles. Phase 2 exige pyarrow+pytest : elle restera BLOCKED tant que ces paquets ne sont pas installes.

---
Addendum 2026-09-28 — cloture de la Phase 0
STATUT : GO
Environnement utilisateur (Ubuntu) : Python 3.12.3 ; pandas 3.0.6, numpy 2.5.3, scipy 1.18.1, statsmodels 0.15.0, scikit-learn 1.9.1, pyarrow 25.0.1, matplotlib 3.11.2, pytest 9.1.1, PyYAML 6.0.3, ruptures 1.1.10, openpyxl 3.1.5.
Verrouillage : requirements.lock.txt (pip freeze --exclude-editable, 33 lignes) ; ces versions remplacent le lock partiel initial.
Commits : e6e487f (initialisation), 569b9f4 (dependances + amendements A1-A4).
Incident : un doublon "Cahier_des_charges (1)" a ete commite par erreur (nom de telechargement) ; supprime par un nouveau commit, sans reecriture d'historique.
Amendements A1-A4 : integres avant toute observation de donnees.
