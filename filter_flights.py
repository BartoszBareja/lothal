import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Set, Tuple

MAX_STOPS = 1
MAX_PRICE_PLN = 6000
REQUIRED_LEG_FIELDS = ("airline", "airplane", "flight_number", "travel_class")

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


def _format_set(name: str, values: Set[str]) -> str:
    sorted_vals = sorted(values)
    rows = [sorted_vals[i : i + 6] for i in range(0, len(sorted_vals), 6)]
    lines = [", ".join(f'"{v}"' for v in row) for row in rows]
    inner = ",\n    ".join(lines)
    return f"{name} = {{\n    {inner}\n}}"


def update_airports_in_file(
    polish: Set[str],
    international: Set[str],
    script_path: Path,
) -> None:
    source = script_path.read_text(encoding="utf-8")

    new_polish = _format_set("VALID_POLISH_AIRPORTS", polish)
    new_intl = _format_set("VALID_INTERNATIONAL_AIRPORTS", international)

    pattern_polish = r"VALID_POLISH_AIRPORTS = \{[^}]*\}"
    pattern_intl = r"VALID_INTERNATIONAL_AIRPORTS = \{[^}]*\}"

    updated = re.sub(pattern_polish, new_polish, source, flags=re.DOTALL)
    updated = re.sub(pattern_intl, new_intl, updated, flags=re.DOTALL)

    if updated != source:
        script_path.write_text(updated, encoding="utf-8")


def _validate_flight(
    flight: dict,
    polish: Set[str],
    international: Set[str],
    new_polish: Set[str],
    new_intl: Set[str],
) -> List[str]:
    reasons: List[str] = []

    price = flight.get("price")
    if price is None:
        reasons.append("brak ceny")
    elif price > MAX_PRICE_PLN:
        reasons.append(f"cena zbyt wysoka: {price} PLN > {MAX_PRICE_PLN}")

    legs = flight.get("flights", [])
    stops = len(legs) - 1
    if stops > MAX_STOPS:
        reasons.append(f"za dużo przesiadek: {stops} > {MAX_STOPS}")

    if not legs:
        reasons.append("brak segmentów lotu")
    else:
        origin = legs[0].get("departure_airport", {}).get("id", "")
        destination = legs[-1].get("arrival_airport", {}).get("id", "")

        if not origin:
            reasons.append("puste id lotniska wylotu")
        elif origin not in polish:
            polish.add(origin)
            new_polish.add(origin)

        if not destination:
            reasons.append("puste id lotniska docelowego")
        elif destination not in international:
            international.add(destination)
            new_intl.add(destination)

    for leg in legs:
        for field in REQUIRED_LEG_FIELDS:
            if not leg.get(field):
                reasons.append(f"brak pola w segmencie: {field}")

    if not flight.get("carbon_emissions", {}).get("this_flight"):
        reasons.append("brak carbon_emissions.this_flight")

    return reasons


def collect_and_validate(
    results: List[dict],
    polish: Set[str],
    international: Set[str],
) -> Tuple[List[dict], Dict, Set[str], Set[str]]:
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
    new_intl = set()
    filtered_results = []

    for record in results:
        if "error" in record:
            stats["queries_with_error"] += 1
            continue

        kept_best = []
        kept_other = []

        for bucket, kept in [
            (record.get("best_flights", []), kept_best),
            (record.get("other_flights", []), kept_other),
        ]:
            for flight in bucket:
                stats["flights_total"] += 1
                reasons = _validate_flight(flight, polish, international, new_polish, new_intl)

                if reasons:
                    stats["flights_rejected"] += 1
                    for reason in reasons:
                        stats["rejection_reasons"][reason] = stats["rejection_reasons"].get(reason, 0) + 1
                else:
                    stats["flights_kept"] += 1
                    kept.append(flight)

        if kept_best or kept_other:
            filtered_results.append(
                {
                    **{k: v for k, v in record.items() if k not in ("best_flights", "other_flights")},
                    "best_flights": kept_best,
                    "other_flights": kept_other,
                }
            )

    if new_polish or new_intl:
        stats["new_airports_added"] = sorted(new_polish) + sorted(new_intl)

    return filtered_results, stats, new_polish, new_intl

def main():
    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("flights_20260314.json")

    if not input_path.exists():
        print(f"Błąd: plik {input_path} nie istnieje.")
        sys.exit(1)

    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)

    print(f"Wczytano: {input_path} ({data.get('total_queries', '?')} zapytań)")

    polish = set(VALID_POLISH_AIRPORTS)
    international = set(VALID_INTERNATIONAL_AIRPORTS)

    filtered, stats, new_polish, new_intl = collect_and_validate(data["results"], polish, international)

    output_path = input_path.with_name(input_path.stem + "_filtered" + input_path.suffix)
    output = {
        **{k: v for k, v in data.items() if k != "results"},
        "filtered_at": datetime.now(timezone.utc).isoformat(),
        "filter_config": {"max_stops": MAX_STOPS, "max_price_pln": MAX_PRICE_PLN},
        "total_queries": len(filtered),
        "results": filtered,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    if new_polish or new_intl:
        update_airports_in_file(polish, international, Path(__file__))

    print()
    print("── Statystyki filtrowania ──────────────────────")
    print(f"  Zapytania:    {stats['queries_total']} łącznie, {stats['queries_with_error']} z błędem API")
    print(f"  Loty łącznie: {stats['flights_total']}")
    kept_ratio = (stats["flights_kept"] / stats["flights_total"] * 100) if stats["flights_total"] else 0.0
    print(f"  Zachowane:    {stats['flights_kept']} ({kept_ratio:.1f}%)")
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
