"""
filter_flights.py — filtrowanie danych lotów z pliku JSON generowanego przez scrapper.py

Kryteria odrzucenia lotu:
  1. brak ceny (price is None) lub cena > 6000 PLN
  2. więcej niż MAX_STOPS przesiadek (liczba segmentów - 1)
  3. puste id lotniska wylotu lub docelowego

Nieznane lotniska (spoza list poniżej) są zachowywane i automatycznie
dopisywane do odpowiedniej stałej — skrypt nadpisuje sam siebie.
"""

import json
import re
import sys
from typing import Dict, List, Set, Tuple
from pathlib import Path
from datetime import datetime, timezone

# ── Parametry filtrowania ────────────────────────────────────────────────────

MAX_STOPS = 1

VALID_POLISH_AIRPORTS = {
    "BZG", "GDN", "IEG", "KRK", "KTW", "LCJ",
    "OSP", "POZ", "RZE", "SZZ", "WAW", "WMI",
    "WRO"
}

VALID_INTERNATIONAL_AIRPORTS = {
    "AMM", "AMS", "ARN", "ATH", "BCN", "BLL",
    "CAI", "CPH", "EIN", "FAO", "FRA", "GOT",
    "HER", "HRG", "JFK", "LAX", "LGW", "LHR",
    "LIS", "MAD", "MAN", "MMX", "OPO", "ORD",
    "PMI", "RHO", "RTM", "SSH"
}

# ── Aktualizacja stałych w tym pliku ─────────────────────────────────────────

def _format_set(name: str, values: Set[str]) -> str:
    """Formatuje set lotnisk jako blok kodu Pythona (posortowany, po 6 w wierszu)."""
    sorted_vals = sorted(values)
    rows = [sorted_vals[i:i+6] for i in range(0, len(sorted_vals), 6)]
    lines = [", ".join(f'"{v}"' for v in row) for row in rows]
    inner = ",\n    ".join(lines)
    return f"{name} = {{\n    {inner}\n}}"


def update_airports_in_file(
    polish: Set[str],
    international: Set[str],
    script_path: Path,
) -> None:
    """Nadpisuje stałe VALID_*_AIRPORTS w tym pliku jeśli coś się zmieniło."""
    source = script_path.read_text(encoding="utf-8")

    new_polish      = _format_set("VALID_POLISH_AIRPORTS", polish)
    new_intl        = _format_set("VALID_INTERNATIONAL_AIRPORTS", international)

    # Zamień blok od nazwy stałej do zamykającego }
    pattern_polish  = r"VALID_POLISH_AIRPORTS = \{[^}]*\}"
    pattern_intl    = r"VALID_INTERNATIONAL_AIRPORTS = \{[^}]*\}"

    updated = re.sub(pattern_polish, new_polish, source, flags=re.DOTALL)
    updated = re.sub(pattern_intl,   new_intl,   updated, flags=re.DOTALL)

    if updated != source:
        script_path.write_text(updated, encoding="utf-8")

# ── Logika filtrowania ───────────────────────────────────────────────────────

