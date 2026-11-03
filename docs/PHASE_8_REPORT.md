# PHASE 8 — Construction des features

STATUT : **GO**

## Ce qui a été testé

La possibilité de construire un dataset supervisé (chronological_id, number) → target à partir de
features calculées sans fuite temporelle (data leakage), conformément à IMPLEMENTATION_SPEC §29-31
et §36. Cette phase ne teste aucune hypothèse sur le système Loto lui-même : elle valide
l'infrastructure technique nécessaire à la modélisation (Phase 9).

## Méthode

Features construites, pour chaque (tirage t, numéro i) :
- `freq_last_k` pour k ∈ {10, 20, 50, 100, 250} : nombre d'apparitions de i dans les k tirages
  précédant strictement t (t exclu)
- `gap_current` : nombre de tirages écoulés depuis la dernière apparition de i avant t (−1 si
  jamais apparu avant t)
- `prev_sum`, `prev_odd_count`, `prev_low_count` : somme / parité / répartition bas-haut du tirage
  t−1 (répétées sur les 49 lignes du tirage t)
- `prev_overlap` : intersection entre les tirages t−2 et t−1

Test de non-fuite par perturbation adversariale : à 10 points de contrôle aléatoires (seed=42), le
contenu réel des tirages d'indice ≥ t est permuté, puis le dataset complet est reconstruit à partir
de cette version perturbée. Deux vérifications :
- lignes d'indice < t : toutes les colonnes (features et cible) doivent rester identiques ;
- ligne d'indice = t : seules les colonnes de features doivent rester identiques — la cible
  (`target`) est explicitement exclue de cette comparaison car elle reflète par construction le
  contenu du tirage t (c'est l'étiquette à prédire, pas une feature prédictive).

Le détecteur a lui-même été validé en meta-test contre une fonction délibérément fautive
(utilisant la somme du tirage courant comme feature), confirmant sa capacité à détecter une vraie
fuite et non simplement à laisser passer tout dataset.

## Résultats (chiffres)

- Dataset : 3155 tirages × 49 numéros = **154 595 lignes**, 10 colonnes de features
- Test de non-fuite : **10/10 points de contrôle passés, 0 échec**
  (points testés : 280, 2437, 289, 2064, 1387, 1369, 2201, 306, 643, 2706)
- Vérification structurelle : somme des `target` = 6 pour chacun des 3155 tirages — **validée**
  (dépendance structurelle documentée ci-dessous)
- Premier tirage (chronological_id=1) : `gap_current` = −1 et `freq_last_k` = 0 pour tous les
  numéros (absence d'historique correctement traitée, aucune valeur artificielle)

## Interprétation

Le pipeline respecte strictement la règle d'absence de fuite temporelle (IMPLEMENTATION_SPEC §30 :
« toute feature au temps T doit être calculée uniquement avec des données < T »). C'est une
condition nécessaire — mais non suffisante — à la validité de toute modélisation ultérieure. Un
test de non-fuite réussi ne dit rien sur le pouvoir prédictif des features : il garantit seulement
que l'évaluation d'un futur modèle ne sera pas artificiellement gonflée par une fuite d'information.

## Limitations

- Le test de non-fuite échantillonne 10 points de contrôle sur 3155 tirages (≈0,3 %), pas une
  vérification exhaustive de tous les indices. Risque résiduel faible mais non nul qu'une fuite
  localisée à un indice non testé passe inaperçue.
- Les features sont volontairement simples (fréquences glissantes, gap, contexte limité à t−1/t−2).
  Aucune feature de fréquence de paire/triplet n'est incluse : la Phase 7 n'a trouvé aucun candidat
  significatif après correction FDR (0/1176 paires, 0/18424 triplets), donc aucune justification
  empirique à ce stade pour les inclure comme features informatives plutôt que comme bruit
  supplémentaire.
- **Dépendance structurelle (IMPLEMENTATION_SPEC §29)** : la somme des `target` valant exactement 6
  par tirage, les 49 observations d'un même tirage ne sont PAS indépendantes entre elles. Toute
  métrique ou procédure de validation en Phase 9-10 qui supposerait l'indépendance intra-tirage sans
  correction serait invalide — point à traiter explicitement en Phase 9.

## Explication alternative envisagée

Sans objet : cette phase est un travail d'ingénierie (construction d'infrastructure), pas un test
d'hypothèse sur le système physique. Le verdict porte uniquement sur la validité technique du
pipeline.

## Fichiers produits

- `data/features/FEATURES_v001.parquet` (154 595 lignes, 10 colonnes de features)
- `data/features/features_manifest.json`
- `src/loto_research/features/build.py`, `leakage.py`
- `tests/test_features.py`, `test_no_leakage.py`
- `logs/run_phase8_*.json`

## Décision

**GO.** Le test de non-fuite est passé sans exception (0/10 échecs). La Phase 9 (baselines
statistiques, puis modèles) peut démarrer, sous réserve de confirmation explicite de l'utilisateur
(règle EXECUTION_PLAN §0.6 : aucune transition automatique, même en cas de GO).
