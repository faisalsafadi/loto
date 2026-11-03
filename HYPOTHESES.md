# HYPOTHESES.md

## LOTO MAROC Research Engine — Registre des hypothèses

**Statut du document** : ACTIF, additif uniquement (aucune suppression, aucune réécriture rétroactive).
**Date de création** : 2026-09-27
**Créé avant** : Phase 1 (import des données). Aucune donnée n'a été observée au moment de la rédaction de ce document.
**Règle absolue** : toute hypothèse ajoutée après observation d'un résultat intéressant dans les données doit être marquée `POST_HOC` et ne peut jamais devenir `CONFIRMATORY`, quelle que soit la force du résultat.

Statuts autorisés (IMPLEMENTATION_SPEC §46) :
`UNTESTED` · `EXPLORATORY` · `SUPPORTED` · `REJECTED` · `REPLICATED` · `PREDICTIVE` · `FAILED_OUT_OF_SAMPLE`

---

### H000 — Hypothèse-cadre du projet (méta-hypothèse, à ne jamais retirer)

| Champ | Valeur |
|---|---|
| ID | H000 |
| Type | CONFIRMATORY (pré-enregistrée) |
| Description | Attente de base du domaine, indépendante des données Loto Maroc |
| H0 | Le Loto Maroc se comporte comme un système de tirage aléatoire uniforme sans structure exploitable, conforme à l'expérience générale des loteries réglementées étudiées dans la littérature |
| H1 | Il existe au moins une structure statistique robuste (niveau C) et prédictive hors-échantillon (niveau D) |
| Variable | — (cadrage général) |
| Test | Ensemble du programme expérimental (phases 3 à 10) |
| Seuil | N/A — hypothèse de cadrage |
| Correction | N/A |
| Données utilisées | Aucune au moment de la rédaction |
| Date de création | 2026-09-27 |
| Statut | UNTESTED |
| Note | **Le taux de base attendu, avant toute analyse, favorise fortement H0.** Ce prior est documenté ici pour empêcher qu'un futur NO-GO soit interprété comme une surprise, ou qu'un futur résultat "intéressant" soit surinterprété faute d'avoir noté l'attente initiale. |

---

### H001 — Équirépartition des numéros principaux

| Champ | Valeur |
|---|---|
| H0 | Les 49 numéros principaux ont une probabilité d'apparition égale (p = 6/49 chacun) |
| H1 | Au moins un numéro s'écarte significativement de p = 6/49 |
| Variable | Fréquence d'apparition par numéro (1–49) |
| Test | χ² d'équirépartition |
| Seuil | α = 0.05, ajusté |
| Correction | Holm (49 tests simultanés si test numéro par numéro) |
| Données utilisées | Dataset ANALYTIC complet (Phase 3) |
| Statut | REJECTED (H1 non supportée : Monte-Carlo p=0.89854, 100000 sim., seed 42, 2026-09-29) |
| Type | CONFIRMATORY |

---

### H002 — Équirépartition du numéro complémentaire

| Champ | Valeur |
|---|---|
| H0 | Le complémentaire suit une distribution uniforme sur son espace de valeurs propre (à définir selon règles officielles, cf. §6 Cahier des charges) |
| H1 | Le complémentaire s'écarte significativement de l'uniformité |
| Variable | Fréquence du complémentaire |
| Test | χ² (modèle propre au complémentaire) |
| Seuil | α = 0.05 |
| Correction | N/A (test unique) |
| Données utilisées | Dataset ANALYTIC complet |
| Statut | SUPPORTED (Niveau B, Phase 3 : chi2(48)=69.355, p=0.0235) — N'A PAS SURVECU pour devenir Niveau C : ni localisation par numero (Phase 4, 0/49 apres FDR-BH) ni instabilite temporelle (Phase 5, homogeneite inter-periodes p=0.5418) ne corroborent le signal. Traite comme compatible avec du bruit d'echantillonnage (2026-09-29). |
| Type | CONFIRMATORY |

---

### H003 — Indépendance entre tirages consécutifs

