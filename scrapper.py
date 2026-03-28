from serpapi import GoogleSearch
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from math import radians, sin, cos, sqrt, atan2

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

AIRPORT_COORDS = {
    # Polskie
    "WAW": (52.1657, 20.9671),
    "WMI": (52.4511, 20.6518),
    "KRK": (50.0777, 19.7848),
    "KTW": (50.4743, 19.0800),
    "GDN": (54.3776, 18.4662),
    "WRO": (51.1027, 16.8858),
    "POZ": (52.4210, 16.8260),
    "RZE": (50.1100, 22.0189),
    "LCJ": (51.7219, 19.3981),
    "SZZ": (53.5847, 14.9022),
    "BZG": (53.0968, 17.9777),
    "IEG": (52.1385, 15.7986),
    "OSP": (54.4739, 17.0844),
    # Hiszpania
    "MAD": (40.4936, -3.5668),
    "BCN": (41.2971, 2.0785),
    "PMI": (39.5517, 2.7388),
    # Grecja
    "ATH": (37.9364, 23.9445),
    "HER": (35.3397, 25.1803),
    "RHO": (36.4054, 28.0862),
    # Portugalia
    "LIS": (38.7813, -9.1359),
    "OPO": (41.2481, -8.6814),
    "FAO": (37.0144, -7.9659),
    # UK
    "LHR": (51.4775, -0.4614),
    "LGW": (51.1537, -0.1821),
    "MAN": (53.3537, -2.2750),
    # Szwecja
    "ARN": (59.6519, 17.9186),
    "GOT": (57.6628, 12.2798),
    "MMX": (55.5363, 13.3762),
    # Holandia
    "AMS": (52.3086, 4.7639),
    "EIN": (51.4501, 5.3922),
    "RTM": (51.9569, 4.4372),
    # USA
    "JFK": (40.6413, -73.7781),
    "LAX": (33.9425, -118.4081),
    "ORD": (41.9742, -87.9073),
    # Egipt
    "CAI": (30.1219, 31.4056),
    "HRG": (27.1783, 33.7994),
    "SSH": (27.9773, 34.3950),
    # Jordania
    "AMM": (31.7226, 35.9932),
    # Dania
    "CPH": (55.6180, 12.6508),
    "BLL": (55.7403, 9.1519),
    # Niemcy
    "FRA": (50.0379, 8.5622),
    "MUC": (48.3538, 11.7861),
    "BER": (52.3667, 13.5033),
}

POLISH_GROUPS = [POLISH_AIRPORTS[:7], POLISH_AIRPORTS[7:]]
INTERNATIONAL_GROUPS = [
    INTERNATIONAL_AIRPORTS[0:7],
    INTERNATIONAL_AIRPORTS[7:14],
    INTERNATIONAL_AIRPORTS[14:21],
    INTERNATIONAL_AIRPORTS[21:28],
]

TRIP_DURATION_DAYS = 7
SEARCH_WINDOW_DAYS = 30
START_DATE = datetime.today()


def haversine(iata1: str, iata2: str):
    """Zwraca dystans w km między dwoma lotniskami na podstawie kodów IATA."""
    if iata1 not in AIRPORT_COORDS or iata2 not in AIRPORT_COORDS:
        return None

    R = 6371.0
    lat1, lon1 = map(radians, AIRPORT_COORDS[iata1])
    lat2, lon2 = map(radians, AIRPORT_COORDS[iata2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return round(R * 2 * atan2(sqrt(a), sqrt(1 - a)), 1)


def generate_date_pairs(start: datetime, window_days: int, trip_days: int):
    pairs = []
    for offset in range(window_days):
        outbound = start + timedelta(days=offset)
        ret = outbound + timedelta(days=trip_days)
        pairs.append((
            outbound.strftime("%Y-%m-%d"),
            ret.strftime("%Y-%m-%d")
        ))
    return pairs


def enrich_flights_with_distance(flights: list) -> list:
    """Dodaje dystans i współrzędne do każdego segmentu lotu."""
    for flight in flights:
        total_distance = 0
        for segment in flight.get("flights", []):
            dep_id = segment["departure_airport"]["id"]
            arr_id = segment["arrival_airport"]["id"]
            dist = haversine(dep_id, arr_id)
            segment["distance_km"] = dist
            segment["departure_airport"]["coords"] = AIRPORT_COORDS.get(dep_id)
            segment["arrival_airport"]["coords"] = AIRPORT_COORDS.get(arr_id)
            if dist:
                total_distance += dist
        flight["total_distance_km"] = round(total_distance, 1) if total_distance else None
    return flights


def extract_flight_data(result: dict, departure_group: str, arrival_group: str, outbound_date: str, return_date: str) -> dict:
    best   = enrich_flights_with_distance(result.get("best_flights",  []))
    other  = enrich_flights_with_distance(result.get("other_flights", []))
    return {
        "departure_group": departure_group,
        "arrival_group":   arrival_group,
        "outbound_date":   outbound_date,
        "return_date":     return_date,
        "best_flights":    best,
        "other_flights":   other,
        "price_insights":  result.get("price_insights", {}),
        "airports":        result.get("airports", []),
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
                    "engine":       "google_flights",
                    "departure_id": dep_str,
                    "arrival_id":   arr_str,
                    "currency":     "PLN",
                    "type":         "1",
                    "outbound_date": outbound_date,
                    "return_date":   return_date,
                    "api_key":       os.getenv("api_key")
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
                        "arrival_group":   arr_str,
                        "outbound_date":   outbound_date,
                        "return_date":     return_date,
                        "error":           str(e)
                    })

                done += 1
                print(f"[{done}/{total}] {outbound_date} | {pol_group[0]}... → {int_group[0]}...")

    output = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "config": {
            "trip_duration_days":    TRIP_DURATION_DAYS,
            "search_window_days":    SEARCH_WINDOW_DAYS,
            "currency":              "PLN",
            "polish_airports":       POLISH_AIRPORTS,
            "international_airports": INTERNATIONAL_AIRPORTS,
        },
        "airport_coords": AIRPORT_COORDS,
        "total_queries":  len(all_results),
        "results":        all_results
    }

    filename = f"flights_{START_DATE.strftime('%Y%m%d')}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nGotowe — zapisano {len(all_results)} zapytań do {filename}")


if __name__ == "__main__":
    main()