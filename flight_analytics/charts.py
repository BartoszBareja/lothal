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


def _save_table(df_table: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    df_table.to_csv(path, index=False, encoding="utf-8")
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
    table_path = _save_table(cheapest.rename(columns={"price_pln": "min_price_pln"}), out_dir / "table_01_cheapest_routes.csv")
    return {"status": "ok", "plot": str(plot_path), "table": str(table_path), "rows": len(cheapest)}


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
    table_path = _save_table(grouped.rename(columns={"price_pln": "min_price_pln"}), out_dir / "table_02_daily_trend.csv")
    return {"status": "ok", "plot": str(plot_path), "table": str(table_path), "rows": len(grouped)}


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
    metrics = {
        "count": int(prices.count()),
        "min": float(prices.min()),
        "q25": q25,
        "median": median,
        "q75": q75,
        "max": float(prices.max()),
    }
    table_path = _save_table(pd.DataFrame([metrics]), out_dir / "table_03_price_histogram.csv")
    return {
        "status": "ok",
        "plot": str(plot_path),
        "table": str(table_path),
        "rows": int(prices.count()),
        "metrics": metrics,
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
    table_path = _save_table(summary, out_dir / "table_04_destination_boxplot.csv")
    return {
        "status": "ok",
        "plot": str(plot_path),
        "table": str(table_path),
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
    table_path = _save_table(pivot.reset_index(), out_dir / "table_05_price_heatmap.csv")
    return {"status": "ok", "plot": str(plot_path), "table": str(table_path), "rows": int(pivot.size)}


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
    metrics = {
        "samples": int(len(subset)),
        "slope": float(slope),
        "intercept": float(intercept),
        "r2": float(r2),
    }
    table_path = _save_table(
        subset[["total_distance_km", "price_pln"]].sort_values("total_distance_km").reset_index(drop=True),
        out_dir / "table_06_price_vs_distance.csv",
    )
    return {
        "status": "ok",
        "plot": str(plot_path),
        "table": str(table_path),
        "rows": int(len(subset)),
        "metrics": metrics,
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
    table_cols = [c for c in ["carbon_grams", "price_pln", "co2_per_100km"] if c in subset.columns]
    table_path = _save_table(subset[table_cols].reset_index(drop=True), out_dir / "table_07_co2_vs_price.csv")
    return {
        "status": "ok",
        "plot": str(plot_path),
        "table": str(table_path),
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


def chart_feature_correlation_matrix(df: pd.DataFrame, out_dir: Path) -> Dict[str, object]:
    numeric_cols = ["price_pln", "stops", "total_distance_km", "total_duration_min", "carbon_grams"]
    available = [c for c in numeric_cols if c in df.columns]
    subset = df[available].dropna(how="all")
    if len(subset) < 3 or len(available) < 2:
        return {"status": "skipped", "reason": "Not enough numeric data for correlation matrix."}

    corr = subset.corr()

    fig, ax = plt.subplots(figsize=(10, 8))
    im = ax.imshow(corr.values, cmap="RdBu_r", vmin=-1, vmax=1)
    plt.colorbar(im, ax=ax, label="Pearson correlation")
    ax.set_xticks(range(len(corr.columns)))
    ax.set_yticks(range(len(corr.index)))
    ax.set_xticklabels(corr.columns, rotation=45, ha="right")
    ax.set_yticklabels(corr.index)
    ax.set_title("Feature correlation matrix")

    for i in range(len(corr.index)):
        for j in range(len(corr.columns)):
            val = corr.values[i, j]
            if not np.isnan(val):
                color = "white" if abs(val) > 0.6 else "black"
                ax.text(j, i, f"{val:.2f}", ha="center", va="center", fontsize=8, color=color)

    plot_path = _save_and_close(out_dir / "chart_09_feature_correlation_matrix.png")
    table_path = _save_table(corr.reset_index(), out_dir / "table_09_feature_correlation_matrix.csv")
    return {
        "status": "ok",
        "plot": str(plot_path),
        "table": str(table_path),
        "rows": int(len(subset)),
        "metrics": {c: corr["price_pln"].get(c, float("nan")) for c in available if c != "price_pln"},
    }


_INTERNATIONAL_AIRPORT_NAMES = {
    "AMM": "Amman (AMM)",
    "AMS": "Amsterdam (AMS)",
    "ARN": "Stockholm Arlanda (ARN)",
    "ATH": "Athens (ATH)",
    "BCN": "Barcelona (BCN)",
    "BLL": "Billund (BLL)",
    "CAI": "Cairo (CAI)",
    "CPH": "Copenhagen (CPH)",
    "EIN": "Eindhoven (EIN)",
    "FAO": "Faro (FAO)",
    "FRA": "Frankfurt (FRA)",
    "GOT": "Gothenburg (GOT)",
    "HER": "Heraklion (HER)",
    "HRG": "Hurghada (HRG)",
    "JFK": "New York JFK (JFK)",
    "LAX": "Los Angeles (LAX)",
    "LGW": "London Gatwick (LGW)",
    "LHR": "London Heathrow (LHR)",
    "LIS": "Lisbon (LIS)",
    "MAD": "Madrid (MAD)",
    "MAN": "Manchester (MAN)",
    "MMX": "Malmö (MMX)",
    "OPO": "Porto (OPO)",
    "ORD": "Chicago O'Hare (ORD)",
    "PMI": "Palma de Mallorca (PMI)",
    "RHO": "Rhodes (RHO)",
    "RTM": "Rotterdam (RTM)",
    "SSH": "Sharm el-Sheikh (SSH)",
}

# tab20 indices 14-15 are a gray pair — skip them so they don't clash with the "Other" slice
_PIE_COLORS = [c for i, c in enumerate(plt.colormaps["tab20"].colors) if i not in {14, 15}]

_POLISH_AIRPORT_NAMES = {
    "BZG": "Bydgoszcz (BZG)",
    "GDN": "Gdańsk (GDN)",
    "IEG": "Zielona Góra (IEG)",
    "KRK": "Kraków (KRK)",
    "KTW": "Katowice (KTW)",
    "LCJ": "Łódź (LCJ)",
    "OSP": "Koszalin (OSP)",
    "POZ": "Poznań (POZ)",
    "RZE": "Rzeszów (RZE)",
    "SZZ": "Szczecin (SZZ)",
    "WAW": "Warszawa Chopin (WAW)",
    "WMI": "Warszawa Modlin (WMI)",
    "WRO": "Wrocław (WRO)",
}


def chart_polish_airport_share(df: pd.DataFrame, out_dir: Path, top_n: int = 8) -> Dict[str, object]:
    from filter_flights import VALID_POLISH_AIRPORTS

    subset = df[df["departure_airport"].isin(VALID_POLISH_AIRPORTS)].dropna(subset=["departure_airport"])
    if subset.empty:
        return {"status": "skipped", "reason": "No flights from Polish airports."}

    counts = subset["departure_airport"].value_counts()
    top = counts.head(top_n)
    other_count = counts.iloc[top_n:].sum()
    if other_count > 0:
        top = pd.concat([top, pd.Series({"Other": other_count})])

    labels = [_POLISH_AIRPORT_NAMES.get(code, code) for code in top.index]
    n_named = len(top) - (1 if other_count > 0 else 0)
    colors = list(_PIE_COLORS[:n_named])
    if other_count > 0:
        colors.append("#cccccc")

    fig, ax = plt.subplots(figsize=(10, 10))
    wedges, texts, autotexts = ax.pie(
        top.values,
        labels=labels,
        autopct="%1.1f%%",
        startangle=140,
        pctdistance=0.78,
        colors=colors,
    )
    for at in autotexts:
        at.set_fontsize(9)
    ax.set_title("Share of flights by Polish departure airport", pad=20)

    plot_path = _save_and_close(out_dir / "chart_10_polish_airport_share.png")
    table_path = _save_table(
        counts.reset_index().rename(columns={"index": "airport", "departure_airport": "flight_count"}),
        out_dir / "table_10_polish_airport_share.csv",
    )
    return {
        "status": "ok",
        "plot": str(plot_path),
        "table": str(table_path),
        "rows": int(subset.shape[0]),
        "metrics": counts.to_dict(),
    }


def chart_destination_share(df: pd.DataFrame, out_dir: Path, top_n: int = 8) -> Dict[str, object]:
    subset = df.dropna(subset=["destination_airport"])
    if subset.empty:
        return {"status": "skipped", "reason": "No destination data."}

    counts = subset["destination_airport"].value_counts()
    top = counts.head(top_n)
    other_count = counts.iloc[top_n:].sum()
    if other_count > 0:
        top = pd.concat([top, pd.Series({"Other": other_count})])

    labels = [_INTERNATIONAL_AIRPORT_NAMES.get(code, code) for code in top.index]

    n_named = len(top) - (1 if other_count > 0 else 0)
    colors = list(_PIE_COLORS[:n_named])
    if other_count > 0:
        colors.append("#cccccc")

    fig, ax = plt.subplots(figsize=(11, 11))
    wedges, texts, autotexts = ax.pie(
        top.values,
        labels=labels,
        autopct="%1.1f%%",
        startangle=140,
        pctdistance=0.78,
        colors=colors,
    )
    for at in autotexts:
        at.set_fontsize(9)
    ax.set_title(f"Most popular destinations (top {top_n})", pad=20)

    plot_path = _save_and_close(out_dir / "chart_11_destination_share.png")
    table_path = _save_table(
        counts.reset_index().rename(columns={"index": "airport", "destination_airport": "flight_count"}),
        out_dir / "table_11_destination_share.csv",
    )
    return {
        "status": "ok",
        "plot": str(plot_path),
        "table": str(table_path),
        "rows": int(subset.shape[0]),
        "metrics": counts.to_dict(),
    }


def chart_polish_airport_share_passengers(df: pd.DataFrame, out_dir: Path, top_n: int = 8) -> Dict[str, object]:
    from filter_flights import VALID_POLISH_AIRPORTS
    from flight_analytics.data import airport_passengers_2024

    polish_codes = [c for c in VALID_POLISH_AIRPORTS if c in airport_passengers_2024]
    if not polish_codes:
        return {"status": "skipped", "reason": "No passenger data for Polish airports."}

    counts = pd.Series({code: airport_passengers_2024[code] for code in polish_codes}).sort_values(ascending=False)
    top = counts.head(top_n)
    other_count = counts.iloc[top_n:].sum()
    if other_count > 0:
        top = pd.concat([top, pd.Series({"Other": other_count})])

    labels = [_POLISH_AIRPORT_NAMES.get(code, code) for code in top.index]
    n_named = len(top) - (1 if other_count > 0 else 0)
    colors = list(_PIE_COLORS[:n_named])
    if other_count > 0:
        colors.append("#cccccc")

    fig, ax = plt.subplots(figsize=(10, 10))
    wedges, texts, autotexts = ax.pie(
        top.values,
        labels=labels,
        autopct="%1.1f%%",
        startangle=140,
        pctdistance=0.78,
        colors=colors,
    )
    for at in autotexts:
        at.set_fontsize(9)
    ax.set_title("Share of passengers by Polish airport (2024)", pad=20)

    plot_path = _save_and_close(out_dir / "chart_13_polish_airport_share_passengers.png")
    return {
        "status": "ok",
        "plot": str(plot_path),
        "metrics": counts.to_dict(),
    }


def chart_destination_share_passengers(df: pd.DataFrame, out_dir: Path, top_n: int = 8) -> Dict[str, object]:
    from filter_flights import VALID_INTERNATIONAL_AIRPORTS
    from flight_analytics.data import airport_passengers_2024

    intl_codes = [c for c in VALID_INTERNATIONAL_AIRPORTS if c in airport_passengers_2024]
    if not intl_codes:
        return {"status": "skipped", "reason": "No passenger data for international airports."}

    counts = pd.Series({code: airport_passengers_2024[code] for code in intl_codes}).sort_values(ascending=False)
    top = counts.head(top_n)
    other_count = counts.iloc[top_n:].sum()
    if other_count > 0:
        top = pd.concat([top, pd.Series({"Other": other_count})])

    labels = [_INTERNATIONAL_AIRPORT_NAMES.get(code, code) for code in top.index]
    n_named = len(top) - (1 if other_count > 0 else 0)
    colors = list(_PIE_COLORS[:n_named])
    if other_count > 0:
        colors.append("#cccccc")

    fig, ax = plt.subplots(figsize=(11, 11))
    wedges, texts, autotexts = ax.pie(
        top.values,
        labels=labels,
        autopct="%1.1f%%",
        startangle=140,
        pctdistance=0.78,
        colors=colors,
    )
    for at in autotexts:
        at.set_fontsize(9)
    ax.set_title(f"Most popular international destinations by passengers (2024, top {top_n})", pad=20)

    plot_path = _save_and_close(out_dir / "chart_14_destination_share_passengers.png")
    return {
        "status": "ok",
        "plot": str(plot_path),
        "metrics": counts.to_dict(),
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
    table_path = _save_table(grouped, out_dir / "table_08_co2_efficiency_destinations.csv")
    return {
        "status": "ok",
        "plot": str(plot_path),
        "table": str(table_path),
        "rows": len(grouped),
        "metrics": {
            "destinations": int(len(grouped)),
            "best_destination": str(grouped.iloc[0]["destination_airport"]) if not grouped.empty else None,
            "best_avg_co2_per_100km": float(grouped.iloc[0]["avg_co2_per_100km"]) if not grouped.empty else np.nan,
        },
    }