# BENCHMARK_M4 — banc d'essai du moteur (faux positifs et puissance)

Configuration (SHA256) : `fab83eee5ac8b19202d5f8b738fee2727af238cf91e240423d38d2ddce0f92f8`  
Seed de base : 42 · Calibration : 100000 simulations par taille · Commit : 473503a96a3f60fd8ab81d2f990cc6163ed1ea6f · Date : 2026-10-31T10:49:14+00:00

Statut : CONFIRMATORY pour la section 1 (critère fixé avant exécution) ; la section 2 est DESCRIPTIVE (mesure de puissance sur biais choisis par nous).

## 1. Faux positifs sous H0 (OBSERVATION / CALCUL)

IC de Wilson ~99,4 % (correction pour 8 vérifications). Test à 2 côtés pour les trois tests calibrés ; pour per_number_holm, seul un taux libéral (> 5 %) est un échec, un taux conservateur est attendu.

| n | test | réps | rejets | taux | IC | verdict |
|---|---|---|---|---|---|---|
| 500 | uniformity_global | 1000 | 48 | 4.8 % | [3.3 % ; 7.0 %] | OK |
| 500 | per_number_holm | 1000 | 43 | 4.3 % | [2.9 % ; 6.4 %] | OK (non libéral) |
| 500 | consecutive_overlap | 1000 | 47 | 4.7 % | [3.2 % ; 6.9 %] | OK |
| 500 | half_homogeneity | 1000 | 58 | 5.8 % | [4.1 % ; 8.2 %] | OK |
| 500 | any_of_four | 1000 | 181 | 18.1 % | [15.0 % ; 21.7 %] | info |
| 3155 | uniformity_global | 1000 | 42 | 4.2 % | [2.8 % ; 6.3 %] | OK |
| 3155 | per_number_holm | 1000 | 57 | 5.7 % | [4.0 % ; 8.1 %] | OK (non libéral) |
| 3155 | consecutive_overlap | 1000 | 50 | 5.0 % | [3.4 % ; 7.2 %] | OK |
| 3155 | half_homogeneity | 1000 | 50 | 5.0 % | [3.4 % ; 7.2 %] | OK |
| 3155 | any_of_four | 1000 | 177 | 17.7 % | [14.6 % ; 21.2 %] | info |

Critère FPR global : **REMPLI**. Ligne any_of_four : information seulement (union de 4 tests, taux attendu supérieur à 5 %).

## 2. Puissance par scénario (CALCUL, DESCRIPTIVE)

Taux de rejet à alpha = 0,05 (Holm sur 49 pour per_number_holm), IC de Wilson 95 %. Niveaux : number = hausse relative ; pair = multiplicateur de la fréquence conjointe ; dependence = probabilité de reprise rho ; rupture = hausse relative sur la seconde moitié.

### number — n = 500

| niveau | uniformity_global | per_number_holm | consecutive_overlap | half_homogeneity | any_of_four |
|---|---|---|---|---|---|
| 0.1 | 3.0 % [1.4 %–6.4 %] | 3.0 % [1.4 %–6.4 %] | 4.0 % [2.0 %–7.7 %] | 5.0 % [2.7 %–9.0 %] | 13.5 % [9.4 %–18.9 %] |
| 0.2 | 10.0 % [6.6 %–14.9 %] | 8.0 % [5.0 %–12.6 %] | 4.0 % [2.0 %–7.7 %] | 6.5 % [3.8 %–10.8 %] | 23.5 % [18.2 %–29.8 %] |
| 0.3 | 16.0 % [11.6 %–21.7 %] | 21.5 % [16.4 %–27.7 %] | 5.5 % [3.1 %–9.6 %] | 4.5 % [2.4 %–8.3 %] | 36.5 % [30.1 %–43.4 %] |

### number — n = 3155

| niveau | uniformity_global | per_number_holm | consecutive_overlap | half_homogeneity | any_of_four |
|---|---|---|---|---|---|
| 0.1 | 13.0 % [9.0 %–18.4 %] | 16.5 % [12.0 %–22.3 %] | 7.0 % [4.2 %–11.4 %] | 2.5 % [1.1 %–5.7 %] | 31.0 % [25.0 %–37.7 %] |
| 0.2 | 40.5 % [33.9 %–47.4 %] | 75.5 % [69.1 %–80.9 %] | 4.5 % [2.4 %–8.3 %] | 3.5 % [1.7 %–7.0 %] | 79.0 % [72.8 %–84.1 %] |
| 0.3 | 90.5 % [85.6 %–93.8 %] | 99.5 % [97.2 %–99.9 %] | 5.0 % [2.7 %–9.0 %] | 4.5 % [2.4 %–8.3 %] | 100.0 % [98.1 %–100.0 %] |