| Champ | Valeur |
|---|---|
| H0 | Le nombre de numéros communs entre deux tirages consécutifs suit la distribution attendue sous tirage indépendant sans remise |
| H1 | La distribution observée des répétitions diffère de la distribution théorique/simulée |
| Variable | Intersection(tirage T, tirage T-1) |
| Test | Comparaison empirique vs distribution Monte-Carlo |
| Seuil | α = 0.05 |
| Correction | N/A (test unique par nature) |
| Données utilisées | Dataset ANALYTIC complet |
| Statut | REJECTED (H1 non supportée : permutation p=0.94615, 20000 perms, seed 42, sur 3124 paires reellement consecutives (amendement A5), 2026-09-29) |
| Type | CONFIRMATORY |

---

### H004 — Distribution des gaps (écarts entre apparitions)

| Champ | Valeur |
|---|---|
| H0 | Pour chaque numéro, la distribution des gaps est compatible avec un processus géométrique correspondant à p = 6/49 |
| H1 | Au moins un numéro présente une distribution de gaps significativement différente du modèle nul |
| Variable | gap_current, gap_mean, gap_median, distribution complète par numéro |
| Test | Comparaison à la distribution nulle simulée (Monte-Carlo) |
| Seuil | α = 0.05, ajusté |
| Correction | FDR (Benjamini-Hochberg), 49 tests |
| Données utilisées | Dataset ANALYTIC complet |
| Statut | REJECTED (H1 non supportée : loi geometrique exacte p=6/49, 0/49 numeros significatifs apres FDR-BH, 2026-10-01 ; extension exploratoire complementaire egalement 0/49) |
| Type | CONFIRMATORY |
| Note | Un gap long ne doit jamais être interprété comme "probabilité future accrue" sans test empirique hors-échantillon (cf. §14 Cahier des charges) |

---

### H005 — Absence de structure dans les paires de numéros

| Champ | Valeur |
|---|---|
| H0 | La fréquence d'apparition conjointe de chaque paire (i, j) est compatible avec le hasard (indépendance des tirages, p uniforme) |
| H1 | Au moins une paire apparaît avec une fréquence significativement différente de l'attendu, après correction |
| Variable | Fréquence observée de chaque paire parmi les 1 176 possibles |
| Test | Comparaison à distribution nulle simulée |
| Seuil | α = 0.05, ajusté |
| Correction | FDR obligatoire (1 176 tests) |
| Données utilisées | Dataset ANALYTIC complet |
| Statut | REJECTED (0/1176 candidats apres FDR-BH en exploration, 2026-10-01 ; aucune paire n'a meme atteint l'etape de confirmation hors-echantillon) |
| Type | EXPLORATORY (pipeline en 4 niveaux : exploration → filtrage → validation → confirmation hors-échantillon, cf. §17 Cahier des charges) |

---

### H006 — Absence de structure dans les triplets

| Champ | Valeur |
|---|---|
| H0 | La fréquence d'apparition conjointe de chaque triplet (i, j, k) est compatible avec le hasard |
| H1 | Au moins un triplet apparaît avec une fréquence significativement différente de l'attendu, après correction et validation hors-échantillon |
| Variable | Fréquence observée de chaque triplet parmi les 18 424 possibles |
| Test | Comparaison à distribution nulle simulée (effectifs attendus très faibles → Monte-Carlo exact requis, pas de χ² asymptotique) |
| Seuil | α = 0.05, ajusté |
| Correction | FDR obligatoire (18 424 tests) |
| Données utilisées | Dataset ANALYTIC complet |
| Statut | REJECTED (0/18424 candidats apres FDR-BH en exploration, 2026-10-01 ; aucun triplet n'a meme atteint l'etape de confirmation hors-echantillon) |
| Type | EXPLORATORY par construction — ne peut jamais devenir CONFIRMATORY sans confirmation hors-échantillon indépendante |

---

### H007 — Stabilité des propriétés statistiques dans le temps (absence de rupture non expliquée)

