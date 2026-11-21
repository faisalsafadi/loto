"""Interface en ligne de commande (SPEC_V2 §4). Analyse : `analyze`. Hypothèses : `hypothesis ...`.
Données : `init-db`, `add`, `add-csv`, `draws`, `correct`, `corrections`. Tableau de bord : `dashboard`.
Usage : loto --help   (ou : python -m loto_research.cli --help)"""
import json
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

import typer

from loto_research.analysis.catalog import CATALOG
from loto_research.analysis.core import ensure_supported_game, run_quick_analysis
from loto_research.db.core import ValidationError, connect, count_draws, get_or_create_game, init_db
from loto_research.db.corrections import (apply_corrections, correct_draw, list_corrections, load_corrections,
                                          parse_changes, plan_correction)
from loto_research.db.hypotheses import available_draws, register_hypothesis, run_confirmatory_test
from loto_research.db.ingest import add_csv, add_new_draw, parse_numbers, prepare_draw
from loto_research.db.loader import load_draws_dataframe
from loto_research.db.runs import cumulative_test_count, dataset_hash, log_result, start_run

app = typer.Typer(help="Boîte à outils d'audit statistique des loteries.", no_args_is_help=True)
hyp_app = typer.Typer(help="Registre d'hypothèses : pré-enregistrement et test confirmatoire unique.",
                      no_args_is_help=True)
app.add_typer(hyp_app, name="hypothesis")
REPO_ROOT = Path(__file__).resolve().parents[2]

DB_OPT = typer.Option(Path("data/loto.sqlite"), help="Fichier de base SQLite")
GAME_OPT = typer.Option("Loto Maroc 6/49", help="Nom du jeu dans la base")


@app.callback()
def main():
    """Boîte à outils d'audit statistique des loteries."""


def _git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
    except Exception:
        return None


def _open(db, game):
    conn = connect(db)
    init_db(conn)
    game_row = conn.execute("SELECT * FROM games WHERE name = ?", (game,)).fetchone()
    if game_row is None:
        names = [r["name"] for r in conn.execute("SELECT name FROM games")]
        typer.echo(f"Jeu introuvable : {game!r}. Jeux disponibles : {names}", err=True)
        raise typer.Exit(1)
    return conn, game_row


@app.command("init-db")
def init_db_cmd(
    db: Path = DB_OPT,
    game: str = GAME_OPT,
    csv_path: Path = typer.Option(Path("data/public/loto_maroc_draws.csv"), "--csv",
                                  help="CSV des tirages à importer (livré avec le logiciel)"),
):
    """Crée la base à partir du CSV de tirages livré avec le logiciel. Validation complète, TOUT OU RIEN.
    Refuse de toucher à une base qui contient déjà des tirages."""
    if game != "Loto Maroc 6/49":
        typer.echo("Seul le Loto Maroc 6/49 est fourni avec le logiciel.", err=True)
        raise typer.Exit(1)
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(db)
    init_db(conn)
    game_id = get_or_create_game(conn, game, 6, 49, bonus_range=49, bonus_exclusive=True)
    if count_draws(conn, game_id) > 0:
        typer.echo(f"Refusé : {db} contient déjà des tirages. Rien n'a été modifié.", err=True)
        raise typer.Exit(1)
    try:
        prepared = add_csv(conn, game_id, csv_path)
    except ValidationError as e:
        typer.echo(f"Refusé (rien n'a été écrit) :\n{e}", err=True)
        raise typer.Exit(1)
    dates = sorted(p["draw_date"] for p in prepared)
    typer.echo(f"{len(prepared)} tirages importés dans {db}, du {dates[0]} au {dates[-1]}.")
    typer.echo(f"Empreinte des données (début) : {dataset_hash(conn, game_id)[:16]}")


@app.command("dashboard")
def dashboard(
    db: Path = DB_OPT,
    game: str = GAME_OPT,
    port: int = typer.Option(8501, help="Port local du tableau de bord"),
    writable: bool = typer.Option(False, "--writable",
                                  help="Active l'ajout de tirages, les corrections et le gel de prédictions"),
):
    """Lance le tableau de bord local (lecture seule par défaut, accessible seulement depuis cette machine)."""
    cmd = [sys.executable, "-m", "loto_research.dashboard", "--db", str(db), "--game", game, "--port", str(port)]
    if writable:
        cmd.append("--writable")
    raise typer.Exit(subprocess.call(cmd))


