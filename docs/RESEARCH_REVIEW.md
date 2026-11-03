# RESEARCH_REVIEW.md

## LOTO MAROC Research Engine — Revue de littérature et de ressources

Version : 1.0
Statut : recherche préalable, antérieure à la Phase 0
Date : 2026-09-27
Objectif : recenser ce qui existe déjà — recherche académique, mathématiques/physique du hasard, cas documentés d'anomalies réelles, outils de test statistique de l'aléa, IA locales open-source, dépôts Git — avant d'écrire une seule ligne de code du projet.

Principe de lecture de ce document : chaque source est classée par fiabilité. Une bonne partie du contenu librement disponible sur "l'analyse de loterie" est du contenu marketing ou SEO de sites vendant des "systèmes gagnants" — ce document signale explicitement ces sources comme non fiables plutôt que de les citer comme faits.

---

## 1. Physique et mathématiques fondamentales du hasard mécanique

Le point de départ scientifique le plus solide n'est pas la loterie elle-même mais la physique des randomiseurs mécaniques en général.

### 1.1 Diaconis, Holmes & Montgomery — biais dynamique dans les systèmes mécaniques aléatoires

Le travail de référence est celui de Persi Diaconis (statisticien, Stanford), Susan Holmes et Richard Montgomery sur le lancer de pièce. Leur analyse montre qu'un objet soumis aux lois de la mécanique — donc en principe déterministe — peut néanmoins présenter un biais dynamique mesurable : une pièce lancée vigoureusement tend à retomber plus souvent du côté où elle a commencé, la probabilité limite dépendant d'un seul paramètre géométrique (l'angle entre la normale de la pièce et le vecteur moment angulaire). Le résultat central est que pour un lancer naturel, la probabilité de retomber comme au départ est d'environ 0,51 et non exactement 0,50.

Ce résultat est directement transposable au projet : il établit qu'un système physique conçu pour être aléatoire (pièce, dé, boules soufflées) n'est jamais *exactement* équiprobable en théorie — la question pertinente n'est donc pas "y a-t-il un biais physique en principe" (il y en a presque toujours un, infinitésimal), mais "ce biais est-il assez grand pour être détectable et exploitable avec l'échantillon dont on dispose". Les travaux ultérieurs (Vulović & Prange sur la pièce vraiment aléatoire, Strzałko et al. sur la prédictibilité de la dynamique du lancer, Yong sur le lancer de pièce épaisse) prolongent cette ligne : ces modèles plus complexes, incluant résistance de l'air et rebonds, confirment que le caractère aléatoire d'un lancer de pièce provient essentiellement du flux dynamique agissant sur l'incertitude des conditions initiales, pas d'une indétermination fondamentale.

**Application au projet** : cette littérature justifie scientifiquement pourquoi le Cahier des charges a raison de ne jamais présumer une équiprobabilité parfaite a priori, tout en exigeant qu'un écart soit démontré comme statistiquement significatif et robuste avant d'être interprété comme un biais exploitable (niveaux B/C du §2).

### 1.2 Machines à boules : gravité vs air soufflé

Deux familles de machines existent dans l'industrie des loteries : les machines à boules par gravité (tambour à palettes, boules en caoutchouc massif, utilisées par exemple pour Powerball/Mega Millions) et les machines à air soufflé (jets d'air calibrés, boules plus légères, utilisées pour les tirages plus rapides type keno/pick-3). Une source de vulgarisation technique (Grokipedia, à traiter avec prudence car il s'agit d'un wiki généré par IA et non d'une source primaire vérifiée) résume que pour garantir l'aléa, ces dispositifs utilisent des boules identiques calibrées en poids et en forme, sont soumis à des tests d'usine et sur site pour vérifier l'efficacité du brassage, et sont soumis à des audits indépendants vérifiant la distribution statistique avant mise en service. Le mécanisme décrit par l'utilisateur pour Loto Maroc (brassage par flux d'air dans une sphère transparente, extraction par aspiration) correspond à la famille "air-mix".