| Champ | Valeur |
|---|---|
| H0 | Les propriétés statistiques (fréquences, sommes, parité) sont stables à travers les périodes 2001–2005, 2006–2010, 2011–2015, 2016–2020, 2021–2026, une fois les changements de règles/calendrier/matériel connus pris en compte |
| H1 | Il existe au moins une rupture non expliquée par un changement connu (règles, calendrier, matériel, fréquence des tirages) |
| Variable | Statistiques descriptives par période |
| Test | CUSUM / change-point / comparaison inter-périodes |
| Seuil | α = 0.05 |
| Correction | Selon nombre de comparaisons inter-périodes |
| Données utilisées | Dataset ANALYTIC complet, stratifié par période et par régime de règles connu |
| Statut | REJECTED (H1 non supportée : homogeneite chi2 confirmee - principaux chi2=178.99 df=192 p=0.7406 ; complementaire chi2=189.29 df=192 p=0.5418 - 2026-09-29) |
| Type | CONFIRMATORY |
| Note | Toute rupture détectée doit être testée contre les explications alternatives (changement de règles, de calendrier, de matériel, de fréquence) avant toute autre interprétation. Ne jamais interpréter comme preuve de fraude. |

---

### H008 — Absence de pouvoir prédictif des modèles ML/statistiques par rapport au hasard (hypothèse centrale du projet)

| Champ | Valeur |
|---|---|
| H0 | Aucun modèle (fréquentiste, Markov, ML) n'améliore significativement les performances hors-échantillon par rapport à `baseline_random` et `frequency_baseline` |
| H1 | Au moins un modèle apporte une amélioration hors-échantillon reproductible et statistiquement défendable |
| Variable | log loss, Brier score, top-k hit rate, calibration — mesurés en walk-forward strict |
| Test | Comparaison modèle vs baselines sur données jamais utilisées pour l'entraînement (Phase 10) |
| Seuil | Dépend de la métrique — effect size + IC + p-value ajustée, pas de seuil arbitraire (§58 IMPLEMENTATION_SPEC) |
| Correction | FDR/Holm si plusieurs modèles/fenêtres testés — **toute configuration essayée doit être journalisée dans `research_audit.json`, y compris celles non retenues**, pour éviter le p-hacking au niveau de la sélection de modèle |
| Données utilisées | Walk-forward complet, aucune donnée ≥ T utilisée pour prédire T |
| Statut | REJECTED (H1 rejetée ; H0 confirmée hors-échantillon -- Phase 10, walk-forward expanding window, n=2655 tirages indépendants, 2026-10-06) |
| Type | CONFIRMATORY — hypothèse centrale, prior fortement en faveur de H0 (cf. H000) |
| Note | C'est la seule hypothèse dont la confirmation (H1) constituerait un résultat de niveau D. Toutes les autres hypothèses (H001–H007) restent au maximum niveau C. |

#### Extension H008-b — Numéros à probabilité prédite la plus basse ("numéros déconseillés")

Ajout du 2026-09-27, formulé avant toute observation de données (pré-enregistré, pas POST_HOC) : à la demande de l'utilisateur, la sortie de prédiction (§29 Cahier des charges, §37 IMPLEMENTATION_SPEC) devra présenter, en plus des numéros à probabilité prédite la plus haute, les numéros à probabilité prédite la plus basse — un même tableau de probabilités par numéro, lu à ses deux extrémités.

**Ceci n'est pas une nouvelle hypothèse statistique.** C'est la même hypothèse H008, avec la même exigence de preuve :

