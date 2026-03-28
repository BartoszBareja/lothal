from pathlib import Path
from typing import Dict

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def _save_and_close(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()
    return path


def chart_cheapest_routes(df: pd.DataFrame, out_dir: Path, top_n: int = 15) -> Dict[str, object]:
    subset = df.dropna(subset=["price_pln", "departure_airport", "destination_airport"]).copy()
    if subset.empty:
        return {"status": "skipped", "reason": "No valid route+price rows."}

    subset["route"] = subset["departure_airport"] + " -> " + subset["destination_airport"]
    cheapest = (
        subset.groupby("route", as_index=False)["price_pln"]
        .min()
        .nsmallest(top_n, "price_pln")
    )

    plt.figure(figsize=(14, 8))
    bars = plt.barh(cheapest["route"], cheapest["price_pln"], color="#ef476f")
    plt.xlabel("Price (PLN)")
    plt.ylabel("Route")
    plt.title(f"Top {top_n} cheapest routes")
    plt.gca().invert_yaxis()

    for bar in bars:
        plt.text(bar.get_width() + 10, bar.get_y() + bar.get_height() / 2, f"{bar.get_width():.0f}", va="center")

    plot_path = _save_and_close(out_dir / "chart_01_cheapest_routes.png")
    return {"status": "ok", "plot": str(plot_path), "rows": len(cheapest)}


def chart_daily_trend(df: pd.DataFrame, out_dir: Path, top_destinations: int = 10) -> Dict[str, object]:
    subset = df.dropna(subset=["outbound_date", "destination_airport", "price_pln"])
    if subset.empty:
        return {"status": "skipped", "reason": "No valid date/destination/price rows."}

    grouped = (
        subset.groupby(["outbound_date", "destination_airport"], as_index=False)["price_pln"]
        .min()
        .sort_values("outbound_date")
    )

    top = grouped["destination_airport"].value_counts().head(top_destinations).index
    grouped = grouped[grouped["destination_airport"].isin(top)]

    plt.figure(figsize=(15, 8))
    for dest in sorted(grouped["destination_airport"].unique()):
        d = grouped[grouped["destination_airport"] == dest]
        plt.plot(d["outbound_date"], d["price_pln"], marker="o", linewidth=1.5, markersize=4, label=dest)

    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=2))
    plt.xticks(rotation=45)
    plt.xlabel("Outbound date")
    plt.ylabel("Daily minimum price (PLN)")
    plt.title("Daily min price trend by destination")
    plt.grid(alpha=0.3, linestyle="--")
    plt.legend(title="Destination", ncol=2, fontsize=8)

    plot_path = _save_and_close(out_dir / "chart_02_daily_trend.png")
    return {"status": "ok", "plot": str(plot_path), "rows": len(grouped)}


def chart_price_histogram(df: pd.DataFrame, out_dir: Path) -> Dict[str, object]:
    prices = df["price_pln"].dropna()
    if prices.empty:
        return {"status": "skipped", "reason": "No price data."}

    median = float(prices.median())
    q25 = float(prices.quantile(0.25))
    q75 = float(prices.quantile(0.75))

    plt.figure(figsize=(12, 7))
    plt.hist(prices, bins=35, color="#06d6a0", edgecolor="#073b4c", alpha=0.85)
    plt.axvline(median, color="#ef476f", linestyle="-", linewidth=2, label=f"Median: {median:.0f}")
    plt.axvline(q25, color="#ffd166", linestyle="--", linewidth=1.5, label=f"Q25: {q25:.0f}")
    plt.axvline(q75, color="#ffd166", linestyle="--", linewidth=1.5, label=f"Q75: {q75:.0f}")
    plt.xlabel("Price (PLN)")
    plt.ylabel("Flight count")
    plt.title("Price distribution")
    plt.legend()
    plt.grid(alpha=0.2)

    plot_path = _save_and_close(out_dir / "chart_03_price_histogram.png")
    return {
        "status": "ok",
        "plot": str(plot_path),
        "rows": int(prices.count()),
        "metrics": {
            "count": int(prices.count()),
            "min": float(prices.min()),
            "q25": q25,
            "median": median,
            "q75": q75,
            "max": float(prices.max()),
        },
    }


