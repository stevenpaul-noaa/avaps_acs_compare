import pandas as pd
import argparse
import os
from glob import glob
from collections import defaultdict

# Thresholds for differences
THRESHOLDS = {
    'AVAPS - ACS Pressure': 1.0,         # hPa
    'AVAPS - ACS Temperature': 0.2,      # °C
    'AVAPS - ACS Humidity': 5.0,         # %
    'AVAPS - ACS WindSpeed': 1.0,        # m/s
    'AVAPS - ACS WindDirection': 1.0     # degrees
}

def analyze_file(csv_path, global_data):
    df = pd.read_csv(csv_path)
    summary_lines = [f"\n=== File: {os.path.basename(csv_path)} ===\n"]

    for column, threshold in THRESHOLDS.items():
        if column not in df.columns:
            summary_lines.append(f"{column}: Column missing.\n")
            continue

        values = pd.to_numeric(df[column], errors='coerce').dropna()
        total = len(values)

        if total == 0:
            summary_lines.append(f"{column}: No valid data.\n")
            continue

        global_data[column].extend(values.tolist())  # accumulate globally

        within_threshold = (values.abs() <= threshold).sum()
        pct_within = 100 * within_threshold / total

        summary_lines.append(f"{column}:\n")
        summary_lines.append(f"  Total values        : {total}\n")
        summary_lines.append(f"  Mean difference     : {values.mean():.4f}\n")
        summary_lines.append(f"  Min/Max difference  : {values.min():.4f} / {values.max():.4f}\n")
        summary_lines.append(f"  Std dev             : {values.std():.4f}\n")
        summary_lines.append(f"  Within threshold    : {within_threshold} ({pct_within:.1f}%)\n\n")

    return "".join(summary_lines)

def write_global_summary(global_data, file_count):
    lines = [f"\n=== GLOBAL SUMMARY ACROSS {file_count} FILE(S) ===\n"]

    for column, threshold in THRESHOLDS.items():
        values = pd.to_numeric(global_data[column], errors='coerce')
        values = pd.Series(values).dropna()
        total = len(values)

        if total == 0:
            lines.append(f"{column}: No valid data.\n")
            continue

        within_threshold = (values.abs() <= threshold).sum()
        pct_within = 100 * within_threshold / total

        lines.append(f"{column}:\n")
        lines.append(f"  Total values        : {total}\n")
        lines.append(f"  Mean difference     : {values.mean():.4f}\n")
        lines.append(f"  Min/Max difference  : {values.min():.4f} / {values.max():.4f}\n")
        lines.append(f"  Std dev             : {values.std():.4f}\n")
        lines.append(f"  Within threshold    : {within_threshold} ({pct_within:.1f}%)\n\n")

    return "".join(lines)

def process_directory(directory):
    csv_files = sorted(glob(os.path.join(directory, "*.csv")))
    if not csv_files:
        print(f"No CSV files found in: {directory}")
        return

    global_data = defaultdict(list)
    summary_output = []

    for csv_file in csv_files:
        file_summary = analyze_file(csv_file, global_data)
        summary_output.append(file_summary)

    # Add global summary
    global_summary = write_global_summary(global_data, len(csv_files))
    summary_output.append(global_summary)

    # Write to file
    summary_path = os.path.join(directory, "avaps_acs_summary.txt")
    with open(summary_path, "w") as f:
        f.writelines(summary_output)

    print(f"Summary written to: {summary_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process AVAPS vs ACS CSV files in a directory and write summary.")
    parser.add_argument("directory", help="Path to the directory containing CSV files")
    args = parser.parse_args()

    process_directory(args.directory)
