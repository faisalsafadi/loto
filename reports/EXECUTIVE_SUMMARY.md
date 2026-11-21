# EXECUTIVE SUMMARY — LOTO MAROC Research Engine

Date : 2026-10-08 — Responsable scientifique du projet

## La question

Les 3155 tirages du Loto Maroc 6/49 (mars 2001 → septembre 2026) contiennent-ils une structure
statistique exploitable, et un modèle entraîné sur cet historique peut-il prédire les tirages
suivants mieux que le hasard ?

## La réponse

**Non, sur tout ce qui a été testé.** Aucune anomalie robuste, aucune dépendance entre tirages,
aucune rupture non expliquée, aucune paire ni aucun triplet qui se distingue après correction des
comparaisons multiples. Les deux modèles testés sur l'historique (fréquence, régression
logistique) font **légèrement moins bien** que l'hypothèse « tous les numéros ont la même
probabilité », sur 2655 prédictions hors-échantillon (écart de 0,015 % à 0,098 % de log loss :
statistiquement net, pratiquement négligeable).

## Ce que cela signifie

- Aucun numéro ni aucune combinaison n'est statistiquement préférable à un autre sur ces données.
- Il n'y a pas de liste de numéros « favorisés » ou « déconseillés » à produire.
- Les prédictions fondées sur l'historique (numéros « chauds », « en retard ») ne sont pas
  soutenues par les données : le modèle de fréquence, qui les traduit directement, a été le moins
  bon des trois.

## Ce que cela ne signifie pas

- Ce n'est pas une preuve d'équité du tirage. Une structure subtile (écart de quelques pour cent
  sur un numéro) ou une manipulation intermittente ne serait pas détectée par ces tests.
- Le fichier source a été réparé avant import (modifications non documentées) et il manque 4
  tirages sur les 3159 annoncés : un contrôle contre une source officielle reste à faire.
- Seuls trois modèles simples ont été testés ; des modèles plus complexes n'ont pas été essayés
  parce que le modèle précédent ne le justifiait pas.
- Le projet n'a pas étudié les gains ni les mises : il ne dit rien sur le rendement espéré d'un
  ticket.

## Résultats isolés à connaître

Le numéro complémentaire montre un écart d'uniformité de niveau « suggestif » (p brut = 0,0235). Il
n'est localisé sur aucun numéro, n'est corroboré par aucune autre analyse et est compatible avec du
bruit d'échantillonnage. Il n'est pas retenu comme anomalie.

Un test exploratoire d'autocorrélation (non pré-enregistré) signale aussi 2 valeurs du complémentaire sur 49 après correction. Ces signaux ne sont pas confirmés et ne peuvent pas l'être sur les données déjà observées : seuls des tirages futurs, avec un test fixé à l'avance, permettraient de les confirmer ou de les écarter, mais l'effet observé est si petit qu'il faudrait de l'ordre de 2 400 tirages (une quinzaine d'années au rythme actuel) pour le détecter avec une puissance raisonnable.

## Suite possible (non exécutée)

Phases 11 à 14 : prédictions exploratoires figées (explicitement non validées), intégration des
nouveaux tirages, couche d'interprétation, boucle de recherche continue. Détail et réponses aux 10
questions du cahier des charges : FINAL.md.