- Cette sortie ne peut être renseignée qu'à partir du modèle validé en Phase 10 (walk-forward, hors-échantillon), jamais à partir de la fréquence historique brute ou du gap seul.
- Un numéro rare historiquement ou en gap long n'est **jamais** présenté comme "moins probable de sortir" sans cette validation — ce serait le sophisme symétrique du "numéro chaud" que le §11 du Cahier des charges interdit déjà explicitement.
- Si la Phase 10 conclut `NO-GO` (hypothèse par défaut, cf. H000), la sortie officielle sera : *"sous H0, tous les numéros sont statistiquement équiprobables ; aucun numéro ne présente de risque supérieur ou inférieur significatif à un autre"* — jamais une liste construite pour donner une impression de résultat exploitable.
- Si utilisée à titre exploratoire uniquement (cf. §11 EXECUTION_PLAN, cas d'un NO-GO en Phase 10 avec prédictions exploratoires), elle porte la même étiquette de non-validation statistique que les numéros favorisés.

Statut : REJECTED (résolu par H008, Phase 10, 2026-10-06). Sortie officielle retenue : « sous H0, tous les numéros sont statistiquement équiprobables ; aucun numéro ne présente de risque supérieur ou inférieur significatif à un autre. » Aucune liste de numéros favorisés ou déconseillés n'est produite.

---

## Amendements pré-enregistrés du 2026-09-28 (avant Phase 1 — aucune donnée observée)

**A1 — Loi de référence de H001/H002.** La loi nulle de la statistique χ² n'est pas χ²(48) (espérance 43, pas 48 ; voir Cahier §12, A1). H001 est testée par p-value Monte-Carlo. Le test asymptotique df=48 n'est plus une référence. Statut de H001 inchangé (UNTESTED, CONFIRMATORY).

**A2 — Tests primaires désignés à l'avance (un par famille).**
| Famille | Test PRIMAIRE (confirmatoire) | Rapportés à titre descriptif (non testés) |
|---|---|---|
| Uniformité des fréquences | χ² de Pearson, p-value Monte-Carlo (100 000 sim., seed 42) | G-test, entropie, KL, Jensen-Shannon, information de Fisher (même information, cf. IMPLEMENTATION_SPEC A2) |
| Dépendance temporelle | Nombre moyen de numéros communs entre tirages consécutifs, p-value par permutation de l'ordre | Ljung-Box sur la somme, runs tests (EXPLORATORY) |
| Stabilité (H007) | Comparaison inter-périodes sur le découpage unique ci-dessous | Toute autre segmentation = POST_HOC |

**A3 — Découpage temporel unique (H007).** 2001–2005, 2006–2010, 2011–2015, 2016–2020, 2021–2026 (Cahier §18). Le découpage en blocs de 500 tirages évoqué dans une analyse externe n'est PAS utilisé : le choix d'un découpage après observation est un degré de liberté du chercheur. Tout autre découpage essayé sera journalisé dans `research_audit.json` et marqué POST_HOC.

**A4 — Fisher et Finite Free Probability.** Aucune hypothèse créée. La Fisher est descriptive ; la Finite Free Probability est écartée faute de question testable. Une éventuelle réouverture exigerait une hypothèse datée et marquée selon la règle générale.

---

## Journal des ajouts

| Date | ID | Action | Auteur |
|---|---|---|---|
| 2026-09-27 | H000–H008 | Création initiale, pré-enregistrement avant Phase 1 | Claude (responsable scientifique du projet) |
| 2026-09-27 | H008-b | Ajout de l'extension "numéros déconseillés" (probabilité prédite la plus basse), pré-enregistrée avant Phase 1, à la demande de l'utilisateur | Claude (responsable scientifique du projet) |

*Toute hypothèse future ajoutée après le début de l'analyse des données doit être insérée ci-dessous avec la mention explicite `POST_HOC` et la date exacte d'ajout.*
| 2026-10-06 | H008, H008-b | Résolution officielle par la Phase 10 (walk-forward, n=2655 tirages, expanding window, test_no_future_features revérifié sur 20 points de contrôle) : H1 rejetée -- aucun modèle n'améliore les performances hors-échantillon ; frequency_baseline et logistic_regression sont significativement MOINS bons que baseline_random après correction de Holm (p_holm<0.05 pour les 3 comparaisons, IC bootstrap excluant 0), effet de taille négligeable (0,015%-0,098% de log loss). H008-b résolu en conséquence : sortie officielle = équiprobabilité, aucune liste de numéros favorisés/déconseillés. | Claude (responsable scientifique du projet) |
| 2026-09-28 | A1–A4 | Amendements pré-enregistrés avant Phase 1 (loi nulle du χ², tests primaires par famille, découpage temporel unique, statut Fisher/FFP) | Claude (responsable scientifique du projet) |

## Amendements A5-A6 du 2026-09-28
Définis APRÈS l'inspection de la structure du fichier (ordre, calendrier, numérotation) et AVANT toute statistique sur les numéros tirés.

**A5 — Tirages consécutifs (H003 ; intervalles de H004).** Le RAW compte environ 42 tirages numérotés mais absents. Le test primaire de H003 n'utilise que les paires (T-1, T) où (a) les numéros N se suivent (ou N = 1 en début d'année) ET (b) l'écart de dates est ≤ 4 jours. Les paires exclues sont comptées et rapportées ; le résultat sur toutes les paires est rapporté à titre descriptif. Les intervalles de H004 traversant un tirage absent sont traités comme censurés (méthode fixée en Phase 3, avant tout calcul).

