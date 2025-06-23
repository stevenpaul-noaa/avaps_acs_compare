import os
import re
import csv
import sys


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


def safe_int(s):
    try:
        return int(s)
    except:
        return None


def safe_float(s):
    try:
        return float(s)
    except:
        return None


def decode_group(group):
    pressure_map = {
        "00": 1000, "92": 925, "85": 850, "70": 700,
        "50": 500, "40": 400, "30": 300, "25": 250
    }
    if len(group) != 5 or not group[:2].isdigit():
        return (None, None)
    code = group[:2]
    height_str = group[2:]
    pressure = pressure_map.get(code)
    height = safe_int(height_str)
    if pressure in [1000] and height is not None and height >= 500:
        height = -1*(height-500)  # Convert values over 500 to negative height
    return (pressure, height)


def decode_temp_dew(group):
    if len(group) != 5 or group == "/////":
        return (None, None)
    temp_str = group[:3]
    dew_str = group[3:]
    if "///" in temp_str or "///" in dew_str:
        return (None, None)
    temp = safe_int(temp_str)
    dew = safe_int(dew_str)
    if temp is None or dew is None:
        return (None, None)
    return (temp / 10.0, dew / 10.0)


def decode_wind(group):
    if len(group) < 4 or "///" in group:
        return (None, None)
    dir_str = group[:3]
    spd_str = group[3:]
    dir_ = safe_int(dir_str)
    spd = safe_int(spd_str)
    return (dir_, spd)


def decode_surface_group(groups):
    if len(groups) < 3:
        return (None, None, None, None, None)
    p_group, td_group, wind_group = groups[:3]
    if len(p_group) != 5 or not p_group.startswith("99"):
        return (None, None, None, None, None)
    pressure = safe_int(p_group[2:])
    if pressure is None:
        return (None, None, None, None, None)
    temp, dew = decode_temp_dew(td_group)
    wdir, wspd = decode_wind(wind_group)
    return (pressure, temp, dew, wdir, wspd)


def extract_drop_time(filename):
    m = re.search(r'(\d{8})[T_](\d{6})', filename)
    if m:
        return f"{m.group(1)}_{m.group(2)}"
    return ""


def decode_xxaa_block(block):
    data_str = ' '.join(block)
    groups = re.findall(r'(?:\d{5}|/{5})', data_str)
    if not groups:
        return None

    meta = groups.pop(0)
    day_of_month = hour_gmt = wind_indicator = None
    try:
        day_of_month = int(meta[:2])
        if day_of_month > 50:
            day_of_month -= 50
        hour_gmt = int(meta[2:4])
        wind_indicator = int(meta[4])
    except:
        pass

    lat = lon = marsden = units = None
    if groups and groups[0].startswith("99"):
        try:
            pos1 = groups.pop(0)
            pos2 = groups.pop(0)
            pos3 = groups.pop(0)
            lat = safe_int(pos1[2:]) / 10.0
            lon = safe_int(pos2[1:]) / 10.0
            marsden = safe_int(pos3[:3])
            units = safe_int(pos3[3:])
        except:
            lat = lon = marsden = units = None

    surface_pressure = surface_temp = surface_dew = surface_wind_dir = surface_wind_spd = None
    if groups and groups[0].startswith("99"):
        surface_data = decode_surface_group(groups[:3])
        if surface_data[0] is not None:
            surface_pressure, surface_temp, surface_dew, surface_wind_dir, surface_wind_spd = surface_data
        groups = groups[3:]

    pressure_map = {
        "00": 1000, "92": 925, "85": 850, "70": 700,
        "50": 500, "40": 400, "30": 300, "25": 250
    }
    levels = {v: {'height': None, 'temp': None, 'dewpt': None, 'wind_dir': None, 'wind_spd': None} for v in pressure_map.values()}

    for i in range(0, len(groups), 3):
        level_groups = groups[i:i+3]
        if len(level_groups) < 3:
            break
        pcode, tempdew, wind = level_groups
        pressure, height = decode_group(pcode)
        if pressure is None:
            continue
        temp, dew = decode_temp_dew(tempdew)
        wdir, wspd = decode_wind(wind)
        levels[pressure] = {
            'height': height,
            'temp': temp,
            'dewpt': dew,
            'wind_dir': wdir,
            'wind_spd': wspd
        }

    result = {
        'day_of_month': day_of_month,
        'hour_gmt': hour_gmt,
        'wind_indicator': wind_indicator,
        'latitude': lat,
        'longitude': lon,
        'marsden': marsden,
        'units': units,
        'surface_pressure_mb': surface_pressure,
        'surface_temp_C': surface_temp,
        'surface_dewpt_dep_C': surface_dew,
        'surface_wind_dir_deg': surface_wind_dir,
        'surface_wind_spd_kt': surface_wind_spd
    }

    for p in sorted(levels.keys(), reverse=True):
        vals = levels[p]
        result[f"{p}_height_m"] = vals['height']
        result[f"{p}_temp_C"] = vals['temp']
        result[f"{p}_dewpt_dep_C"] = vals['dewpt']
        result[f"{p}_wind_dir_deg"] = vals['wind_dir']
        result[f"{p}_wind_spd_kt"] = vals['wind_spd']

    return result


def decode_directory_to_csv(directory, output_csv="decoded_xxaa.csv"):
    files = [f for f in os.listdir(directory) if f.endswith(".WMO")]
    total_files = len(files)
    print(f"Found {total_files} files for processing.")
    records = []
    max_filename_len = max((len(f) for f in files), default=0)

    for i, f in enumerate(files, 1):
        print(f"\rProcessing file {i} of {total_files}: {f.ljust(max_filename_len)}", end='', flush=True)
        file_path = os.path.join(directory, f)
        block = extract_xxaa_block(file_path)
        if not block:
            continue
        decoded = decode_xxaa_block(block)
        if decoded:
            decoded['filename'] = f
            decoded['drop_time'] = extract_drop_time(f)
            records.append(decoded)

    print()
    if not records:
        print("No XXAA data decoded.")
        return

    fieldnames = [
        'filename', 'drop_time', 'day_of_month', 'hour_gmt', 'wind_indicator',
        'latitude', 'longitude', 'marsden', 'units',
        'surface_pressure_mb', 'surface_temp_C', 'surface_dewpt_dep_C',
        'surface_wind_dir_deg', 'surface_wind_spd_kt'
    ]
    for p in sorted([1000, 925, 850, 700, 500, 400, 300, 250], reverse=True):
        fieldnames.extend([
            f"{p}_height_m", f"{p}_temp_C", f"{p}_dewpt_dep_C",
            f"{p}_wind_dir_deg", f"{p}_wind_spd_kt"
        ])

    with open(output_csv, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    print(f"Wrote {len(records)} lines to {output_csv}.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python decode_xxaa_directory.py <directory>")
    else:
        decode_directory_to_csv(sys.argv[1])
