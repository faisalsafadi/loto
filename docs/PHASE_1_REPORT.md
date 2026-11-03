### Phase 1 — Import et contrôle des tirages
STATUT : NO-GO sur le critère de comptage ; écart accepté formellement par l'utilisateur le 2026-09-28. La Phase 2 peut démarrer sur confirmation explicite.

Ce qui a été testé : import du fichier source, SHA256, structure, comptage contre les 3 159 annoncés, cohérence numérotation / calendrier (diagnostic en lecture seule).
Méthode : scripts/phase1_import.py et scripts/phase1_diagnostic.py, exécutés par l'utilisateur. Aucune statistique sur les numéros tirés n'a été calculée.
Résultats (chiffres) :
- SHA256 eb5b5be17b050542b721cea1ad09e71ffc29b1dbfa92742647162c3d7eeb246b ; 204 474 octets.
- 3 155 lignes de données (attendu 3 159, écart -4) ; dates du 2001-03-17 au 2026-09-26, strictement décroissantes.
- 0 date dupliquée ; 0 ligne « 0 0 0 0 0 0 + 0 » ; 0 valeur hors [1,49].
- Environ 42 tirages numérotés mais absents (estimation par numérotation et calendrier) : dont 20 en janv.-févr. 2020, 7 en 2018, 5 en 2017, 4 en déc. 2012.
- 3 lignes datées du 31/12 (2004, 2006, 2012) probablement mal datées d'un an ; N dupliqués : 277 (2023), 100 (2024) ; cas ambigu en déc. 2009.
- Calendrier : 2 tirages par semaine jusqu'en 2014, 3 par semaine dès 2016 (lundis apparus en 2015).
- Trou du 2020-03-25 au 2020-06-06 sans trou de numérotation.
Interprétation : le fichier a été réparé par l'utilisateur avant import. Modifications déclarées : NON DOCUMENTÉES (l'utilisateur indique avoir « réparé » le fichier, l'essentiel étant la suite des numéros, sans détailler ; le texte précédent de cette ligne était un exemple de gabarit, pas une déclaration). Le RAW n'est donc pas un fichier original. L'écart de -4 est compatible avec la suppression des anomalies prévues au Cahier, ce qui n'est pas démontré.
Limitations : modifications antérieures à l'import non journalisées ; certaines erreurs (années des 31/12) pourraient venir de cette réparation ; les tirages absents ne sont pas reconstituables sans source officielle.
Explication alternative envisagée : le chiffre 3 159 provient d'une autre version du fichier, ou des lignes ont été perdues lors d'une récupération (feuille Récupéré_Feuil1).
Fichiers produits : data/raw/loteriema_20260928_original.xlsx (lecture seule), data/raw/MANIFEST.json, logs/run_phase1_*.json, scripts/phase1_*.py.
Décision : RAW = ce fichier tel qu'importé, sans aucune correction. Les anomalies sont signalées par des flags et traitées en Phase 2 avec journal de nettoyage (amendements A5 et A6).