def chart_destination_boxplot(df: pd.DataFrame, out_dir: Path, top_destinations: int = 12) -> Dict[str, object]:
    subset = df.dropna(subset=["destination_airport", "price_pln"])
    if subset.empty:
        return {"status": "skipped", "reason": "No destination+price data."}

    top = subset["destination_airport"].value_counts().head(top_destinations).index
    subset = subset[subset["destination_airport"].isin(top)]

    labels = sorted(subset["destination_airport"].unique())
    data = [subset[subset["destination_airport"] == d]["price_pln"].values for d in labels]

    plt.figure(figsize=(14, 8))
    plt.boxplot(data, labels=labels, patch_artist=True)
    plt.xlabel("Destination")
    plt.ylabel("Price (PLN)")
    plt.title("Price spread by destination")
    plt.grid(axis="y", alpha=0.25)

    plot_path = _save_and_close(out_dir / "chart_04_destination_boxplot.png")
    summary = (
        subset.groupby("destination_airport", as_index=False)["price_pln"]
        .agg(["count", "min", "median", "mean", "max"])
        .reset_index()
    )
    return {
        "status": "ok",
        "plot": str(plot_path),
        "rows": len(subset),
        "metrics": {
            "destinations": int(len(labels)),
            "avg_price": float(subset["price_pln"].mean()),
            "median_price": float(subset["price_pln"].median()),
            "min_price": float(subset["price_pln"].min()),
            "max_price": float(subset["price_pln"].max()),
        },
    }


def chart_price_heatmap(df: pd.DataFrame, out_dir: Path) -> Dict[str, object]:
    subset = df.dropna(subset=["outbound_date", "destination_airport", "price_pln"])
    if subset.empty:
        return {"status": "skipped", "reason": "No date+destination+price data."}

    pivot = subset.pivot_table(
        index="destination_airport",
        columns="outbound_date",
        values="price_pln",
        aggfunc="min",
    ).sort_index()

    plt.figure(figsize=(15, 8))
    im = plt.imshow(pivot.values, aspect="auto", cmap="viridis")
    plt.colorbar(im, label="Min price (PLN)")
    plt.yticks(range(len(pivot.index)), pivot.index)
    plt.xticks(range(len(pivot.columns)), [d.strftime("%m-%d") for d in pivot.columns], rotation=60)
    plt.xlabel("Outbound date")
    plt.ylabel("Destination")
    plt.title("Heatmap: min price by date and destination")

    plot_path = _save_and_close(out_dir / "chart_05_price_heatmap.png")
    return {"status": "ok", "plot": str(plot_path), "rows": int(pivot.size)}


def chart_price_vs_distance(df: pd.DataFrame, out_dir: Path) -> Dict[str, object]:
    subset = df.dropna(subset=["price_pln", "total_distance_km"])
    subset = subset[(subset["price_pln"] > 0) & (subset["total_distance_km"] > 0)]
    if len(subset) < 3:
        return {"status": "skipped", "reason": "Not enough points for regression."}

    x = subset["total_distance_km"].to_numpy()
    y = subset["price_pln"].to_numpy()

    slope, intercept = np.polyfit(x, y, 1)
    y_pred = slope * x + intercept
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1 - (ss_res / ss_tot) if ss_tot else np.nan

    plt.figure(figsize=(12, 8))
    plt.scatter(x, y, alpha=0.45, s=20, color="#118ab2", label="Flights")
    order = np.argsort(x)
    plt.plot(x[order], y_pred[order], color="#ef476f", linewidth=2.2, label=f"Fit: y={slope:.2f}x+{intercept:.2f}")
    plt.xlabel("Total distance (km)")
    plt.ylabel("Price (PLN)")
    plt.title(f"Price vs distance (R2={r2:.3f})")
    plt.grid(alpha=0.25)
    plt.legend()

    plot_path = _save_and_close(out_dir / "chart_06_price_vs_distance.png")
    return {
        "status": "ok",
        "plot": str(plot_path),
        "rows": int(len(subset)),
        "metrics": {
            "samples": int(len(subset)),
            "slope": float(slope),
            "intercept": float(intercept),
            "r2": float(r2),
        },
    }