### pair — n = 500

| niveau | uniformity_global | per_number_holm | consecutive_overlap | half_homogeneity | any_of_four |
|---|---|---|---|---|---|
| 1.5 | 5.5 % [3.1 %–9.6 %] | 4.5 % [2.4 %–8.3 %] | 3.0 % [1.4 %–6.4 %] | 6.5 % [3.8 %–10.8 %] | 17.0 % [12.4 %–22.8 %] |
| 2 | 7.0 % [4.2 %–11.4 %] | 4.0 % [2.0 %–7.7 %] | 4.0 % [2.0 %–7.7 %] | 4.5 % [2.4 %–8.3 %] | 16.5 % [12.0 %–22.3 %] |
| 3 | 13.0 % [9.0 %–18.4 %] | 12.0 % [8.2 %–17.2 %] | 5.5 % [3.1 %–9.6 %] | 5.0 % [2.7 %–9.0 %] | 29.0 % [23.2 %–35.6 %] |

### pair — n = 3155

| niveau | uniformity_global | per_number_holm | consecutive_overlap | half_homogeneity | any_of_four |
|---|---|---|---|---|---|
| 1.5 | 5.0 % [2.7 %–9.0 %] | 4.5 % [2.4 %–8.3 %] | 3.5 % [1.7 %–7.0 %] | 3.5 % [1.7 %–7.0 %] | 15.0 % [10.7 %–20.6 %] |
| 2 | 20.5 % [15.5 %–26.6 %] | 25.5 % [20.0 %–32.0 %] | 3.5 % [1.7 %–7.0 %] | 6.0 % [3.5 %–10.2 %] | 39.0 % [32.5 %–45.9 %] |
| 3 | 82.5 % [76.6 %–87.1 %] | 86.5 % [81.1 %–90.6 %] | 7.0 % [4.2 %–11.4 %] | 7.5 % [4.6 %–12.0 %] | 92.0 % [87.4 %–95.0 %] |

### dependence — n = 500

| niveau | uniformity_global | per_number_holm | consecutive_overlap | half_homogeneity | any_of_four |
|---|---|---|---|---|---|
| 0.02 | 6.5 % [3.8 %–10.8 %] | 3.5 % [1.7 %–7.0 %] | 76.5 % [70.2 %–81.8 %] | 5.0 % [2.7 %–9.0 %] | 79.0 % [72.8 %–84.1 %] |
| 0.05 | 11.0 % [7.4 %–16.1 %] | 7.5 % [4.6 %–12.0 %] | 100.0 % [98.1 %–100.0 %] | 13.5 % [9.4 %–18.9 %] | 100.0 % [98.1 %–100.0 %] |
| 0.1 | 29.0 % [23.2 %–35.6 %] | 10.5 % [7.0 %–15.5 %] | 100.0 % [98.1 %–100.0 %] | 21.0 % [15.9 %–27.2 %] | 100.0 % [98.1 %–100.0 %] |

### dependence — n = 3155

| niveau | uniformity_global | per_number_holm | consecutive_overlap | half_homogeneity | any_of_four |
|---|---|---|---|---|---|
| 0.02 | 4.0 % [2.0 %–7.7 %] | 3.5 % [1.7 %–7.0 %] | 100.0 % [98.1 %–100.0 %] | 5.0 % [2.7 %–9.0 %] | 100.0 % [98.1 %–100.0 %] |
| 0.05 | 14.0 % [9.9 %–19.5 %] | 8.0 % [5.0 %–12.6 %] | 100.0 % [98.1 %–100.0 %] | 9.0 % [5.8 %–13.8 %] | 100.0 % [98.1 %–100.0 %] |
| 0.1 | 28.0 % [22.2 %–34.6 %] | 13.5 % [9.4 %–18.9 %] | 100.0 % [98.1 %–100.0 %] | 27.5 % [21.8 %–34.1 %] | 100.0 % [98.1 %–100.0 %] |

### rupture — n = 500

| niveau | uniformity_global | per_number_holm | consecutive_overlap | half_homogeneity | any_of_four |
|---|---|---|---|---|---|
| 0.2 | 4.5 % [2.4 %–8.3 %] | 5.5 % [3.1 %–9.6 %] | 4.0 % [2.0 %–7.7 %] | 7.0 % [4.2 %–11.4 %] | 18.5 % [13.7 %–24.5 %] |
| 0.3 | 5.0 % [2.7 %–9.0 %] | 6.5 % [3.8 %–10.8 %] | 2.5 % [1.1 %–5.7 %] | 5.5 % [3.1 %–9.6 %] | 16.0 % [11.6 %–21.7 %] |

