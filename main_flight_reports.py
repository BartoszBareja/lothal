from pathlib import Path
from typing import Callable, Dict

from flight_analytics.charts import (
    chart_cheapest_routes,
    chart_co2_efficiency_by_destination,
    chart_co2_vs_price,
    chart_daily_trend,
    chart_destination_boxplot,
    chart_price_heatmap,
    chart_price_histogram,
    chart_price_vs_distance,
)
from flight_analytics.data import clean_results, flatten_flights, load_data


OUTPUT_DIR = Path("output")
DEFAULT_INPUT = Path("flights_20260315.json")


def ask_yes_no(prompt: str, default: bool = True) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    answer = input(f"{prompt} {suffix}: ").strip().lower()
    if not answer:
        return default
    return answer in {"y", "yes", "t", "true", "1"}


def print_menu() -> None:
    print("\n=== Flight Analytics Menu ===")
    print("1. Top cheapest routes (bar chart)")
    print("2. Daily min-price trend by destination")
    print("3. Price distribution histogram")
    print("4. Destination price boxplot")
    print("5. Heatmap: min price by date x destination")
    print("6. Price vs distance with regression")
    print("7. CO2 vs price")
    print("8. CO2 efficiency by destination")
    print("9. Generate all charts")
    print("0. Exit")


def run() -> None:
    print("Flight analytics generator")
    path_input = input(f"Input JSON file [{DEFAULT_INPUT}]: ").strip()
    input_path = Path(path_input) if path_input else DEFAULT_INPUT

    if not input_path.exists():
        print(f"Error: file does not exist: {input_path}")
        return

    do_clean = ask_yes_no("Run cleaning step with filter rules?", default=True)

    data = load_data(input_path)
    cleaning_stats = None
    if do_clean:
        data, cleaning_stats = clean_results(data)
        print("Cleaning complete.")

    df = flatten_flights(data)
    if df.empty:
        print("No flights available after preprocessing.")
        return

    OUTPUT_DIR.mkdir(exist_ok=True)
    chart_results: Dict[str, Dict[str, object]] = {}

    chart_funcs: Dict[str, tuple[str, Callable[..., Dict[str, object]]]] = {
        "1": ("cheapest_routes", chart_cheapest_routes),
        "2": ("daily_trend", chart_daily_trend),
        "3": ("price_histogram", chart_price_histogram),
        "4": ("destination_boxplot", chart_destination_boxplot),
        "5": ("price_heatmap", chart_price_heatmap),
        "6": ("price_vs_distance", chart_price_vs_distance),
        "7": ("co2_vs_price", chart_co2_vs_price),
        "8": ("co2_efficiency_destinations", chart_co2_efficiency_by_destination),
    }

    while True:
        print_menu()
        choice = input("Select option: ").strip()

        if choice == "0":
            break

        if choice in chart_funcs:
            chart_name, fn = chart_funcs[choice]
            result = fn(df, OUTPUT_DIR)
            chart_results[chart_name] = result
            print(f"[{chart_name}] {result}")
            continue

        if choice == "9":
            for chart_name, fn in chart_funcs.values():
                result = fn(df, OUTPUT_DIR)
                chart_results[chart_name] = result
                print(f"[{chart_name}] {result}")
            print("All chart tasks finished.")
            continue

        print("Invalid option.")

    print("\nDone.")
    print(f"Rows analyzed: {len(df)}")


if __name__ == "__main__":
    run()
