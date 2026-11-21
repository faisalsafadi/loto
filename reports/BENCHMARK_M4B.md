# BENCHMARK_M4B — extension POST_HOC : dépendance faible

Config de base (SHA256) : `fab83eee5ac8b19202d5f8b738fee2727af238cf91e240423d38d2ddce0f92f8` · Seed 42 · Commit : 916d4bd16f11bc3e0cad772c62cd991a1077ed84 · Date : 2026-10-31T11:04:51+00:00

Statut : **POST_HOC**. Les niveaux de rho (0,002 ; 0,005 ; 0,01) ont été choisis après avoir vu la saturation de M4. Les prédictions de la colonne « prédit » ont été écrites avant l'exécution (en tête de `scripts/m4b_run_benchmark.py`). Les lignes « M4 » viennent du lancement officiel de M4.

## 1. Puissance sous dépendance (CALCUL, DESCRIPTIVE)

### dependence — n = 500

| rho | source | prédit (recouvrement) | uniformity_global | per_number_holm | consecutive_overlap | half_homogeneity |
|---|---|---|---|---|---|---|
| 0.002 | M4b | 6.0 % | 7.0 % [4.2 %–11.4 %] | 4.0 % [2.0 %–7.7 %] | 10.0 % [6.6 %–14.9 %] | 5.0 % [2.7 %–9.0 %] |
| 0.005 | M4b | 10.0 % | 5.5 % [3.1 %–9.6 %] | 6.0 % [3.5 %–10.2 %] | 13.5 % [9.4 %–18.9 %] | 4.5 % [2.4 %–8.3 %] |
| 0.01 | M4b | 27.0 % | 8.0 % [5.0 %–12.6 %] | 3.0 % [1.4 %–6.4 %] | 20.0 % [15.0 %–26.1 %] | 6.0 % [3.5 %–10.2 %] |
| 0.02 | M4 | — | 6.5 % [3.8 %–10.8 %] | 3.5 % [1.7 %–7.0 %] | 76.5 % [70.2 %–81.8 %] | 5.0 % [2.7 %–9.0 %] |
| 0.05 | M4 | — | 11.0 % [7.4 %–16.1 %] | 7.5 % [4.6 %–12.0 %] | 100.0 % [98.1 %–100.0 %] | 13.5 % [9.4 %–18.9 %] |
| 0.1 | M4 | — | 29.0 % [23.2 %–35.6 %] | 10.5 % [7.0 %–15.5 %] | 100.0 % [98.1 %–100.0 %] | 21.0 % [15.9 %–27.2 %] |

### dependence — n = 3155

| rho | source | prédit (recouvrement) | uniformity_global | per_number_holm | consecutive_overlap | half_homogeneity |
|---|---|---|---|---|---|---|
| 0.002 | M4b | 10.0 % | 4.5 % [2.4 %–8.3 %] | 3.5 % [1.7 %–7.0 %] | 11.5 % [7.8 %–16.7 %] | 3.5 % [1.7 %–7.0 %] |
| 0.005 | M4b | 40.0 % | 4.5 % [2.4 %–8.3 %] | 6.0 % [3.5 %–10.2 %] | 40.0 % [33.5 %–46.9 %] | 6.5 % [3.8 %–10.8 %] |
| 0.01 | M4b | 93.0 % | 5.0 % [2.7 %–9.0 %] | 4.0 % [2.0 %–7.7 %] | 92.5 % [88.0 %–95.4 %] | 6.0 % [3.5 %–10.2 %] |
| 0.02 | M4 | — | 4.0 % [2.0 %–7.7 %] | 3.5 % [1.7 %–7.0 %] | 100.0 % [98.1 %–100.0 %] | 5.0 % [2.7 %–9.0 %] |
| 0.05 | M4 | — | 14.0 % [9.9 %–19.5 %] | 8.0 % [5.0 %–12.6 %] | 100.0 % [98.1 %–100.0 %] | 9.0 % [5.8 %–13.8 %] |
| 0.1 | M4 | — | 28.0 % [22.2 %–34.6 %] | 13.5 % [9.4 %–18.9 %] | 100.0 % [98.1 %–100.0 %] | 27.5 % [21.8 %–34.1 %] |

## 2. Biais minimal détectable à 80 % de puissance, test de recouvrement (CALCUL)

Interpolation linéaire entre niveaux testés (M4 + M4b combinés) : estimation grossière.

| n | rho minimal à 80 % |
|---|---|
| 500 | 0.0245 (interpolé) |
| 3155 | 0.00881 (interpolé) |

## 3. Limites (LIMITATION)

- Niveaux choisis après observation : POST_HOC, descriptif seulement.
- 200 répétitions par cellule : erreur type jusqu'à 3,5 points ; interpolation grossière.
- rho est la probabilité de reprise de chaque numéro du tirage précédent dans un modèle simple ; d'autres formes de dépendance ne sont pas couvertes.
- Le banc mesure la sensibilité du moteur, pas un pouvoir prédictif.
