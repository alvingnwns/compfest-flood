import csv
import json
import os
import random
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATASETS_DIR = BASE_DIR / "app" / "data" / "datasets"
ROADS_DIR = BASE_DIR / "app" / "data" / "roads"
OUTPUT_FILE = DATASETS_DIR / "synthetic_road_risk.csv"

def generate_synthetic_data(num_samples=1000):
    DATASETS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Base features configuration
    # We will generate a mix of primary, secondary, and arterial roads
    road_types = ["primary", "secondary", "arterial", "local"]
    
    with open(OUTPUT_FILE, "w", newline="") as csvfile:
        fieldnames = [
            "segment_id", "road_type", "length_km", "travel_time_minutes",
            "rainfall_mm", "hazard_score", "elevation_meters",
            "historical_flood_exposure", "drainage_pressure", "is_disrupted"
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for i in range(num_samples):
            road_type = random.choice(road_types)
            length_km = round(random.uniform(0.5, 15.0), 2)
            # travel time roughly based on length and type
            speed = {"primary": 40, "secondary": 30, "arterial": 50, "local": 20}[road_type]
            travel_time = round((length_km / speed) * 60 + random.uniform(-2, 5), 1)
            travel_time = max(1.0, travel_time)
            
            # Flood related features
            # A heavy rain event
            rainfall_mm = round(random.uniform(50, 250), 1)
            
            # Elevation is typically 0-30 meters in Jakarta
            elevation_meters = round(random.uniform(-1, 20), 1)
            
            # Historical exposure 0-1
            historical_exposure = round(random.uniform(0, 1), 2)
            
            # Drainage pressure is higher when rainfall is high and elevation is low
            base_pressure = (rainfall_mm / 250.0) + ((20 - elevation_meters) / 20.0)
            drainage_pressure = min(1.0, max(0.0, round(base_pressure * random.uniform(0.4, 0.6), 2)))
            
            # Hazard score is a function of rainfall, elevation, and historical exposure
            base_hazard = (rainfall_mm / 250.0) * 0.4 + (1.0 - (elevation_meters + 1) / 21.0) * 0.4 + historical_exposure * 0.2
            hazard_score = min(1.0, max(0.0, round(base_hazard + random.uniform(-0.1, 0.1), 2)))
            
            # Disruption Label Generation
            # If hazard is high, probability of disruption is high
            disruption_prob = hazard_score * 0.6 + drainage_pressure * 0.4
            
            is_disrupted = 1 if random.random() < disruption_prob else 0
            
            # Inject some outliers or deterministic rules to ensure model learns
            if hazard_score > 0.85 and drainage_pressure > 0.8:
                is_disrupted = 1
            if hazard_score < 0.2 and elevation_meters > 10:
                is_disrupted = 0
                
            writer.writerow({
                "segment_id": f"syn-road-{i:04d}",
                "road_type": road_type,
                "length_km": length_km,
                "travel_time_minutes": travel_time,
                "rainfall_mm": rainfall_mm,
                "hazard_score": hazard_score,
                "elevation_meters": elevation_meters,
                "historical_flood_exposure": historical_exposure,
                "drainage_pressure": drainage_pressure,
                "is_disrupted": is_disrupted
            })

    print(f"Generated {num_samples} synthetic road samples at {OUTPUT_FILE}")

if __name__ == "__main__":
    generate_synthetic_data()