**Limite documentaire confirmée** : je n'ai trouvé aucune publication technique ou rapport d'audit public spécifique à la machine utilisée par la SGLN (fabricant, modèle, fréquence de certification, identité du tiers certificateur). Cette absence d'information physique vérifiable reste une limitation permanente du projet, déjà actée dans les échanges précédents.

---

## 2. Littérature académique sur les tests statistiques appliqués aux loteries

Il existe une littérature académique authentique et directement pertinente, distincte du contenu marketing.

### 2.1 Genest, Lockhart & Stephens (2002) — « χ² and the lottery »

Référence centrale, publiée dans *Journal of the Royal Statistical Society: Series D (The Statistician)*, vol. 51, p. 243-257. Cité comme référence méthodologique de fond dans les travaux ultérieurs sur l'audit statistique des loteries de type k/N. C'est l'article de référence pour l'usage correct (et les pièges) du test du χ² appliqué aux tirages de loterie.

### 2.2 Scalas et al. — audit statistique des loteries mexicaine et italienne

Ce travail (ScienceDirect / arXiv 0806.4595) présente les valeurs moyennes et covariances théoriques des variables aléatoires représentant les numéros tirés dans ce type de jeu, dans le but d'auditer statistiquement la cohérence d'un échantillon de résultats historiques avec les valeurs théoriques issues d'un modèle hypergéométrique. Point méthodologique important qu'il souligne explicitement : il est rigoureusement impossible de « prouver » l'aléa d'une séquence de nombres ; on peut seulement tester statistiquement si les résultats historiques présentent les propriétés quantitatives dérivées du modèle probabiliste supposé. Un résultat empirique notable rapporté dans une version de ce travail (référencé dans un résumé associé) indique que, pour une des séries testées, sur la période 1984-1993 les données n'étaient pas compatibles avec l'hypothèse d'équité du tirage — un exemple concret qu'une anomalie statistique robuste *a déjà été détectée* dans une loterie réelle par le passé, ce qui légitime la démarche du projet sans présumer du résultat pour Loto Maroc.

### 2.3 Bayesian Analysis of Lottery Randomness (UK National Lottery)

Ce travail propose une alternative bayésienne aux tests fréquentistes classiques. Il note que la littérature publiée sur l'analyse de l'aléa des loteries a presque exclusivement utilisé des méthodes fréquentistes sous forme de tests d'adéquation, et que cette approche, bien qu'elle atteigne généralement son objectif, souffre de problèmes d'interprétation, de taille et de puissance arbitraires, et de multiplicité des tests. Les auteurs appliquent leur méthode aux 1 101 premiers tirages du jeu principal de la loterie nationale britannique. Ce point renforce directement l'exigence du Cahier des charges (§13) de traiter rigoureusement les comparaisons multiples, et suggère qu'une extension bayésienne pourrait être envisagée en complément des tests fréquentistes prévus, sans remplacer le protocole déjà défini.

### 2.4 Hernandez et al. (WSEAS 2005) — tests de hasard, ARIMA et réseaux de neurones

Étude testant l'aléa de trois loteries (dont une loterie de Floride et la loterie vénézuélienne Zulia) via le test du χ² d'adéquation, le χ² de Pearson en tableau de contingence, le test des intervalles et le test de longueur des suites. Résultat rapporté : dans la loterie Zulia, les chiffres 7 et 9 apparaissaient en deuxième position 4 % de plus que l'attendu, rejetant l'hypothèse nulle au test du χ² d'adéquation, avec une statistique de test plus proche de la zone de rejet dans les loteries vénézuélienne et américaine testées, mais sans preuve de non-aléa dans les autres cas. C'est un exemple utile de résultat mitigé et localisé, cohérent avec ce que le projet doit s'attendre à trouver le plus souvent : quelques écarts isolés, sans qu'ils survivent nécessairement à une correction multiple rigoureuse.

