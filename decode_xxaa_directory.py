import os
import re
import csv
import sys
import time

def extract_xxaa_block(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()

    block = []
    in_xxaa = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("XXAA"):
            in_xxaa = True
            block.append(stripped)
            continue
        if in_xxaa:
            if stripped.startswith(("XX", "31313", "62626", "61616", "6 REL")) or not stripped:
                break
            block.append(stripped)

    return block

def decode_group(group):
    try:
        pressure_code = group[:2]
        height = int(group[2:])
        pressure_map = {
            "00": 1000, "92": 925, "85": 850, "70": 700,
            "50": 500, "40": 400, "30": 300, "25": 250
        }
        pressure = pressure_map.get(pressure_code, None)
        return (pressure, height)
    except:
        return (None, None)

def decode_temp_dew(group):
    try:
        temp = int(group[:3]) / 10.0
        dew = int(group[3:]) / 10.0
        return (temp, dew)
    except:
        return (None, None)

def decode_wind(group):
    try:
        dir = int(group[:3])
        spd = int(group[3:])
        return (dir, spd)
    except:
        return (None, None)

def extract_drop_time(filename):
    # Try both AR2025-20250123N1-06-20250123T203710-5.WMO and D20250123_203710_P.WMO formats
    match1 = re.search(r'(\d{8})[T_](\d{6})', filename)
    if match1:
        return f"{match1.group(1)}_{match1.group(2)}"
    return None

def decode_xxaa_block(block):
    data = ' '.join(block)
    chunks = re.findall(r'\d{5}', data)

    if len(chunks) < 1:
        return None

    meta = chunks.pop(0)
    try:
        day_of_month = int(meta[:2]) % 50
        hour_gmt = int(meta[2:4])
        wind_indicator = int(meta[4])
    except:
        day_of_month = hour_gmt = wind_indicator = None

    lat = lon = marsden = units = None
    if chunks and chunks[0].startswith("99"):
        try:
            pos1 = chunks.pop(0)
            pos2 = chunks.pop(0)
            lat = int(pos1[2:]) / 10.0
            octant = int(pos2[0])
            lon = int(pos2[1:]) / 10.0
            pos3 = chunks.pop(0)
            marsden = int(pos3[:3])
            units = int(pos3[3:])
        except:
            lat = lon = marsden = units = None

    pressure_data = {}
    surface_pressure_key = None

    if chunks and chunks[0].startswith("99"):
        try:
            surface = chunks.pop(0)
            surface_pressure = int(surface[2:])
            surface_pressure_key = f"SFC_{surface_pressure}"
            temp_dew = chunks.pop(0)
            wind = chunks.pop(0)
            temp, dew_dep = decode_temp_dew(temp_dew)
            wind_dir, wind_spd = decode_wind(wind)
            pressure_data[surface_pressure_key] = (None, temp, dew_dep, wind_dir, wind_spd)
        except:
            pass

    for i in range(0, len(chunks), 3):
        group = chunks[i:i+3]
        if len(group) == 3:
            pressure, height = decode_group(group[0])
            temp, dew_dep = decode_temp_dew(group[1])
            wind_dir, wind_spd = decode_wind(group[2])
            if pressure:
                pressure_data[pressure] = (height, temp, dew_dep, wind_dir, wind_spd)

    result = {
        'day_of_month': day_of_month,
        'hour_gmt': hour_gmt,
        'wind_indicator': wind_indicator,
        'latitude': lat,
        'longitude': lon,
        'marsden': marsden,
        'units': units,
    }

    if surface_pressure_key and surface_pressure_key in pressure_data:
        vals = pressure_data[surface_pressure_key]
        result[f"surface_pressure_mb"] = int(surface_pressure_key.split('_')[1])
        result[f"surface_temp_C"] = vals[1]
        result[f"surface_dewpt_dep_C"] = vals[2]
        result[f"surface_wind_dir_deg"] = vals[3]
        result[f"surface_wind_spd_kt"] = vals[4]

    for p in [1000, 925, 850, 700, 500, 400, 300, 250]:
        vals = pressure_data.get(p, (None, None, None, None, None))
        result[f"{p}_height_m"] = vals[0]
        result[f"{p}_temp_C"] = vals[1]
        result[f"{p}_dewpt_dep_C"] = vals[2]
        result[f"{p}_wind_dir_deg"] = vals[3]
        result[f"{p}_wind_spd_kt"] = vals[4]
    return result

def decode_directory_to_csv(directory, output_csv="decoded_xxaa.csv"):
    files = [f for f in os.listdir(directory) if f.endswith(".WMO")]
    total_files = len(files)
    print(f"Found {total_files} files for processing.")
    records = []
    max_filename_length = max((len(f) for f in files), default=0)
    for i, f in enumerate(files, 1):
        print(f"\rProcessing file {i} of {total_files}: {f.ljust(max_filename_length)}", end='', flush=True)
        file_path = os.path.join(directory, f)
        block = extract_xxaa_block(file_path)
        if block:
            decoded = decode_xxaa_block(block)
            if decoded:
                decoded['filename'] = f
                decoded['drop_time'] = extract_drop_time(f)
                records.append(decoded)
    print()
    if records:
        fieldnames = ['filename', 'drop_time', 'day_of_month', 'hour_gmt', 'wind_indicator', 'latitude', 'longitude', 'marsden', 'units',
                      'surface_pressure_mb', 'surface_temp_C', 'surface_dewpt_dep_C', 'surface_wind_dir_deg', 'surface_wind_spd_kt']
        for p in [1000, 925, 850, 700, 500, 400, 300, 250]:
            fieldnames += [
                f"{p}_height_m", f"{p}_temp_C", f"{p}_dewpt_dep_C",
                f"{p}_wind_dir_deg", f"{p}_wind_spd_kt"
            ]
        with open(output_csv, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)
        print(f"Wrote {len(records)} lines to {output_csv}.")
    else:
        print("No XXAA data decoded.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python decode_xxaa_directory.py <directory>")
    else:
        decode_directory_to_csv(sys.argv[1])
