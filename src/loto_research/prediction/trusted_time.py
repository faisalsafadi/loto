"""Heure de référence pour le gel des prédictions.

On interroge d'abord des sites fiables (en-tête HTTP « Date », précision d'environ une seconde). Si aucun n'est joignable
(internet coupé), l'horloge de l'ordinateur sert de secours. Quand les deux sont connues, on retient la PLUS TARDIVE :
un gel n'est accepté que si les deux horloges sont avant l'heure limite. La source et l'écart sont enregistrés dans le
fichier figé."""
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

SOURCES = ("https://www.google.com", "https://www.cloudflare.com", "https://www.wikipedia.org")
SKEW_WARNING_SECONDS = 120


def online_time(timeout=3.0, sources=SOURCES):
    """(datetime UTC, hôte) d'après l'en-tête Date d'un site fiable, ou None si aucun n'est joignable."""
    for url in sources:
        try:
            req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "loto-research"})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                header = response.headers.get("Date")
            if header:
                dt = parsedate_to_datetime(header)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc), url.split("//", 1)[1]
        except Exception:
            continue
    return None


def reference_now(fetch=online_time, system_now=None):
    """Heure de référence : {now (UTC), source, skew_seconds, warning}. `fetch` et `system_now` sont injectables
    pour les tests."""
    sys_now = system_now or datetime.now(timezone.utc)
    got = fetch()
    if got is None:
        return {"now": sys_now, "source": "system", "skew_seconds": None,
                "warning": "Heure en ligne indisponible : horloge de l'ordinateur utilisée."}
    online, host = got
    skew = (sys_now - online).total_seconds()
    warning = None
    if abs(skew) > SKEW_WARNING_SECONDS:
        warning = f"L'horloge de l'ordinateur est décalée de {skew:+.0f} s par rapport à l'heure en ligne."
    return {"now": max(sys_now, online), "source": f"online:{host}", "skew_seconds": round(skew, 1),
            "warning": warning}


def clock_record(info):
    """Version enregistrable (JSON) de l'heure de référence."""
    return {"source": info["source"], "skew_seconds": info["skew_seconds"], "warning": info["warning"],
            "reference_utc": info["now"].isoformat(timespec="seconds")}