### 2.5 Structure et rupture de régime — UK Lotto 49→59 boules

Une étude sur les tickets de loterie britannique souligne l'importance de segmenter l'historique lorsque les règles du jeu changent : les données ont dû être regroupées en deux périodes distinctes en raison du passage du nombre de numéros du Lotto de 49 à 59. C'est une confirmation académique directe de la nécessité, déjà prévue au §18 du Cahier des charges, de vérifier si Loto Maroc a changé de format sur ses ~25 ans d'historique avant toute analyse agrégée.

### 2.6 Biais humain vs biais machine — « Trying To Be Random in Selecting Numbers for Lotto »

Article pédagogique (*Journal of Statistics Education*) qui distingue explicitement l'aléa produit par une machine de celui que les humains croient produire en choisissant "au hasard" leurs propres numéros. Il est bâti sur la définition standard du jeu : dans un jeu de loto n/N, les n numéros gagnants sont sélectionnés sans remise, de manière aléatoire, généralement à l'aide d'un dispositif mécanique soigneusement fabriqué. Utile pour ne pas confondre, dans les futurs rapports du projet, un biais des *joueurs* (utile pour comprendre la répartition des mises, hors-sujet ici) avec un biais du *système de tirage* (seul objet du projet).

---

## 3. Économie comportementale : gambler's fallacy et hot-hand dans les loteries

Cette littérature ne porte pas sur le tirage physique mais sur le comportement des joueurs — elle est pertinente uniquement pour éviter que le projet ne reproduise, côté analyse, les mêmes biais cognitifs que ceux étudiés côté joueurs.

### 3.1 Clotfelter & Cook (1993) — l'article fondateur

Publié dans *Management Science* (vol. 39, n°12, p. 1521-1525), c'est la référence historique sur le sophisme du joueur appliqué à la loterie. Le sophisme du joueur est la croyance que la probabilité d'un événement diminue lorsque cet événement vient de se produire, alors que la probabilité est objectivement connue comme indépendante d'un tirage à l'autre. En étudiant le jeu quotidien du Maryland, les auteurs trouvent une tendance claire et constante : le montant misé sur un numéro donné chute fortement immédiatement après son tirage, puis remonte progressivement à son niveau antérieur sur plusieurs mois.

### 3.2 Kong, Granic, Lambert & Teo (2019) — l'effet inverse (hot-hand)

Publié dans *Management Science*, ce travail montre que les marchés de loterie peuvent aussi présenter le phénomène inverse du « hot-hand », où les numéros gagnants récents reçoivent une part accrue des mises dans les tirages futurs, alors même que les événements passés et futurs sont indépendants. Les auteurs notent que le sophisme du joueur prévaut généralement lorsque les nombres aléatoires sont générés par des dispositifs mécaniques comme les jeux de loterie, tandis que le hot-hand apparaît davantage dans des jeux à prix multiples.

**Pertinence directe pour ce projet** : ces deux résultats confirment un point déjà noté dans `HYPOTHESES.md` (H004) — un écart de fréquence de mise des joueurs ne dit strictement rien sur la probabilité réelle du tirage suivant. Le projet doit continuer à traiter ces deux notions comme complètement séparées.

---

## 4. Cas documentés de biais ou de fraude réels — et sources à écarter

### 4.1 Cas réels bien établis

