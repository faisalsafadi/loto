# Source des données / Data source

**English summary.** `loto_maroc_draws.csv` lists the draws of Morocco's Loto 6/49, retrieved from the official lottery
website (https://www.eloterie.ma/resultats). It is provided for convenience and to make the audit reproducible. If you
hold rights over this content and want it removed, open an issue: it will be removed from the repository.

---

## Contenu

- `loto_maroc_draws.csv` : les tirages du Loto 6/49 marocain, une ligne par tirage, du 2001-03-17 à la date d'export.
- Colonnes : `date`, `n1` à `n6` (dans l'ordre de la source), `bonus` (complémentaire), `source`, `source_ref`, `draw_no`
  (numéro de tirage officiel, qui repart chaque année ; il peut être vide).
- Les valeurs corrigées sont appliquées à l'export (aucune correction à ce jour).
- Ce fichier ne contient **que** des tirages : pas d'hypothèses, pas de prédictions, pas de journaux.

## Provenance

- Source : le site officiel de la loterie, page des résultats (https://www.eloterie.ma/resultats).
- Les 3 155 premiers tirages (colonne `source` = `DATASET_v001`, du 2001-03-17 au 2026-09-26) viennent d'un fichier
  tableur récupéré sur le site, puis **réparé à la main avant l'import, sans journal des modifications**. 3 155 tirages
  ont été retenus au lieu des 3 159 annoncés. Un recoupement systématique avec le site n'est pas documenté : la
  provenance est connue, l'exactitude de chaque numéro n'est pas démontrée.
- Les tirages suivants ont été ajoutés un par un, avec leur source.
- Le fichier tableur d'origine n'est pas redistribué ; son empreinte SHA256 est
  `eb5b5be17b050542b721cea1ad09e71ffc29b1dbfa92742647162c3d7eeb246b`.

## Droits et retrait

Les résultats d'un tirage sont des faits publiés par l'opérateur. Ce dépôt les fournit par commodité, avec leur source,
pour rendre l'audit reproductible. Si tu détiens des droits sur ce contenu et souhaites son retrait, ouvre une issue :
le fichier sera retiré du dépôt, et l'outil continuera de fonctionner avec des données importées par chacun
(`loto add-csv`, ou la page Tirages du tableau de bord).

## Vérifier l'intégrité

Après `loto init-db`, la commande affiche l'empreinte des données (début). Elle doit être identique à celle publiée
dans les notes de version pour la version du CSV utilisée.
