from serpapi import GoogleSearch
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv(".env")

POLISH_AIRPORTS = [
    "WAW", "WMI", "KRK", "KTW", "GDN", "WRO",
    "POZ", "RZE", "LCJ", "SZZ", "BZG", "IEG", "OSP"
]

INTERNATIONAL_AIRPORTS = [
    "MAD", "BCN", "PMI", "ATH", "HER", "RHO", "LIS",
    "OPO", "FAO", "LHR", "LGW", "MAN", "ARN", "GOT",
    "MMX", "AMS", "EIN", "RTM", "JFK", "LAX", "ORD",
    "CAI", "HRG", "SSH", "AMM", "CPH", "BLL", "FRA"
]

# Grupy po 7 — limit SerpApi
POLISH_GROUPS = [POLISH_AIRPORTS[:7], POLISH_AIRPORTS[7:]]
INTERNATIONAL_GROUPS = [
    INTERNATIONAL_AIRPORTS[0:7],
    INTERNATIONAL_AIRPORTS[7:14],
    INTERNATIONAL_AIRPORTS[14:21],
    INTERNATIONAL_AIRPORTS[21:28],
]

TRIP_DURATION_DAYS = 7
SEARCH_WINDOW_DAYS = 3
START_DATE = datetime.today()

def generate_date_pairs(start: datetime, window_days: int, trip_days: int):
    """Generuje pary (outbound, return) dla każdego dnia w oknie wyszukiwania."""
    pairs = []
    for offset in range(window_days):
        outbound = start + timedelta(days=offset)
        ret = outbound + timedelta(days=trip_days)
        pairs.append((
            outbound.strftime("%Y-%m-%d"),
            ret.strftime("%Y-%m-%d")
        ))
    return pairs

def extract_flight_data(result: dict, departure_group: str, arrival_group: str, outbound_date: str, return_date: str) -> dict:
    """Wyciąga tylko potrzebne dane z odpowiedzi API."""
    return {
        "departure_group": departure_group,
        "arrival_group": arrival_group,
        "outbound_date": outbound_date,
        "return_date": return_date,
        "best_flights": result.get("best_flights", []),
        "other_flights": result.get("other_flights", []),
        "price_insights": result.get("price_insights", {}),
        "airports": result.get("airports", []),
    }

def main():
    date_pairs = generate_date_pairs(START_DATE, SEARCH_WINDOW_DAYS, TRIP_DURATION_DAYS)
    all_results = []
    total = len(POLISH_GROUPS) * len(INTERNATIONAL_GROUPS) * len(date_pairs)
    done = 0

    for outbound_date, return_date in date_pairs:
        for pol_group in POLISH_GROUPS:
            for int_group in INTERNATIONAL_GROUPS:
                dep_str = ", ".join(pol_group)
                arr_str = ", ".join(int_group)

                params = {
                    "engine": "google_flights",
                    "departure_id": dep_str,
                    "arrival_id": arr_str,
                    "currency": "PLN",
                    "type": "1",  # round trip
                    "outbound_date": outbound_date,
                    "return_date": return_date,
                    "api_key": os.getenv("api_key")
                }

                try:
                    search = GoogleSearch(params)
                    result = search.get_dict()
                    all_results.append(
                        extract_flight_data(result, dep_str, arr_str, outbound_date, return_date)
                    )
                except Exception as e:
                    all_results.append({
                        "departure_group": dep_str,
                        "arrival_group": arr_str,
                        "outbound_date": outbound_date,
                        "return_date": return_date,
                        "error": str(e)
                    })

                done += 1
                print(f"[{done}/{total}] {outbound_date} | {pol_group[0]}... → {int_group[0]}...")

    output = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "config": {
            "trip_duration_days": TRIP_DURATION_DAYS,
            "search_window_days": SEARCH_WINDOW_DAYS,
            "currency": "PLN",
            "polish_airports": POLISH_AIRPORTS,
            "international_airports": INTERNATIONAL_AIRPORTS,
        },
        "total_queries": len(all_results),
        "results": all_results
    }

    filename = f"flights_{START_DATE.strftime('%Y%m%d')}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nGotowe — zapisano {len(all_results)} zapytań do {filename}")

if __name__ == "__main__":
    main()