- **Pennsylvania « Triple Six Fix » (1980)** : cas de fraude authentique où des boules lestées garantissaient que seuls les chiffres 4 et 6 pouvaient être tirés, découvert grâce à des anomalies de paris — des initiés avaient misé massivement sur le 666 —, combinées à une investigation mécanique.
- **Hot Lotto RNG Fraud (2010, affaire Eddie Tipton)** : un initié avait programmé le générateur de nombres aléatoires pour produire des résultats prévisibles à des dates précises, détecté par l'analyse des pistes d'audit et des schémas d'achat de tickets suspects sur plusieurs tirages. Un point méthodologique crucial rapporté ailleurs : la fraude Tipton n'a pas été détectée par les contrôles de sortie — les résultats semblaient normaux tout au long de la période de manipulation. C'était une fraude logicielle (RNG informatique), pas mécanique — elle ne s'applique pas directement à Loto Maroc (machine physique à air soufflé), mais elle illustre qu'une anomalie peut être invisible aux tests statistiques classiques si la manipulation est suffisamment fine et intermittente.
- **Loterie israélienne, répétition de combinaison (Hod HaSharon, ~2010)** : cas réel largement documenté où deux tirages ont produit la même combinaison à quelques semaines d'intervalle, événement estimé par un statisticien de l'université de Tel-Aviv comme devant se produire statistiquement une fois tous les 10 000 ans compte tenu de deux tirages par semaine. Ce cas est intéressant car il illustre un phénomène statistiquement rarissime qui n'a *pas* été retenu comme preuve de fraude — c'est l'exemple même de la distinction que le projet doit maintenir entre anomalie extrêmement improbable et fraude prouvée (§37 du Cahier des charges).

### 4.2 Sources à traiter avec une prudence extrême, voire à écarter