### rupture — n = 3155

| niveau | uniformity_global | per_number_holm | consecutive_overlap | half_homogeneity | any_of_four |
|---|---|---|---|---|---|
| 0.2 | 12.0 % [8.2 %–17.2 %] | 12.0 % [8.2 %–17.2 %] | 7.0 % [4.2 %–11.4 %] | 13.0 % [9.0 %–18.4 %] | 33.0 % [26.9 %–39.8 %] |
| 0.3 | 27.5 % [21.8 %–34.1 %] | 44.0 % [37.3 %–50.9 %] | 4.5 % [2.4 %–8.3 %] | 22.0 % [16.8 %–28.2 %] | 62.5 % [55.6 %–68.9 %] |

## 3. Biais minimal détectable à 80 % de puissance (CALCUL)

Interpolation linéaire entre niveaux testés (trois niveaux seulement : estimation grossière). « Non atteint » ou « <= plus bas niveau » signifie que les niveaux choisis ne permettent pas de conclure.

| scénario | n | test | biais minimal à 80 % |
|---|---|---|---|
| number | 500 | uniformity_global | > 0.3 (non atteint) |
| number | 500 | per_number_holm | > 0.3 (non atteint) |
| number | 500 | consecutive_overlap | > 0.3 (non atteint) |
| number | 500 | half_homogeneity | > 0.3 (non atteint) |
| number | 3155 | uniformity_global | 0.279 (interpolé) |
| number | 3155 | per_number_holm | 0.219 (interpolé) |
| number | 3155 | consecutive_overlap | > 0.3 (non atteint) |
| number | 3155 | half_homogeneity | > 0.3 (non atteint) |
| pair | 500 | uniformity_global | > 3.0 (non atteint) |
| pair | 500 | per_number_holm | > 3.0 (non atteint) |
| pair | 500 | consecutive_overlap | > 3.0 (non atteint) |
| pair | 500 | half_homogeneity | > 3.0 (non atteint) |
| pair | 3155 | uniformity_global | 2.96 (interpolé) |
| pair | 3155 | per_number_holm | 2.89 (interpolé) |
| pair | 3155 | consecutive_overlap | > 3.0 (non atteint) |
| pair | 3155 | half_homogeneity | > 3.0 (non atteint) |
| dependence | 500 | uniformity_global | > 0.1 (non atteint) |
| dependence | 500 | per_number_holm | > 0.1 (non atteint) |
| dependence | 500 | consecutive_overlap | 0.0245 (interpolé) |
| dependence | 500 | half_homogeneity | > 0.1 (non atteint) |
| dependence | 3155 | uniformity_global | > 0.1 (non atteint) |
| dependence | 3155 | per_number_holm | > 0.1 (non atteint) |
| dependence | 3155 | consecutive_overlap | 0.02 (<= plus bas niveau testé) |
| dependence | 3155 | half_homogeneity | > 0.1 (non atteint) |
| rupture | 500 | uniformity_global | > 0.3 (non atteint) |
| rupture | 500 | per_number_holm | > 0.3 (non atteint) |
| rupture | 500 | consecutive_overlap | > 0.3 (non atteint) |
| rupture | 500 | half_homogeneity | > 0.3 (non atteint) |
| rupture | 3155 | uniformity_global | > 0.3 (non atteint) |
| rupture | 3155 | per_number_holm | > 0.3 (non atteint) |
| rupture | 3155 | consecutive_overlap | > 0.3 (non atteint) |
| rupture | 3155 | half_homogeneity | > 0.3 (non atteint) |

## 4. Limites (LIMITATION)

- Seuls les biais injectés ici sont évalués : l'absence de détection d'un biais non simulé n'est pas mesurée.
- Aucun des 4 tests n'est spécifique aux paires : un biais de paire n'est vu que par l'effet marginal qu'il induit sur les deux numéros.
- Un niveau où la puissance atteint ~100 % (saturation) ne permet pas d'estimer le biais minimal.
- Puissance estimée sur 200 répétitions par cellule : erreur type jusqu'à 3,5 points.
- Calibration par Monte-Carlo : erreur de l'ordre de 1/sqrt(100 000) sur les p-values.
- Le banc mesure le moteur de détection, pas un pouvoir prédictif (Niveau D du Cahier).