def chart_co2_vs_price(df: pd.DataFrame, out_dir: Path) -> Dict[str, object]:
    subset = df.dropna(subset=["price_pln", "carbon_grams"]).copy()
    if subset.empty:
        return {"status": "skipped", "reason": "No CO2+price data."}

    subset["co2_per_100km"] = np.where(
        subset["total_distance_km"].fillna(0) > 0,
        subset["carbon_grams"] / subset["total_distance_km"] * 100,
        np.nan,
    )

    x = subset["carbon_grams"].to_numpy()
    y = subset["price_pln"].to_numpy()
    slope, intercept = np.polyfit(x, y, 1) if len(subset) >= 3 else (np.nan, np.nan)

    plt.figure(figsize=(12, 8))
    plt.scatter(x, y, alpha=0.45, s=22, color="#8338ec", label="Flights")
    if len(subset) >= 3:
        order = np.argsort(x)
        y_pred = slope * x + intercept
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot else np.nan
        plt.plot(x[order], y_pred[order], color="#ef476f", linewidth=2, label=f"Fit: y={slope:.6f}x+{intercept:.1f}")
    else:
        r2 = np.nan

    plt.xlabel("CO2 (grams)")
    plt.ylabel("Price (PLN)")
    plt.title("CO2 vs price")
    plt.grid(alpha=0.25)
    plt.legend()

    plot_path = _save_and_close(out_dir / "chart_07_co2_vs_price.png")
    return {
        "status": "ok",
        "plot": str(plot_path),
        "rows": len(subset),
        "metrics": {
            "samples": int(len(subset)),
            "avg_co2_grams": float(subset["carbon_grams"].mean()),
            "median_co2_grams": float(subset["carbon_grams"].median()),
            "avg_co2_per_100km": float(subset["co2_per_100km"].dropna().mean()) if subset["co2_per_100km"].notna().any() else np.nan,
            "slope": float(slope) if not np.isnan(slope) else np.nan,
            "intercept": float(intercept) if not np.isnan(intercept) else np.nan,
            "r2": float(r2) if not np.isnan(r2) else np.nan,
        },
    }


def chart_co2_efficiency_by_destination(df: pd.DataFrame, out_dir: Path, top_n: int = 12) -> Dict[str, object]:
    subset = df.dropna(subset=["destination_airport", "carbon_grams", "total_distance_km"]).copy()
    subset = subset[subset["total_distance_km"] > 0]
    if subset.empty:
        return {"status": "skipped", "reason": "No destination+CO2+distance rows."}

    subset["co2_per_100km"] = subset["carbon_grams"] / subset["total_distance_km"] * 100
    grouped = (
        subset.groupby("destination_airport", as_index=False)
        .agg(
            flights=("co2_per_100km", "count"),
            avg_co2_per_100km=("co2_per_100km", "mean"),
            median_co2_per_100km=("co2_per_100km", "median"),
            avg_price=("price_pln", "mean"),
        )
        .sort_values("avg_co2_per_100km")
        .head(top_n)
    )

    plt.figure(figsize=(14, 8))
    bars = plt.barh(grouped["destination_airport"], grouped["avg_co2_per_100km"], color="#2a9d8f")
    plt.gca().invert_yaxis()
    plt.xlabel("Average CO2 per 100 km (grams)")
    plt.ylabel("Destination")
    plt.title(f"Top {top_n} CO2-efficient destinations")
    plt.grid(axis="x", alpha=0.25)

    for bar in bars:
        plt.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2, f"{bar.get_width():.1f}", va="center")

    plot_path = _save_and_close(out_dir / "chart_08_co2_efficiency_destinations.png")
    return {
        "status": "ok",
        "plot": str(plot_path),
        "rows": len(grouped),
        "metrics": {
            "destinations": int(len(grouped)),
            "best_destination": str(grouped.iloc[0]["destination_airport"]) if not grouped.empty else None,
            "best_avg_co2_per_100km": float(grouped.iloc[0]["avg_co2_per_100km"]) if not grouped.empty else np.nan,
        },
    }