Plusieurs pages trouvées en ligne sur "l'analyse mécanique des loteries" présentent des statistiques très précises (pourcentages de perte de poids de boules, taux de "dérive mécanique", décroissance d'entropie) qui ont toutes les caractéristiques de contenu généré pour le référencement (SEO) plutôt que de résultats vérifiables : absence d'auteur identifiable, absence de méthodologie publiée, absence de source primaire citée, chiffres invraisemblablement précis. C'est notamment le cas de contenus affirmant qu'un lot de boules 2018 montrerait *"une perte de poids moyenne de 0,3 % corrélée parfaitement à leur fréquence de tirage accrue"* ou qu'une analyse de 10 000 tirages nord-américains aurait trouvé un pourcentage donné de tirages en "dérive mécanique". **Aucune de ces affirmations n'est reprise dans ce document comme fait établi.** Elles sont signalées ici uniquement pour que l'équipe du projet sache les reconnaître et ne les utilise jamais comme référence, même informelle — c'est exactement le type de source qui, si elle était citée par erreur dans un rapport `ANOMALY_REPORT.md`, discréditerait toute la démarche scientifique du projet.

De la même façon, les nombreux sites de "pronostics loto" affichant des numéros "chauds/froids" ne sont jamais des sources scientifiques et ne doivent jamais être cités, même à titre d'inspiration méthodologique — le §11 du Cahier des charges l'interdit déjà explicitement.

---

## 5. Absence de littérature académique spécifique à Loto Maroc

Recherche infructueuse : aucune étude académique, aucun article de statistique appliquée, aucun audit public spécifiquement consacré au Loto Maroc (SGLN) n'a été trouvé. Les seules sources disponibles sont journalistiques et institutionnelles : historique du jeu 6/49 lancé en 1978 par la Loterie Nationale, description générale du mécanisme de tirage par tambour et tube transparent avec capteur optique, mention d'audits et de contrôles techniques périodiques sans détail public, et présence d'une commission de contrôle pluri-institutionnelle à chaque tirage.

**Conséquence méthodologique** : ce projet serait, à notre connaissance, la première analyse statistique indépendante et systématique de l'historique du Loto Maroc. C'est à la fois une opportunité (aucun résultat préexistant à confirmer ou infirmer, aucun biais de confirmation possible envers une étude antérieure) et une responsabilité supplémentaire de rigueur, puisqu'il n'existe aucune littérature de comparaison directe pour valider les ordres de grandeur des résultats obtenus — la comparaison se fera donc principalement avec les résultats obtenus sur d'autres loteries 6/49 dans le monde (UK, Mexique, Italie, etc., cf. section 2).

---

## 6. Outils et méthodologies de test statistique de l'aléa

Au-delà des tests déjà listés dans `IMPLEMENTATION_SPEC.md` (χ², Bonferroni/Holm/FDR, Monte-Carlo), il existe des batteries de tests de l'aléa standardisées, historiquement conçues pour les générateurs de nombres pseudo-aléatoires informatiques (RNG), mais dont certains tests individuels sont transposables conceptuellement à une séquence de tirages :

- **NIST SP 800-22** : suite de référence développée par le National Institute of Standards and Technology, comportant 15 tests, réputée exigeante et relativement coûteuse en calcul. Comprend notamment le test de fréquence (monobit), le test des runs, le test de rang de matrice, et le test des excursions aléatoires.
- **Dieharder** : suite développée à partir des tests Diehard originaux de George Marsaglia, incorporant également les tests de la suite STS du NIST, comportant environ une trentaine de tests.
- **ENT / StringENT** : ENT est une suite de cinq tests simples et rapides, dont un seul produit une p-value formelle ; StringENT est une extension académique récente qui corrige cette limite en fournissant des p-values pour l'ensemble de la batterie.
- **TestU01** : traite la séquence comme une collection de nombres flottants dans [0,1) et comprend trois ensembles de tests (10, 96 et 100 tests respectivement).

**Applicabilité réelle et limite** : ces suites sont conçues pour des flux binaires ou des séquences de très grande taille (≥10⁶ valeurs), très supérieure aux ~3 000 tirages disponibles pour Loto Maroc. Elles ne remplacent donc pas les tests spécifiques déjà prévus (χ², gaps, paires, Monte-Carlo) mais peuvent inspirer des tests complémentaires légers (test des runs, test de rang) si le volume de données le permet, en gardant à l'esprit que leur puissance statistique sera limitée par la taille d'échantillon.

Un dépôt personnel trouvé sur GitHub (`baychimo/loto`, archivé) confirme cette piste en pratique : le projet utilise les outils dieharder et ENT pour exécuter ses statistiques sur des numéros de loterie, et son auteur précise honnêtement que le système n'a fait aucune prédiction correcte à ce jour, ce qui ne devrait surprendre personne — un exemple de transparence scientifique rare dans ce domaine, à saluer et à prendre en modèle.

---

## 7. Détection de rupture (change-point detection)

Le §19 du Cahier des charges et le §28 de `IMPLEMENTATION_SPEC.md` prévoient CUSUM, Bayesian change-point, et la bibliothèque `ruptures`. Confirmation :

**ruptures** (Truong, Oudre, Vayatis — Centre Borelli / CNRS) est une bibliothèque Python pour la détection de ruptures hors-ligne, fournissant des méthodes pour l'analyse et la segmentation de signaux non stationnaires, avec des algorithmes de détection exacte et approchée pour divers modèles paramétriques et non-paramétriques. Elle est téléchargée plus de 12 millions de fois et citée dans plus de 250 publications académiques, ce qui en fait un choix mûr et bien maintenu — confirmation que le choix technique du Cahier des charges est le bon. Installation directe : `pip install ruptures`.

Pour la détection bayésienne de rupture mentionnée au §19 (Bayesian change-point), la référence académique standard du domaine (connaissance générale, non vérifiée par recherche pour cette revue) est l'algorithme de détection en ligne bayésienne de rupture ; il conviendra de le confirmer et le documenter précisément au moment de son implémentation en Phase 5/11, plutôt que de l'affirmer ici sans vérification supplémentaire.

---

## 8. IA locale / modèles open-source candidats pour la couche d'interprétation (§24 Cahier des charges, §43-44 IMPLEMENTATION_SPEC)

Le rôle de cette couche est strictement interprétatif (formuler des hypothèses, comparer des rapports, rédiger de la documentation) — elle ne doit jamais produire de résultat numérique primaire. Le choix du modèle est donc secondaire par rapport au moteur statistique, mais voici l'état du marché des modèles ouverts pertinents pour un déploiement local, à valider et re-vérifier au moment de l'implémentation réelle (Phase 13) car ce secteur évolue vite :

| Modèle | Paramètres | Licence | Point fort rapporté | VRAM indicative (Q4) |
|---|---|---|---|---|
| Qwen 3 235B-A22B | 235B (22B actifs) | Apache 2.0 | Raisonnement général + code | ~132 Go |
| DeepSeek R1 | 671B (37B actifs) | MIT | Raisonnement mathématique profond | ~136 Go |
| Llama 4 Scout | 109B (17B actifs) | Llama License | Contexte très long (10M tokens) | ~55 Go |
| Mistral Small 3.1 | 24B | Apache 2.0 | Workflows agentiques, un seul GPU | ~14-16 Go |
| Gemma 3 27B | 27B | Gemma Terms | GPU unique grand public | ~16 Go |
| Phi-4 Reasoning | 14B | MIT | Edge / matériel modeste | ~8 Go |

Source de ce tableau : comparatif de benchmarks publics (MMLU, HumanEval) mis à jour en juillet 2026. **Réserve méthodologique** : il s'agit d'un site de blog/comparatif, pas d'une publication scientifique évaluée par les pairs — les chiffres doivent être considérés comme indicatifs et re-vérifiés auprès des pages officielles des modèles (Hugging Face, cartes de modèle) avant toute décision finale.

**Recommandation pour ce projet** (compte tenu que la tâche est de l'interprétation de rapports statistiques déjà calculés, pas de la génération de code complexe) : un modèle de taille modeste et facilement auto-hébergeable (Mistral Small 3.1 ou Gemma 3 27B) est probablement suffisant et plus simple à opérer que les modèles de plusieurs centaines de milliards de paramètres, dont l'apport pour cette tâche spécifique (résumer et interroger des rapports déjà produits par le moteur statistique) serait probablement marginal. Ce choix reste à confirmer en Phase 13, une fois les rapports réels disponibles pour évaluer le besoin.

---

## 9. Dépôts Git pertinents

| Dépôt | Nature | Intérêt pour le projet |
|---|---|---|
| `deepcharles/ruptures` | Bibliothèque officielle, maintenue | Détection de rupture — usage direct prévu (§19 Cahier des charges) |
| `baychimo/loto` (archivé) | Projet personnel | Utilise dieharder/ENT sur des données de loterie ; transparence exemplaire sur l'échec prédictif |
| `knightinfected/backtester` | Simulation de backtesting loterie (Cash 3, Géorgie) | Simule rétroactivement la précision de différents modèles prédictifs en parcourant les données jour par jour, en ne générant des prédictions qu'à partir des données passées disponibles à ce moment — architecture walk-forward très proche de celle exigée au §26 du Cahier des charges et à la Phase 10 du plan d'exécution. Utile comme référence de structure, pas comme source de résultats. |
| `heheshang/ai_lottory_python` | Projet avec contraintes éthiques explicites | Impose un plafond de confiance à 85 %, une messagerie obligatoire de jeu responsable, et une validation statistique avec plus de 90 % de couverture de tests — un parallèle intéressant avec l'exigence de transparence et de non-surinterprétation du projet, même si son approche prédictive reste à prendre avec la même prudence que toute autre tentative de ce type. |
| `yangboz/LotteryPrediction` | Projet ancien, largement suivi (291 étoiles) | Rappelle explicitement dans sa documentation que le sophisme du joueur existe en plus des lois de probabilité classiques et qu'il ne garantit à personne de réaliser un rêve d'enrichissement — utile comme rappel de bonne pratique de communication, à reproduire dans nos propres rapports finaux. |
| `hrparty/lotteryAnalyzer` | Projet minimal | Peu de documentation disponible ; intérêt limité, mentionné pour exhaustivité. |

**Bibliothèques scientifiques déjà retenues dans `IMPLEMENTATION_SPEC.md`** (pandas, numpy, scipy, statsmodels, scikit-learn, XGBoost, LightGBM, pyarrow, pytest) sont confirmées comme le socle standard de l'écosystème data science Python — aucun changement recommandé à ce stade.

---

## 10. Synthèse et implications pour la suite du projet

1. **Le design du projet est scientifiquement aligné avec l'état de l'art académique** sur l'audit statistique des loteries (Genest/Lockhart/Stephens, Scalas et al., approche bayésienne alternative) — aucune lacune méthodologique majeure identifiée par rapport à cette littérature.
2. **La physique du hasard mécanique (Diaconis et al.) confirme** qu'un biais physique infinitésimal existe presque toujours en théorie dans tout système mécanique — ce qui renforce, plutôt qu'affaiblit, l'exigence du projet de ne jamais interpréter un écart brut comme une preuve sans validation hors-échantillon robuste.
3. **Aucune étude académique n'existe sur Loto Maroc spécifiquement** — le projet est probablement inédit sur ce terrain précis, ce qui augmente la responsabilité de rigueur et interdit toute comparaison directe de résultats.
4. **Des cas réels de fraude et de biais mécanique existent** (Pennsylvanie 1980, Tipton 2010) mais concernent des configurations très différentes (fraude interne délibérée, RNG logiciel) — ils justifient la vigilance méthodologique sans présumer d'une situation comparable ici.
5. **Une grande partie du contenu en ligne sur ce sujet est du contenu SEO non fiable** — ce document a identifié et écarté explicitement ces sources pour qu'elles ne contaminent jamais, même par inadvertance, un futur rapport du projet.
6. **Les outils techniques prévus (ruptures, scipy, statsmodels, Monte-Carlo) sont corroborés par l'usage académique et industriel réel** — aucun changement d'architecture technique recommandé.
7. **Le choix de l'IA locale reste ouvert et secondaire** — à trancher en Phase 13 sur la base du besoin réel (interprétation de rapports déjà produits), pas en amont.

Cette revue ne modifie aucune hypothèse déjà enregistrée dans `HYPOTHESES.md` — elle les renforce méthodologiquement. Aucune hypothèse nouvelle n'est ajoutée à ce stade : toute idée issue de cette revue qui mériterait de devenir une hypothèse testable devra être ajoutée à `HYPOTHESES.md` explicitement, datée, et non marquée comme confirmatoire par défaut.

---

## Références principales citées

- Diaconis, P., Holmes, S., Montgomery, R. (2007). *Dynamical Bias in the Coin Toss*. SIAM Review, 49(2), 211-235.
- Genest, C., Lockhart, R.A., Stephens, M.A. (2002). *χ² and the lottery*. Journal of the Royal Statistical Society: Series D (The Statistician), 51, 243-257.
- Scalas, E. et al. *Statistical auditing and randomness test of lotto k/N-type games*. ScienceDirect / arXiv:0806.4595.
- Clotfelter, C.T., Cook, P.J. (1993). *Notes: The "Gambler's Fallacy" in Lottery Play*. Management Science, 39(12), 1521-1525.
- Kong, L., Granic, G., Lambert, N., Teo, C. (2019). *Judgment Error in Lottery Play: When the Hot-Hand Meets the Gambler's Fallacy*. Management Science, 66(2), 844-862.
- Truong, C., Oudre, L., Vayatis, N. (2020). *Selective review of offline change point detection methods*. Signal Processing, 167, 107299.
- Hernandez, A.A.G. et al. (2005). *Analysis of the results of lotteries using statistical methods and artificial neural networks*. WSEAS Int. Conf. on Neural Networks, Lisbonne.
- GitHub : deepcharles/ruptures ; baychimo/loto ; knightinfected/backtester ; heheshang/ai_lottory_python ; yangboz/LotteryPrediction.

*Document additif — à mettre à jour si de nouvelles sources pertinentes sont identifiées en cours de projet, avec date d'ajout.*