@app.command()
def analyze(
    db: Path = DB_OPT,
    game: str = GAME_OPT,
    n_sim: int = typer.Option(100000, help="Simulations Monte-Carlo pour H001"),
    n_perm: int = typer.Option(20000, help="Permutations pour H003"),
    seed: int = typer.Option(42, help="Graine aléatoire"),
    progress: bool = typer.Option(False, help="Afficher la progression des simulations"),
):
    """Analyse rapide (H001, H002, H003, H004, H007). Tous les résultats sont DESCRIPTIFS :
    aucun test confirmatoire n'existe sans hypothèse pré-enregistrée (`loto hypothesis`)."""
    conn, game_row = _open(db, game)
    try:
        ensure_supported_game(game_row)
    except NotImplementedError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)

    df = load_draws_dataframe(conn, game_row["id"])
    config = {"n_sim": n_sim, "n_perm": n_perm, "seed": seed}
    run_id = start_run(conn, game_row["id"], "quick", config, git_commit=_git_commit())
    typer.echo(f"=== loto analyze — lancement #{run_id} — {len(df)} tirages ({game}) ===")
    typer.echo("Résultats DESCRIPTIFS : pas de test confirmatoire sans hypothèse pré-enregistrée.\n")

    results = run_quick_analysis(df, n_sim, n_perm, seed, progress=progress)
    for r in results:
        log_result(conn, run_id, tag="DESCRIPTIVE", **r)
        if r["method"] == "fdr_bh":
            typer.echo(f"{r['label']:<11} {int(r['statistic'])}/{r['family_size']} significatifs après FDR-BH ; "
                       f"plus petit p brut = {r['p_raw']:.5f} (avant correction)  DESCRIPTIVE")
        else:
            stat = "-" if r["statistic"] is None else f"{r['statistic']:.4f}"
            p_raw = "-" if r["p_raw"] is None else f"{r['p_raw']:.5f}"
            typer.echo(f"{r['label']:<11} statistique={stat:>10}  p={p_raw:>8}  [{r['method']}]  DESCRIPTIVE")

    total = cumulative_test_count(conn, game_row["id"])
    typer.echo(f"\nNombre de tests distincts enregistrés pour ce jeu (par version des données) : {total}")
    typer.echo("Relancer sur des données identiques ne crée pas de nouvelle information et n'augmente pas ce total.")


@app.command("add")
def add(
    draw_date: str = typer.Option(..., "--date", help="Date du tirage, AAAA-MM-JJ"),
    numbers: str = typer.Option(..., help="Numéros principaux dans l'ordre de la source, ex. 5 12 23 31 40 44"),
    bonus: int = typer.Option(..., help="Numéro complémentaire"),
    source: str = typer.Option(..., help="Origine du tirage, ex. site officiel de la loterie"),
    source_ref: Optional[str] = typer.Option(None, help="URL ou référence précise"),
    draw_no: Optional[int] = typer.Option(None, help="Numéro de tirage officiel, si connu"),
    allow_same_date: bool = typer.Option(False, "--allow-same-date",
                                         help="DANGEREUX : autorise un 2e tirage à la même date (les deux seront analysés)"),
    yes: bool = typer.Option(False, "--yes", help="Ne pas demander de confirmation"),
    db: Path = DB_OPT,
    game: str = GAME_OPT,
):
    """Ajoute UN tirage (ajout seul : un tirage ne se modifie ni ne se supprime ; une erreur se corrige avec
    `loto correct`). Validation immédiate, source obligatoire, un seul tirage par date, confirmation."""
    conn, game_row = _open(db, game)
    try:
        nums = parse_numbers(numbers)
        prep = prepare_draw(conn, game_row["id"], draw_date, nums, bonus, source, allow_same_date=allow_same_date)
    except ValidationError as e:
        typer.echo(f"Refusé : {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Tirage à enregistrer : {prep['draw_date']}  numéros {prep['numbers']}  "
               f"complémentaire {prep['bonus']}")
    typer.echo(f"Source : {source}" + (f" ({source_ref})" if source_ref else ""))
    for note in prep["notes"]:
        typer.echo(f"NOTE : {note}")
    if not yes:
        typer.confirm("Enregistrer ? L'ajout est définitif.", abort=True)
    try:
        draw_id, _ = add_new_draw(conn, game_row["id"], draw_date, nums, bonus, source, source_ref=source_ref,
                                  source_draw_no=draw_no, allow_same_date=allow_same_date)
    except ValidationError as e:
        typer.echo(f"Refusé : {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Tirage #{draw_id} ajouté. Tirages dans la base : {count_draws(conn, game_row['id'])}.")


