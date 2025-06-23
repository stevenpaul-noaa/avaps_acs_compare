import csv
import sys
from collections import defaultdict

def load_csv_data(csv_file):
    data = defaultdict(dict)
    with open(csv_file, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            filename = row['filename']
            drop_time = row['drop_time']
            if filename.startswith("AR2025"):
                key = ("ACS", drop_time)
            elif filename.startswith("D"):
                key = ("AVAPS", drop_time)
            else:
                continue
            data[key] = row
    return data

def compare_rows(acs_row, avaps_row, fields, thresholds):
    diffs = []
    tolerated_diffs = 0
    exceed_diffs = 0
    for field in fields:
        acs_val = acs_row.get(field)
        avaps_val = avaps_row.get(field)

        if not acs_val or not avaps_val:
            continue  # Skip if either value is blank

        try:
            acs_num = float(acs_val)
            avaps_num = float(avaps_val)
            diff = abs(acs_num - avaps_num)
            if diff > thresholds.get(field, 0):
                diffs.append((field, acs_val, avaps_val, diff, False))
                exceed_diffs += 1
            else:
                diffs.append((field, acs_val, avaps_val, diff, True))
                tolerated_diffs += 1
        except:
            if acs_val != avaps_val:
                diffs.append((field, acs_val, avaps_val, None, False))
                exceed_diffs += 1
    return diffs, tolerated_diffs, exceed_diffs

def main(csv_file):
    data = load_csv_data(csv_file)
    matched_times = set(k[1] for k in data.keys() if k[0] == "ACS")
    fields_to_compare = [
        'latitude', 'longitude', 'marsden', 'units',
        'surface_temp_C', 'surface_dewpt_dep_C', 'surface_wind_dir_deg', 'surface_wind_spd_kt'
    ]
    for p in [1000, 925, 850, 700, 500, 400, 300, 250]:
        fields_to_compare += [
            f"{p}_height_m", f"{p}_temp_C", f"{p}_dewpt_dep_C",
            f"{p}_wind_dir_deg", f"{p}_wind_spd_kt"
        ]

    # Define field-specific thresholds
    thresholds = {
        'latitude': 0.2,
        'longitude': 0.2,
        'surface_temp_C': 1,
        'surface_dewpt_dep_C': 1,
        'surface_wind_dir_deg': 5,
        'surface_wind_spd_kt': 2.7,
    }
    for p in [1000, 925, 850, 700, 500, 400, 300, 250]:
        thresholds.update({
            f"{p}_height_m": 20,
            f"{p}_temp_C": 1,
            f"{p}_dewpt_dep_C": 1,
            f"{p}_wind_dir_deg": 5,
            f"{p}_wind_spd_kt": 2.7,
        })

    total = 0
    matched = 0
    all_within_tolerance = 0
    had_exceedances = 0
    exceeded_drops = []

    with open("csv_comparison_report.txt", "w") as out:
        for drop_time in matched_times:
            acs_key = ("ACS", drop_time)
            avaps_key = ("AVAPS", drop_time)
            total += 1
            if acs_key in data and avaps_key in data:
                matched += 1
                diffs, tolerated_diffs, exceed_diffs = compare_rows(data[acs_key], data[avaps_key], fields_to_compare, thresholds)
                if exceed_diffs == 0:
                    all_within_tolerance += 1
                else:
                    had_exceedances += 1
                    exceeded_drops.append(drop_time)

                out.write(f"Comparing drop_time {drop_time} (ACS: {data[acs_key]['filename']} vs AVAPS: {data[avaps_key]['filename']}):\n")
                if diffs:
                    for field, a, b, diff, tolerated in diffs:
                        if a != b:
                            note = "(within tolerance)" if tolerated else "(EXCEEDS tolerance)"
                            diff_str = f" diff={diff:.2f}" if diff is not None else ""
                            out.write(f"  {field}: ACS = {a}, AVAPS = {b}{diff_str} {note}\n")
                else:
                    out.write("  -> No differences found.\n")
                out.write("\n")

        out.write(f"Summary: {total} ACS entries processed, {matched} had matching AVAPS files.\n")
        out.write(f"         {all_within_tolerance} file pairs had only tolerated differences or none at all.\n")
        out.write(f"         {had_exceedances} file pairs had one or more differences that exceeded tolerances.\n")
        if exceeded_drops:
            out.write("\nList of drop_times with exceeded tolerances (sorted):\n")
            for drop in sorted(exceeded_drops):
                out.write(f"  {drop}\n")

    print("Comparison complete. See 'csv_comparison_report.txt'.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python compare_csv_data.py <decoded_csv_file>")
    else:
        main(sys.argv[1])