def collect_and_validate(
    results: List[dict],
    polish: Set[str],
    international: Set[str],
) -> Tuple[List[dict], Dict, Set[str], Set[str]]:
    """
    Filtruje wyniki, zbiera nieznane lotniska i dodaje je do odpowiednich setów.
    Zwraca (filtered_results, stats, new_polish_found, new_intl_found).
    """
    stats = {
        "queries_total": len(results),
        "queries_with_error": 0,
        "flights_total": 0,
        "flights_kept": 0,
        "flights_rejected": 0,
        "rejection_reasons": {},
        "new_airports_added": [],
    }

    new_polish = set()
    new_intl   = set()
    filtered_results = []

    for record in results:
        if "error" in record:
            stats["queries_with_error"] += 1
            continue

        kept_best  = []
        kept_other = []

        for bucket, kept in [
            (record.get("best_flights",  []), kept_best),
            (record.get("other_flights", []), kept_other),
        ]:
            for flight in bucket:
                stats["flights_total"] += 1
                reasons = []

                # 1. Cena
                price = flight.get("price")
                if price is None:
                    reasons.append("brak ceny")
                elif price > 6000:
                    reasons.append(f"cena zbyt wysoka: {price} PLN > 6000")

                # 2. Przesiadki
                legs = flight.get("flights", [])
                stops = len(legs) - 1
                if stops > MAX_STOPS:
                    reasons.append(f"za dużo przesiadek: {stops} > {MAX_STOPS}")

                # 3. Lotniska — puste id = odrzuć; nieznane = dodaj do listy
                if not legs:
                    reasons.append("brak segmentów lotu")
                else:
                    origin = legs[0].get("departure_airport", {}).get("id", "")
                    dest   = legs[-1].get("arrival_airport",  {}).get("id", "")

                    if not origin:
                        reasons.append("puste id lotniska wylotu")
                    elif origin not in polish:
                        polish.add(origin)
                        new_polish.add(origin)

                    if not dest:
                        reasons.append("puste id lotniska docelowego")
                    elif dest not in international:
                        international.add(dest)
                        new_intl.add(dest)

                # 4. Brakujące dane w segmentach
                REQUIRED_LEG_FIELDS = ["airline", "airplane", "flight_number", "travel_class"]
                for leg in legs:
                    for field in REQUIRED_LEG_FIELDS:
                        if not leg.get(field):
                            reasons.append(f"brak pola w segmencie: {field}")

                # 5. Brak emisji CO₂
                if not flight.get("carbon_emissions", {}).get("this_flight"):
                    reasons.append("brak carbon_emissions.this_flight")

                if reasons:
                    stats["flights_rejected"] += 1
                    for r in reasons:
                        stats["rejection_reasons"][r] = stats["rejection_reasons"].get(r, 0) + 1
                else:
                    stats["flights_kept"] += 1
                    kept.append(flight)

        if kept_best or kept_other:
            filtered_results.append({
                **{k: v for k, v in record.items() if k not in ("best_flights", "other_flights")},
                "best_flights":  kept_best,
                "other_flights": kept_other,
            })

    if new_polish or new_intl:
        stats["new_airports_added"] = sorted(new_polish) + sorted(new_intl)

    return filtered_results, stats, new_polish, new_intl


# ── Punkt wejścia ────────────────────────────────────────────────────────────

def main():
    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("flights_20260314.json")

    if not input_path.exists():
        print(f"Błąd: plik {input_path} nie istnieje.")
        sys.exit(1)

    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)

    print(f"Wczytano: {input_path} ({data.get('total_queries', '?')} zapytań)")

    # Pracujemy na kopiach setów — update_airports_in_file zapisze zmiany
    polish        = set(VALID_POLISH_AIRPORTS)
    international = set(VALID_INTERNATIONAL_AIRPORTS)

    filtered, stats, new_polish, new_intl = collect_and_validate(
        data["results"], polish, international
    )

    # Zapisz przefiltrowany JSON
    output_path = input_path.with_name(input_path.stem + "_filtered" + input_path.suffix)
    output = {
        **{k: v for k, v in data.items() if k != "results"},
        "filtered_at": datetime.now(timezone.utc).isoformat(),
        "filter_config": {"max_stops": MAX_STOPS, "max_price_pln": 6000},
        "total_queries": len(filtered),
        "results": filtered,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # Nadpisz stałe w tym pliku jeśli pojawiły się nowe lotniska
    if new_polish or new_intl:
        update_airports_in_file(polish, international, Path(__file__))

    # Raport
    print()
    print("── Statystyki filtrowania ──────────────────────")
    print(f"  Zapytania:    {stats['queries_total']} łącznie, {stats['queries_with_error']} z błędem API")
    print(f"  Loty łącznie: {stats['flights_total']}")
    print(f"  Zachowane:    {stats['flights_kept']} ({stats['flights_kept'] / stats['flights_total'] * 100:.1f}%)")
    print(f"  Odrzucone:    {stats['flights_rejected']}")
    if stats["rejection_reasons"]:
        print("  Powody odrzucenia:")
        for reason, count in sorted(stats["rejection_reasons"].items(), key=lambda x: -x[1]):
            print(f"    [{count:>4}x] {reason}")
    if new_polish:
        print(f"  Nowe polskie lotniska dodane do listy:        {sorted(new_polish)}")
    if new_intl:
        print(f"  Nowe międzynarodowe lotniska dodane do listy: {sorted(new_intl)}")
    print()
    print(f"  Zapisano do: {output_path}")


if __name__ == "__main__":
    main()
