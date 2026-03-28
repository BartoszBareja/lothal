import json
import pandas as pd
import matplotlib.pyplot as plt
import os

# Tworzenie katalogu wyjściowego
if not os.path.exists('output'):
    os.makedirs('output')

def process_and_plot_refined(json_file):
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Budowanie bazy informacji o lotniskach
    airport_info = {}
    for result in data.get('results', []):
        for group in result.get('airports', []):
            for side in ['arrival', 'departure']:
                for item in group.get(side, []):
                    aid = item.get('airport', {}).get('id')
                    if aid:
                        airport_info[aid] = {
                            'city': item.get('city', 'Nieznane')
                        }

    target_airports = [
        "MAD", "BCN", "PMI", "ATH", "HER", "RHO", "LIS",
        "OPO", "FAO", "LHR", "LGW", "MAN", "ARN", "GOT",
        "MMX", "AMS", "EIN", "RTM", "JFK", "LAX", "ORD",
        "CAI", "HRG", "SSH", "AMM", "CPH", "BLL", "FRA"
    ]

    all_flights = []
    for result in data.get('results', []):
        ret_date = result.get('return_date', 'N/A')
        for cat in ['best_flights', 'other_flights']:
            for offer in result.get(cat, []):
                # Tylko loty w dwie strony
                if offer.get('type') != 'Round trip':
                    continue
                    
                price = offer.get('price')
                segments = offer.get('flights', [])
                if not segments or price is None:
                    continue
                
                first_seg = segments[0]
                last_seg = segments[-1]
                dest_id = last_seg['arrival_airport']['id']
                
                if dest_id in target_airports:
                    dep_id = first_seg['departure_airport']['id']
                    all_flights.append({
                        'dest_id': dest_id,
                        'price': price,
                        'airline': first_seg.get('airline', 'N/A'),
                        'dep_city': airport_info.get(dep_id, {}).get('city', dep_id),
                        'dest_city': airport_info.get(dest_id, {}).get('city', dest_id),
                        'dep_time': first_seg['departure_airport']['time'],
                        'arr_time': last_seg['arrival_airport']['time'],
                        'return_date': ret_date
                    })

    df = pd.DataFrame(all_flights)
    
    for aid in target_airports:
        subset = df[df['dest_id'] == aid]
        if subset.empty:
            continue
        
        top_3 = subset.sort_values('price').head(3)
        
        plt.figure(figsize=(14, 8))
        x_labels = []
        for _, row in top_3.iterrows():
            label = (f"{row['dep_city']} -> {row['dest_city']}\n"
                     f"{row['airline']}\n"
                     f"Wylot: {row['dep_time']}\n"
                     f"Przylot: {row['arr_time']}\n"
                     f"Powrót: {row['return_date']}")
            x_labels.append(label)
        
        bars = plt.bar(x_labels, top_3['price'], color='lightcoral', edgecolor='maroon')
        plt.ylabel('Cena za lot w dwie strony (PLN)')
        plt.title(f'3 Najtańsze loty (Round Trip) do: {aid} ({airport_info.get(aid, {}).get("city", "")})')
        
        for bar in bars:
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5, 
                     f"{int(bar.get_height())} PLN", ha='center', va='bottom', fontweight='bold')
        
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        plt.savefig(f"output/roundtrip_{aid}.png")
        plt.close()

process_and_plot_refined('flights_20260314.json')