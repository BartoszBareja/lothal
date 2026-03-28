import json
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import itertools
import os

def plot_scatter_with_shapes(json_file):
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    target_airports = [
        "MAD", "BCN", "PMI", "ATH", "HER", "RHO", "LIS",
        "OPO", "FAO", "LHR", "LGW", "MAN", "ARN", "GOT",
        "MMX", "AMS", "EIN", "RTM", "JFK", "LAX", "ORD",
        "CAI", "HRG", "SSH", "AMM", "CPH", "BLL", "FRA"
    ]

    entries = []
    for result in data.get('results', []):
        out_date = result.get('outbound_date')
        if not out_date: continue
        for cat in ['best_flights', 'other_flights']:
            for offer in result.get(cat, []):
                if offer.get('type') != 'Round trip': continue
                price = offer.get('price')
                flights = offer.get('flights', [])
                if not flights or price is None: continue
                dest_id = flights[-1]['arrival_airport']['id']
                if dest_id in target_airports:
                    entries.append({'date': out_date, 'dest': dest_id, 'price': price})

    df = pd.DataFrame(entries)
    if df.empty: return

    # Agregacja: najtańszy lot na dzień
    df_agg = df.groupby(['date', 'dest'])['price'].min().reset_index()
    df_agg['date'] = pd.to_datetime(df_agg['date'])

    # Definicja listy dostępnych kształtów
    marker_list = ['o', 'v', '^', '<', '>', '8', 's', 'p', '*', 'h', 'H', 'D', 'd', 'P', 'X']
    marker_cycle = itertools.cycle(marker_list)

    plt.figure(figsize=(16, 10))
    
    # Rysowanie punktów z przypisaniem unikalnego kształtu
    for dest_id in sorted(df_agg['dest'].unique()):
        subset = df_agg[df_agg['dest'] == dest_id]
        plt.scatter(subset['date'], subset['price'], 
                    label=dest_id, 
                    s=80, 
                    marker=next(marker_cycle), 
                    alpha=0.8)

    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.gca().xaxis.set_major_locator(mdates.DayLocator())
    
    plt.xlabel('Data wylotu')
    plt.ylabel('Minimalna cena (PLN)')
    plt.title('Najniższe dzienne ceny lotów (Round Trip) - Różne Kształty Punktów')
    
    plt.legend(title='Destynacja', bbox_to_anchor=(1.02, 1), loc='upper left', ncol=2)
    plt.grid(True, linestyle='--', alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    if not os.path.exists('output'):
        os.makedirs('output')
        
    plt.savefig('output/cheapest_daily_scatter_shapes.png')
    plt.close()

plot_scatter_with_shapes('flights_20260314.json')