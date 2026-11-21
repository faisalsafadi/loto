"""Banc d'essai M4 : taux de faux positifs sous H0 et puissance sous biais connus.

Méthode : la loi nulle de chaque statistique non exacte (uniformité globale, recouvrement consécutif,
homogénéité entre moitiés) est calibrée UNE FOIS par taille n par Monte-Carlo (tirage sans remise
réel), puis réutilisée pour toutes les répétitions. Le test par numéro utilise la loi binomiale
exacte (marginale de chaque numéro) et Holm sur 49 tests : rejet <=> p minimale <= alpha / 49.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.stats import binom, norm

from loto_research.simulation import bench_config as cfg
from loto_research.simulation.generators import gen_null, generate

ANY = "any_of_four"
Z_FPR = float(norm.ppf(1 - cfg.ALPHA / 16))   # 8 vérifications de FPR (4 tests x 2 tailles) : IC ~99,4 %
Z_POWER = 1.96


def cell_rng(scenario, level, n):
    label = f"{scenario}|{float(level):.6f}|{int(n)}"
    h = int.from_bytes(hashlib.sha256(label.encode("utf-8")).digest()[:8], "big")
    return np.random.default_rng(np.random.SeedSequence([cfg.BASE_SEED, h]))


def stats_from_presence(x):
    """Statistiques de test, vectorisées sur les répétitions. x : bool (reps, n, 49)."""
    reps, n, _ = x.shape
    counts = x.sum(axis=1)
    expected = n * cfg.K / cfg.N_MAX
    chi2 = ((counts - expected) ** 2 / expected).sum(axis=1)
    overlap = (x[:, 1:] & x[:, :-1]).sum(axis=(1, 2)) / (n - 1)
    n1 = n // 2
    n2 = n - n1
    a = x[:, :n1].sum(axis=1)
    b = x[:, n1:].sum(axis=1)
    c = a + b
    e1 = n1 * c / n
    e2 = n2 * c / n
    safe1 = np.where(e1 > 0, e1, 1.0)
    safe2 = np.where(e2 > 0, e2, 1.0)
    homog = (((a - e1) ** 2) / safe1 + ((b - e2) ** 2) / safe2).sum(axis=1)
    return {"counts": counts, "chi2": chi2, "overlap": overlap, "homog": homog}


def per_number_min_p(counts, n):
    """p minimale parmi les 49 numéros (binomiale exacte, double queue doublée)."""
    p = cfg.K / cfg.N_MAX
    lo = binom.cdf(counts, n, p)
    hi = binom.sf(counts - 1, n, p)
    pv = np.minimum(1.0, 2.0 * np.minimum(lo, hi))
    return pv.min(axis=1)


def p_upper(sorted_null, obs):
    n_null = len(sorted_null)
    ge = n_null - np.searchsorted(sorted_null, obs, side="left")
    return (1.0 + ge) / (n_null + 1.0)


def p_two_sided(sorted_null, obs):
    n_null = len(sorted_null)
    le = np.searchsorted(sorted_null, obs, side="right")
    ge = n_null - np.searchsorted(sorted_null, obs, side="left")
    return np.minimum(1.0, 2.0 * np.minimum((1.0 + le) / (n_null + 1.0), (1.0 + ge) / (n_null + 1.0)))


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2.0 * n)) / denom
    half = z * np.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n)) / denom
    return (float(max(0.0, centre - half)), float(min(1.0, centre + half)))


def calibrate(n, n_sim, cache_dir=None, chunk=cfg.CAL_CHUNK_REPS, progress=None):
    """Lois nulles (triées) des trois statistiques calibrées, pour une taille n."""
    path = None
    if cache_dir is not None:
        path = Path(cache_dir) / f"bench_cal_n{n}_sim{n_sim}_{cfg.config_hash()[:12]}.npz"
        if path.exists():
            z = np.load(path)
            return {k: z[k] for k in ("chi2", "overlap", "homog")}
    rng = cell_rng("calibration", 0.0, n)
    out = {"chi2": [], "overlap": [], "homog": []}
    done = 0
    while done < n_sim:
        c = min(chunk, n_sim - done)
        s = stats_from_presence(gen_null(rng, c, n))
        for k in out:
            out[k].append(s[k])
        done += c
        if progress is not None:
            progress(done, n_sim)
    res = {k: np.sort(np.concatenate(v)) for k, v in out.items()}
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(path, **res)
    return res


def run_cell(scenario, level, n, reps, cal, alpha=cfg.ALPHA, chunk=cfg.CHUNK_REPS):
    """Une cellule (scénario, niveau, taille) : taux de rejet de chaque test, avec IC de Wilson."""
    rng = cell_rng(scenario, level, n)
    rej = {t: 0 for t in cfg.TESTS}
    any_rej = 0
    done = 0
    while done < reps:
        c = min(chunk, reps - done)
        x = generate(scenario, level, rng, c, n)
        s = stats_from_presence(x)
        flags = {
            "uniformity_global": p_upper(cal["chi2"], s["chi2"]) <= alpha,
            "per_number_holm": per_number_min_p(s["counts"], n) <= alpha / cfg.N_MAX,
            "consecutive_overlap": p_two_sided(cal["overlap"], s["overlap"]) <= alpha,
            "half_homogeneity": p_upper(cal["homog"], s["homog"]) <= alpha,
        }
        any_flag = np.zeros(c, dtype=bool)
        for t, f in flags.items():
            rej[t] += int(f.sum())
            any_flag |= f
        any_rej += int(any_flag.sum())
        done += c
    z = Z_FPR if scenario == "null" else Z_POWER
    rows = []
    for t in list(cfg.TESTS) + [ANY]:
        k = any_rej if t == ANY else rej[t]
        lo, hi = wilson(k, reps, z)
        rows.append({"n": int(n), "scenario": scenario, "level": float(level), "reps": int(reps),
                     "test": t, "rejections": int(k), "rate": k / reps, "ci_low": lo, "ci_high": hi})
    return rows


def min_detectable(levels, rates, target=cfg.POWER_TARGET):
    """Niveau minimal atteignant `target` de puissance (interpolation linéaire entre niveaux testés).
    Renvoie (valeur ou None, remarque)."""
    pairs = sorted(zip(levels, rates))
    lv = [p[0] for p in pairs]
    rt = [p[1] for p in pairs]
    if rt[0] >= target:
        return lv[0], "<= plus bas niveau testé"
    for i in range(1, len(lv)):
        if rt[i] >= target:
            val = lv[i - 1] + (target - rt[i - 1]) * (lv[i] - lv[i - 1]) / (rt[i] - rt[i - 1])
            return val, "interpolé"
    return None, f"> {lv[-1]} (non atteint)"


def fpr_check(row):
    t = row["test"]
    if t == ANY:
        return "info"
    if t == "per_number_holm":
        return "OK (non libéral)" if row["ci_low"] <= cfg.ALPHA else "ÉCHEC (libéral)"
    return "OK" if row["ci_low"] <= cfg.ALPHA <= row["ci_high"] else "ÉCHEC"


def fpr_all_ok(rows):
    nulls = [r for r in rows if r["scenario"] == "null"]
    return bool(nulls) and all(not fpr_check(r).startswith("ÉCHEC") for r in nulls)


def ensure_tables(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS simulated_runs (
            id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, seed INTEGER NOT NULL,
            model TEXT NOT NULL, config_hash TEXT NOT NULL, params_json TEXT NOT NULL, git_commit TEXT);
        CREATE TABLE IF NOT EXISTS bench_cells (
            id INTEGER PRIMARY KEY, run_id INTEGER NOT NULL REFERENCES simulated_runs(id),
            n INTEGER NOT NULL, scenario TEXT NOT NULL, level REAL NOT NULL, test TEXT NOT NULL,
            reps INTEGER NOT NULL, rejections INTEGER NOT NULL, rate REAL NOT NULL,
            ci_low REAL NOT NULL, ci_high REAL NOT NULL);
        CREATE TRIGGER IF NOT EXISTS simulated_runs_no_update BEFORE UPDATE ON simulated_runs
            BEGIN SELECT RAISE(ABORT, 'simulated_runs is append-only'); END;
        CREATE TRIGGER IF NOT EXISTS simulated_runs_no_delete BEFORE DELETE ON simulated_runs
            BEGIN SELECT RAISE(ABORT, 'simulated_runs is append-only'); END;
        CREATE TRIGGER IF NOT EXISTS bench_cells_no_update BEFORE UPDATE ON bench_cells
            BEGIN SELECT RAISE(ABORT, 'bench_cells is append-only'); END;
        CREATE TRIGGER IF NOT EXISTS bench_cells_no_delete BEFORE DELETE ON bench_cells
            BEGIN SELECT RAISE(ABORT, 'bench_cells is append-only'); END;
        """
    )