**A6 — Changement de calendrier connu (H007).** Les tirages passent de 2 par semaine (mercredi, samedi) à 3 (lundi, mercredi, samedi) entre 2015 et 2016, quasiment à la frontière des périodes 2011-2015 et 2016-2020. Toute différence entre ces deux périodes est attribuée en premier lieu à ce changement et ne peut en être séparée avec ces données. Toute segmentation supplémentaire par régime de calendrier serait POST_HOC.

## Amendement A7 et note de transparence du 2026-09-28

**A7 — Loi nulle du complémentaire (H002).** Si le complémentaire est tiré sans remise parmi les 43 numéros
restant après les 6 principaux (hypothèse de travail retenue, cf. argument du rang 2 de gain et absence
documentée de doublon C/principaux), sa loi MARGINALE reste uniforme sur 49 : chaque tirage ne fournit
qu'une seule catégorie tirée (pas de sélection multiple corrélée comme pour les 6 principaux). Le test
primaire de H002 est donc un χ²(48) classique (PAS de facteur correctif type A1/A2, qui ne concerne que
les 6 principaux). Confirmation empirique décisive : le flag BONUS_IN_MAIN de la Phase 2 (0 occurrence
attendue si l'hypothèse est vraie, ~12,24% sinon).

**Note de transparence — exposition préalable non contrôlée.** Le fichier `a_lire` du projet rapporte des
résultats produits par un outil tiers non audité sur une version antérieure des données, incluant un signal
sur le complémentaire concentré autour de 2015-2019 (p rapportés : 0,02348 global, 0,0003 sur une fenêtre
glissante 05/09/2015-14/01/2019). Cette analyse externe présente un p-hacking non corrigé manifeste
(balayage de fenêtres et d'années, sélection du minimum). AUCUN de ces chiffres n'est retenu comme fait.
Mais Claude (responsable scientifique) a eu connaissance de cette piste AVANT tout calcul propre au projet
sur H002/H007. Toute future détection du système touchant le complémentaire autour de 2015-2019 devra être
signalée comme potentiellement non naïve du fait de cette exposition, jamais présentée comme une
confirmation aveugle. Le découpage temporel pré-enregistré (A3 : blocs de 5 ans du Cahier §18) n'a PAS été
choisi en fonction de cette fenêtre et reste la référence confirmatoire.

## Note POST_HOC du 2026-09-30 — ruptures.Pelt sur le complémentaire (fermée sans suite)
Exploration (Phase 5 addendum) : ruptures.Pelt (penalite log(n)*variance) trouve 4 ruptures sur la
sequence du complementaire (dates 2003-08-27, 2006-04-22, 2017-09-20, 2018-03-31). Calibration Monte-Carlo
(5000 sim., seed 42) : P(>=4 ruptures sous bruit pur) = 0.045. Resultat a la limite du seuil, contredit
par le CUSUM (test primaire, p=0.528) sur le meme signal, et compatible avec le taux de faux positifs
attendu sur l'ensemble des tests des Phases 3-5. FERME SANS INVESTIGATION SUPPLEMENTAIRE : aucune
hypothese nouvelle creee, aucune Phase dediee. Marque ici uniquement pour tracabilite complete
(research_audit.json, IMPLEMENTATION_SPEC §56).

---

## Note POST_HOC du 2026-10-08 — H009 : autocorrélation lag-1 du complémentaire (EXPLORATORY)

Inscription tardive : cette entrée était exigée dès le 2026-09-30 par l'addendum de TEMPORAL_REPORT.md
(« tout numéro flagué ici doit être ajouté à HYPOTHESES.md comme POST_HOC avant toute investigation
ultérieure »). Elle n'a été inscrite que le 2026-10-08, à la rédaction de FINAL.md. À ma connaissance,
aucune investigation sur ces valeurs n'a eu lieu entre-temps ; ce point reste à confirmer par l'utilisateur.

| Champ | Valeur |
|---|---|
| ID | H009 |
| Type | EXPLORATORY / POST_HOC — ne peut JAMAIS devenir CONFIRMATORY sur DATASET_v001 |
| Origine | Addendum Phase 5 (2026-09-30) : test d'autocorrélation lag-1 par numéro, non pré-enregistré avant la Phase 1 |
| H0 | Pour chaque valeur k du complémentaire, l'indicateur « complémentaire = k » n'a pas d'autocorrélation lag-1 |
| H1 | Au moins une valeur du complémentaire présente une autocorrélation lag-1 |
| Test | Autocorrélation lag-1 par valeur, correction FDR-BH sur la famille de 49 valeurs |
| Données utilisées | DATASET_v001 complet (déjà observé : aucune confirmation n'est possible dessus) |
| Observation | 0/49 numéros principaux et 2/49 valeurs du complémentaire significatifs après FDR-BH. Valeurs concernées (complémentaire) : **2** (ρ = +0,0569 ; z = 3,20 ; p = 0,00138) et **49** (ρ = +0,0563 ; z = 3,16 ; p = 0,00157), q BH = 0,0386 chacune dans la famille de 49. Réserves : (a) Holm/Bonferroni sur 49 ne les retiendraient pas (p×49 = 0,068 et 0,077) ; (b) un BH conjoint sur les 98 tests (principaux + complémentaire) donnerait q ≈ 0,077 si aucun p principal n'est plus petit (p principaux non revus à l'inscription) ; (c) probabilité, sous H0, que les 2 plus petits p sur 49 soient ≤ 0,00157 : ≈ 0,003 (calcul approché fait à l'inscription) ; (d) valeurs suivantes, non retenues : 23 (p = 0,0126), 4 (0,0196), 38 (0,0273). Effet : ρ ≈ 0,057 (z = ρ√n, n = 3155). |
| Statut | EXPLORATORY |
| Note | L'écart d'uniformité du complémentaire (H002, p brut = 0,0235) porte sur une propriété différente et ne corrobore pas ces signaux. Le fait que les deux concernent le complémentaire est noté sans interprétation. |
| Confirmation possible | Uniquement sur des tirages postérieurs au 2026-09-26, avec un test pré-enregistré (valeurs 2 et 49, sens positif, seuil) AVANT de les lire. Puissance (calcul approché) : pour un ρ vrai de 0,057 (probablement surestimé, effet du maximum sélectionné), ≈ 2 400 tirages seraient nécessaires pour 80 % de puissance (test unilatéral, α = 0,025), soit une quinzaine d'années à 3 tirages par semaine ; avec 300 tirages la puissance serait d'environ 17 %. Les nouveaux tirages de la Phase 12 ne suffisent donc pas en pratique à trancher H009. |

## Enregistrement prospectif de H009 — 2026-10-31 (PRE_REGISTERED, tirages futurs uniquement)
H009R-2 et H009R-49 : autocorrélation lag-1 positive de l'indicateur « complémentaire = v », v = 2 et v = 49.
Famille de 2, Bonferroni, test unique à n_star = 2400 tirages postérieurs à la date d'enregistrement.
H009 (POST_HOC) reste exploratoire et ne devient jamais confirmatoire. Détails : docs/H009_PREREGISTRATION.md.

## H010 — 2026-11-01 (PRE_REGISTERED, prédictions exploratoires figées)
Frequency et logistique réduisent-ils le log loss par rapport au hasard uniforme sur les prédictions figées avant
chaque tirage ? Wilcoxon unilatéral apparié, Holm sur 2 comparaisons, alpha 0,05, test unique à n_star = 500
prédictions évaluées. Résumés descriptifs seulement avant. Modèles fixés (hasard, fréquence alpha 10, logistique C 1,0).
Détail : docs/PREDICTIONS_PROTOCOL.md. Statut du résultat attendu : H0 non rejetée (Phase 10 : modèles moins bons que le hasard).
