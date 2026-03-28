import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

from filter_flights import (
    VALID_INTERNATIONAL_AIRPORTS,
    VALID_POLISH_AIRPORTS,
    collect_and_validate,
)


def load_data(json_path: Path) -> Dict[str, Any]:
    with json_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def clean_results(data: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    results = data.get("results", [])
    polish = set(VALID_POLISH_AIRPORTS)
    international = set(VALID_INTERNATIONAL_AIRPORTS)

    filtered, stats, _, _ = collect_and_validate(results, polish, international)

    cleaned = {
        **{k: v for k, v in data.items() if k != "results"},
        "results": filtered,
        "total_queries": len(filtered),
    }
    return cleaned, stats


def flatten_flights(data: Dict[str, Any]) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []

    for result in data.get("results", []):
        outbound_date = result.get("outbound_date")
        return_date = result.get("return_date")

        for category in ("best_flights", "other_flights"):
            offers = result.get(category, [])
            for offer in offers:
                flights = offer.get("flights", [])
                if not flights:
                    continue

                first = flights[0]
                last = flights[-1]

                dep_airport = first.get("departure_airport", {})
                arr_airport = last.get("arrival_airport", {})

                dep_id = dep_airport.get("id")
                dest_id = arr_airport.get("id")

                distance = offer.get("total_distance_km")
                if distance is None:
                    seg_dist = [seg.get("distance_km") for seg in flights if seg.get("distance_km")]
                    distance = round(sum(seg_dist), 1) if seg_dist else None

                total_duration = offer.get("total_duration")
                if total_duration is None:
                    durations = [seg.get("duration") for seg in flights if seg.get("duration")]
                    total_duration = sum(durations) if durations else None

                carbon = offer.get("carbon_emissions", {}).get("this_flight")

                rows.append(
                    {
                        "outbound_date": outbound_date,
                        "return_date": return_date,
                        "category": category,
                        "trip_type": offer.get("type"),
                        "price_pln": offer.get("price"),
                        "departure_airport": dep_id,
                        "destination_airport": dest_id,
                        "dep_time": dep_airport.get("time"),
                        "arr_time": arr_airport.get("time"),
                        "airline": first.get("airline"),
                        "flight_number": first.get("flight_number"),
                        "travel_class": first.get("travel_class"),
                        "stops": max(len(flights) - 1, 0),
                        "segments": len(flights),
                        "total_distance_km": distance,
                        "total_duration_min": total_duration,
                        "carbon_grams": carbon,
                        "often_delayed": offer.get("often_delayed_by_over_30_min"),
                    }
                )

    df = pd.DataFrame(rows)
    if not df.empty:
        df["outbound_date"] = pd.to_datetime(df["outbound_date"], errors="coerce")
        df["return_date"] = pd.to_datetime(df["return_date"], errors="coerce")
        for col in ("price_pln", "total_distance_km", "total_duration_min", "carbon_grams", "stops"):
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def destination_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    enriched = df.copy()
    enriched["co2_per_100km"] = np.nan
    mask = (
        enriched["carbon_grams"].notna()
        & enriched["total_distance_km"].notna()
        & (enriched["total_distance_km"] > 0)
    )
    enriched.loc[mask, "co2_per_100km"] = (
        enriched.loc[mask, "carbon_grams"] / enriched.loc[mask, "total_distance_km"] * 100
    )

    summary = (
        enriched.dropna(subset=["destination_airport", "price_pln"])
        .groupby("destination_airport", as_index=False)
        .agg(
            flights_count=("price_pln", "count"),
            min_price_pln=("price_pln", "min"),
            median_price_pln=("price_pln", "median"),
            avg_price_pln=("price_pln", "mean"),
            avg_distance_km=("total_distance_km", "mean"),
            avg_carbon_g=("carbon_grams", "mean"),
            avg_co2_per_100km=("co2_per_100km", "mean"),
        )
        .sort_values("avg_price_pln")
    )
    return summary