def store_run(conn, seed, model, config_hash, params, rows, git_commit=None):
    ensure_tables(conn)
    cur = conn.execute(
        "INSERT INTO simulated_runs (created_at, seed, model, config_hash, params_json, git_commit) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (datetime.now(timezone.utc).isoformat(), int(seed), model, config_hash,
         json.dumps(params, sort_keys=True), git_commit))
    run_id = cur.lastrowid
    conn.executemany(
        "INSERT INTO bench_cells (run_id, n, scenario, level, test, reps, rejections, rate, ci_low, ci_high) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [(run_id, r["n"], r["scenario"], r["level"], r["test"], r["reps"], r["rejections"],
          r["rate"], r["ci_low"], r["ci_high"]) for r in rows])
    conn.commit()
    return run_id


def _pct(x):
    return f"{100 * x:.1f} %"


def build_report(rows, meta):
    sizes = sorted({r["n"] for r in rows})
    scenarios = [s for s in ("number", "pair", "dependence", "rupture") if any(r["scenario"] == s for r in rows)]
    L = []
    L.append("# BENCHMARK_M4 — banc d'essai du moteur (faux positifs et puissance)\n")
    L.append(f"Configuration (SHA256) : `{meta.get('config_hash', '?')}`  ")
    L.append(f"Seed de base : {cfg.BASE_SEED} · Calibration : {meta.get('n_calibration', '?')} simulations par taille · "
             f"Commit : {meta.get('git_commit', '?')} · Date : {meta.get('created_at', '?')}\n")
    L.append("Statut : CONFIRMATORY pour la section 1 (critère fixé avant exécution) ; la section 2 est "
             "DESCRIPTIVE (mesure de puissance sur biais choisis par nous).\n")

    L.append("## 1. Faux positifs sous H0 (OBSERVATION / CALCUL)\n")
    L.append("IC de Wilson ~99,4 % (correction pour 8 vérifications). Test à 2 côtés pour les trois tests "
             "calibrés ; pour per_number_holm, seul un taux libéral (> 5 %) est un échec, un taux conservateur est attendu.\n")
    L.append("| n | test | réps | rejets | taux | IC | verdict |")
    L.append("|---|---|---|---|---|---|---|")
    for r in [r for r in rows if r["scenario"] == "null"]:
        L.append(f"| {r['n']} | {r['test']} | {r['reps']} | {r['rejections']} | {_pct(r['rate'])} | "
                 f"[{_pct(r['ci_low'])} ; {_pct(r['ci_high'])}] | {fpr_check(r)} |")
    L.append(f"\nCritère FPR global : **{'REMPLI' if fpr_all_ok(rows) else 'NON REMPLI'}**. "
             "Ligne any_of_four : information seulement (union de 4 tests, taux attendu supérieur à 5 %).\n")

    L.append("## 2. Puissance par scénario (CALCUL, DESCRIPTIVE)\n")
    L.append("Taux de rejet à alpha = 0,05 (Holm sur 49 pour per_number_holm), IC de Wilson 95 %. "
             "Niveaux : number = hausse relative ; pair = multiplicateur de la fréquence conjointe ; "
             "dependence = probabilité de reprise rho ; rupture = hausse relative sur la seconde moitié.\n")
    heads = list(cfg.TESTS) + [ANY]
    for sc in scenarios:
        for n in sizes:
            sub = [r for r in rows if r["scenario"] == sc and r["n"] == n]
            if not sub:
                continue
            L.append(f"### {sc} — n = {n}\n")
            L.append("| niveau | " + " | ".join(heads) + " |")
            L.append("|---|" + "---|" * len(heads))
            for lv in sorted({r["level"] for r in sub}):
                cells = []
                for t in heads:
                    r = next(x for x in sub if x["level"] == lv and x["test"] == t)
                    cells.append(f"{_pct(r['rate'])} [{_pct(r['ci_low'])}–{_pct(r['ci_high'])}]")
                L.append(f"| {lv:g} | " + " | ".join(cells) + " |")
            L.append("")

    L.append("## 3. Biais minimal détectable à 80 % de puissance (CALCUL)\n")
    L.append("Interpolation linéaire entre niveaux testés (trois niveaux seulement : estimation grossière). "
             "« Non atteint » ou « <= plus bas niveau » signifie que les niveaux choisis ne permettent pas de conclure.\n")
    L.append("| scénario | n | test | biais minimal à 80 % |")
    L.append("|---|---|---|---|")
    for sc in scenarios:
        for n in sizes:
            for t in cfg.TESTS:
                sub = sorted([r for r in rows if r["scenario"] == sc and r["n"] == n and r["test"] == t],
                             key=lambda r: r["level"])
                if not sub:
                    continue
                val, note = min_detectable([r["level"] for r in sub], [r["rate"] for r in sub])
                txt = f"{val:.3g} ({note})" if val is not None else note
                L.append(f"| {sc} | {n} | {t} | {txt} |")
    L.append("")

    L.append("## 4. Limites (LIMITATION)\n")
    L.append("- Seuls les biais injectés ici sont évalués : l'absence de détection d'un biais non simulé n'est pas "
             "mesurée.")
    L.append("- Aucun des 4 tests n'est spécifique aux paires : un biais de paire n'est vu que par l'effet "
             "marginal qu'il induit sur les deux numéros.")
    L.append("- Un niveau où la puissance atteint ~100 % (saturation) ne permet pas d'estimer le biais minimal.")
    L.append("- Puissance estimée sur 200 répétitions par cellule : erreur type jusqu'à 3,5 points.")
    L.append("- Calibration par Monte-Carlo : erreur de l'ordre de 1/sqrt(100 000) sur les p-values.")
    L.append("- Le banc mesure le moteur de détection, pas un pouvoir prédictif (Niveau D du Cahier).")
    return "\n".join(L) + "\n"