@app.command("add-csv")
def add_csv_cmd(
    path: Path = typer.Argument(..., help="CSV : date,n1..n6,bonus,source[,source_ref,draw_no]"),
    allow_same_date: bool = typer.Option(False, "--allow-same-date",
                                         help="DANGEREUX : autorise plusieurs tirages à la même date"),
    yes: bool = typer.Option(False, "--yes", help="Ne pas demander de confirmation"),
    db: Path = DB_OPT,
    game: str = GAME_OPT,
):
    """Ajoute plusieurs tirages depuis un CSV, TOUT OU RIEN : si une ligne est invalide, rien n'est écrit."""
    conn, game_row = _open(db, game)
    try:
        prepared = add_csv(conn, game_row["id"], path, allow_same_date=allow_same_date, dry_run=True)
    except ValidationError as e:
        typer.echo(f"Refusé (rien n'a été écrit) :\n{e}", err=True)
        raise typer.Exit(1)
    dates = sorted(p["draw_date"] for p in prepared)
    typer.echo(f"{len(prepared)} tirages valides, du {dates[0]} au {dates[-1]}.")
    for note in sorted({n for p in prepared for n in p["notes"]}):
        typer.echo(f"NOTE : {note}")
    if not yes:
        typer.confirm("Enregistrer ces tirages ? L'ajout est définitif.", abort=True)
    try:
        add_csv(conn, game_row["id"], path, allow_same_date=allow_same_date)
    except ValidationError as e:
        typer.echo(f"Refusé (rien n'a été écrit) :\n{e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"{len(prepared)} tirages ajoutés. Tirages dans la base : {count_draws(conn, game_row['id'])}.")


@app.command("draws")
def draws(
    last: int = typer.Option(10, help="Nombre de derniers tirages à afficher"),
    db: Path = DB_OPT,
    game: str = GAME_OPT,
):
    """Affiche le nombre de tirages, la période couverte et les derniers tirages (état corrigé)."""
    conn, game_row = _open(db, game)
    total = count_draws(conn, game_row["id"])
    lo, hi = conn.execute("SELECT MIN(draw_date), MAX(draw_date) FROM draws WHERE game_id = ?",
                          (game_row["id"],)).fetchone()
    typer.echo(f"{total} tirages ({game}), du {lo} au {hi}.")
    rows = conn.execute("SELECT id, draw_date, numbers_json, bonus, source FROM draws WHERE game_id = ? "
                        "ORDER BY draw_date DESC, id DESC LIMIT ?", (game_row["id"], last)).fetchall()
    corr = load_corrections(conn, game_row["id"])
    for r in rows:
        nums, b = apply_corrections(json.loads(r["numbers_json"]), r["bonus"], corr.get(r["id"], []))
        mark = "  (corrigé)" if r["id"] in corr else ""
        typer.echo(f"#{r['id']:<5} {r['draw_date']}  {nums}  +{b}  [{r['source']}]{mark}")


@app.command("correct")
def correct(
    draw_id: int = typer.Option(..., "--draw-id", help="Numéro du tirage (colonne # de `loto draws`)"),
    changes: List[str] = typer.Option(..., "--set", help="Changement champ=valeur, ex. n3=17 ou bonus=9 (répétable)"),
    reason: str = typer.Option(..., help="Pourquoi cette correction (obligatoire)"),
    author: str = typer.Option(..., help="Qui corrige (obligatoire)"),
    yes: bool = typer.Option(False, "--yes", help="Ne pas demander de confirmation"),
    db: Path = DB_OPT,
    game: str = GAME_OPT,
):
    """Corrige les numéros ou le complémentaire d'un tirage. Le tirage d'origine reste intact : la correction est
    une ligne ajoutée (raison, auteur, date) que le chargeur applique. La date n'est pas corrigeable.
    Plusieurs --set s'appliquent ensemble : le tirage final doit être valide."""
    conn, game_row = _open(db, game)
    try:
        plan = plan_correction(conn, draw_id, parse_changes(changes))
    except ValidationError as e:
        typer.echo(f"Refusé : {e}", err=True)
        raise typer.Exit(1)
    if plan["game_id"] != game_row["id"]:
        typer.echo(f"Refusé : le tirage #{draw_id} n'appartient pas au jeu {game!r}.", err=True)
        raise typer.Exit(1)
    typer.echo(f"Tirage #{draw_id} du {plan['draw_date']}")
    typer.echo(f"  avant : {plan['before'][0]}  +{plan['before'][1]}")
    typer.echo(f"  après : {plan['after'][0]}  +{plan['after'][1]}")
    typer.echo(f"  raison : {reason}   auteur : {author}")
    if not yes:
        typer.confirm("Enregistrer cette correction ? Elle est définitive (on peut la recorriger, pas l'effacer).",
                      abort=True)
    try:
        correct_draw(conn, draw_id, parse_changes(changes), reason, author)
    except ValidationError as e:
        typer.echo(f"Refusé : {e}", err=True)
        raise typer.Exit(1)
    typer.echo("Correction enregistrée. Le contenu analysé change : l'empreinte des données change aussi.")


@app.command("corrections")
def corrections_cmd(db: Path = DB_OPT, game: str = GAME_OPT):
    """Liste toutes les corrections enregistrées (traçabilité complète)."""
    conn, game_row = _open(db, game)
    rows = list_corrections(conn, game_row["id"])
    if not rows:
        typer.echo("Aucune correction enregistrée.")
        return
    for r in rows:
        typer.echo(f"#{r['id']} tirage #{r['draw_id']} ({r['draw_date']}) {r['field']} : {r['old_value']} -> "
                   f"{r['new_value']}  raison : {r['reason']}  par {r['author']} le {r['at']}")


@hyp_app.command("add")
def hypothesis_add(
    code: str = typer.Option(..., help="Identifiant court, ex. H009-v2"),
    h0: str = typer.Option(..., help="Hypothèse nulle"),
    h1: str = typer.Option(..., help="Hypothèse alternative (sens fixé ici, pas après)"),
    test_name: str = typer.Option(..., "--test", help=f"Test du catalogue : {', '.join(CATALOG)}"),
    params: str = typer.Option("{}", help='Paramètres JSON, ex. \'{"value": 2, "direction": "positive"}\''),
    correction: str = typer.Option("none", help="none | bonferroni"),
    family_size: int = typer.Option(1, help="Taille de la famille d'hypothèses pré-enregistrées ensemble"),
    kind: str = typer.Option("PRE_REGISTERED", help="PRE_REGISTERED | EXPLORATORY | POST_HOC"),
    n_star: Optional[int] = typer.Option(None, help="Effectif cible de tirages postérieurs (obligatoire si PRE_REGISTERED)"),
    db: Path = DB_OPT,
    game: str = GAME_OPT,
):
    """Enregistre une hypothèse AVANT de la tester. La date d'enregistrement est posée par l'outil."""
    conn, game_row = _open(db, game)
    try:
        hid = register_hypothesis(conn, game_row["id"], code, h0, h1, test_name, json.loads(params),
                                  correction=correction, family_size=family_size, kind=kind, n_star=n_star)
    except (ValidationError, NotImplementedError, json.JSONDecodeError) as e:
        typer.echo(f"Refusé : {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Hypothèse #{hid} ({code}, {kind}) enregistrée. Seuls les tirages de date strictement "
               f"postérieure à aujourd'hui pourront la tester.")


@hyp_app.command("list")
def hypothesis_list(db: Path = DB_OPT, game: str = GAME_OPT):
    """Liste les hypothèses, les tirages postérieurs disponibles et l'issue éventuelle."""
    conn, game_row = _open(db, game)
    rows = conn.execute("SELECT * FROM hypotheses WHERE game_id = ? ORDER BY id", (game_row["id"],)).fetchall()
    if not rows:
        typer.echo("Aucune hypothèse enregistrée.")
        return
    for h in rows:
        out = conn.execute("SELECT * FROM hypothesis_outcomes WHERE hypothesis_id = ?", (h["id"],)).fetchone()
        n_avail = available_draws(conn, h)
        status = f"{out['decision']} (p={out['p_value']:.5f}, alpha={out['alpha_effective']:.4f})" if out else "non testée"
        target = f"{n_avail}/{h['n_star']} tirages" if h["n_star"] else f"{n_avail} tirages postérieurs (exploratoire)"
        typer.echo(f"#{h['id']} {h['code']:<12} {h['kind']:<14} {h['test_name']:<20} enregistrée le "
                   f"{h['registered_date']}  {target}  -> {status}")


@hyp_app.command("test")
def hypothesis_test(
    hypothesis_id: int = typer.Argument(..., help="Numéro de l'hypothèse"),
    alpha: float = typer.Option(0.05, help="Seuil avant correction"),
    seed: int = typer.Option(42, help="Graine aléatoire"),
    db: Path = DB_OPT,
    game: str = GAME_OPT,
):
    """Test confirmatoire UNIQUE, sur les n_star premiers tirages postérieurs à l'enregistrement."""
    conn, _ = _open(db, game)
    try:
        r = run_confirmatory_test(conn, hypothesis_id, alpha=alpha, seed=seed, git_commit=_git_commit())
    except ValidationError as e:
        typer.echo(f"Refusé : {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"{r['code']} : {r['decision']}  statistique={r['statistic']:.4f}  p={r['p_value']:.5f}  "
               f"alpha effectif={r['alpha_effective']:.4f}  ({r['n_draws_used']} tirages)")
    typer.echo("Ce test confirmatoire est définitif : l'hypothèse ne pourra pas être testée de nouveau.")


if __name__ == "__main__":
    app()
