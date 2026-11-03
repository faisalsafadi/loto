# ANOMALY_REPORT.md

## LOTO MAROC Research Engine — Recherche d'anomalies (Phase 4)

Généré le 2026-09-29T09:05:15.466837+00:00. Dataset : DATASET_v001, 3155 tirages.

Aucune anomalie de ce rapport n'est présentée sans sa p-value corrigée. Aucune anomalie, quel que soit son niveau, n'est interprétée comme une preuve de fraude ou de trucage (Cahier des charges §37) — au plus, une anomalie statistique nécessitant investigation.

**Absence d'information physique** : aucune donnée sur l'état, l'usure ou la calibration des boules et de la machine n'est disponible (RESEARCH_REVIEW.md §1.2) ; toute anomalie de fréquence ou de position reste une observation statistique, jamais une preuve mécanique.

## OBSERVATION

- [A] Fréquence par numéro principal : 49 tests (méthode holm, pré-enregistrée H001).
- [B] Fréquence par numéro du complémentaire : 49 tests (méthode fdr_bh, EXPLORATOIRE — approfondit le signal Niveau B de la Phase 3).
- [C] Biais de position (n1..n6) : 6 tests lancés (méthode bonferroni), puis **RÉTRACTÉS** — voir section de rétractation en fin de rapport. Ne comptent pas dans les anomalies retenues.
- Total : 104 tests.

## CALCUL

### [A] Numéros principaux — niveau B après correction Holm
  Aucun numéro de niveau B.

### [B] Complémentaire — niveau B après correction FDR-BH
  Aucun numéro de niveau B.

### [C] Positions — RÉTRACTÉ (voir section de rétractation)
  Résultats bruts conservés pour traçabilité, NE SONT PAS des anomalies : chi2 énormes (1907-7980,
  df=48, p=0 aux 6 positions) causés par un modèle nul invalide, pas par un biais quelconque.
  - n1 : chi2=7797.84 (df=48) -- n2 : chi2=2903.00 -- n3 : chi2=2007.46
  - n4 : chi2=1906.85 -- n5 : chi2=2937.60 -- n6 : chi2=7979.93

## INTERPRÉTATION

- 0 numéro de niveau B retenu sur les familles [A] et [B] (98 tests). Les 6 résultats de la famille [C] sont RÉTRACTÉS (modèle nul invalide, voir plus bas), pas comptés comme anomalies.
- Le Niveau B signifie « anomalie statistique brute » (Cahier §2) : cela NE constitue PAS un Niveau C (anomalie robuste), qui exige la survie à une investigation multi-période/indépendante (Phases 5 et 7), ni a fortiori un Niveau D (pouvoir prédictif, Phase 10).
- [B] et [C] sont des recherches EXPLORATOIRES au sens de HYPOTHESES.md : toute anomalie qui y serait détectée doit être ajoutée à HYPOTHESES.md comme POST_HOC avant d'être creusée plus loin.

## LIMITATION

- [C] repose sur une hypothèse NON vérifiée (colonnes = ordre réel de tirage). Un résultat significatif ici pourrait aussi bien refléter un artefact de saisie qu'un biais mécanique réel : aucune conclusion mécanique ne peut être tirée sans confirmation de la source des données.
- La correction multiple est appliquée PAR FAMILLE (A, B, C séparément), pas globalement sur l'ensemble du projet — une correction globale de bout en bout est prévue en synthèse finale (Phase 14).
- Les tests exacts (binomiaux, position) ne souffrent pas de la corrélation intra-tirage qui affecte le test joint des 6 numéros (Phase 3, amendement A1) : ils testent chaque numéro/position indépendamment, ce qui est statistiquement valide mais ne teste pas les dépendances conjointes (paires/triplets, prévues Phase 7).

## RÉTRACTATION POST-HOC — [C] Biais de position

Diagnostic effectué APRÈS avoir observé les chi2 anormalement élevés (scripts/diagnostic_position_order.py,
lecture seule) : **99,90% des lignes (3152/3155) ont n1<n2<...<n6** (triées par ordre croissant). n1 est le
minimum des 6 dans 100% des cas, n6 le maximum dans 99,94%.

**Conséquence** : le test [C] supposait que n1..n6 représentent l'ordre réel de sortie des boules (position
physique), avec un modèle nul d'uniformité par position. C'est FAUX pour 99,90% des données : ce sont des
STATISTIQUES D'ORDRE (min, 2e plus petit, ..., max) d'un tirage sans remise, qui ne sont JAMAIS
marginalement uniformes par construction, quelle que soit l'équité du tirage. Les chi2 énormes ne sont donc
pas une anomalie — ils confirment simplement que les données sont triées, ce qu'un test bien spécifié
aurait dû anticiper. Le test [C] est retiré du décompte des anomalies ; aucune anomalie de position n'est
affirmée, ni infirmée : la question reste NON TESTÉE faute de données dans le bon ordre.

**Observation annexe (factuelle, pas un test statistique — n=3, non exploitable)** : les 3 lignes NON
triées sont chronological_id 2333 (2021-06-26 : 2,8,3,20,23,25 — ressemble à une simple interversion de
saisie), 3154 (2026-09-23) et 3155 (2026-09-26) — ces deux dernières étant les DEUX DERNIERS tirages du
fichier, mélangés en profondeur, compatible avec un ordre de tirage réel non encore trié par la source au
moment de la mise à jour la plus récente. À surveiller en Phase 12 (intégration des nouveaux tirages) :
si de futurs tirages arrivent non triés puis sont ensuite "normalisés" par la source, cela confirmerait
que la colonne perd l'information de position dès qu'un tirage est archivé.

**Décision** : le §20 du Cahier (biais de position) est déclaré NON TESTABLE avec ces données (colonnes
pré-triées par la source à 99,90%). Aucune correction du test n'est tentée (un test sur les statistiques
d'ordre serait redondant avec H001, déjà testée en Phase 3 par Monte-Carlo, p=0,899).
