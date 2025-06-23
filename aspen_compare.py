import os
import re

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

def highlight_diff(line1, line2):
    diff = []
    for c1, c2 in zip(line1, line2):
        diff.append("^" if c1 != c2 else " ")
    max_len = max(len(line1), len(line2))
    return line1.ljust(max_len), line2.ljust(max_len), "".join(diff).ljust(max_len)

def compare_blocks(block1, block2):
    diffs = []
    max_len = max(len(block1), len(block2))
    for i in range(max_len):
        l1 = block1[i] if i < len(block1) else ""
        l2 = block2[i] if i < len(block2) else ""
        if l1 != l2:
            l1_disp, l2_disp, diff = highlight_diff(l1, l2)
            diffs.append((i+1, l1_disp, l2_disp, diff))
    return diffs

def find_matching_pairs(directory):
    acs_files = [f for f in os.listdir(directory) if f.startswith("AR2025-") and f.endswith(".WMO")]
    avaps_files = [f for f in os.listdir(directory) if f.startswith("D") and f.endswith("_P.WMO")]

    pairs = []

    for acs in acs_files:
        match = re.search(r'AR2025-\d{8}N\d-\d{2}-(\d{8}T\d{6})-\d\.WMO', acs)
        if not match:
            continue
        timestamp = match.group(1)  # e.g., 20250123T203710
        avaps_name = f"D{timestamp[:8]}_{timestamp[9:15]}_P.WMO"
        if avaps_name in avaps_files:
            pairs.append((os.path.join(directory, acs), os.path.join(directory, avaps_name)))
    return pairs

def main(directory, output_file="comparison_report.txt"):
    total = 0
    no_diff = 0
    pairs = find_matching_pairs(directory)
    if not pairs:
        print("No matching file pairs found.")
        return

    with open(output_file, 'w', encoding='utf-8') as out:
        for file1, file2 in pairs:
            base1 = os.path.basename(file1)
            base2 = os.path.basename(file2)
            print(f"\nFound ACS file:    {base1}")
            print(f"Found matching AVAPS file: {base2}")
            out.write(f"Comparing:\n  ACS:   {base1}\n  AVAPS: {base2}\n\n")

            xxaa1 = extract_xxaa_block(file1)
            xxaa2 = extract_xxaa_block(file2)
            diffs = compare_blocks(xxaa1, xxaa2)
            total += 1

            if not diffs:
                no_diff += 1
                print("No differences found in XXAA.")
                out.write("  -> No differences found.\n\n")
            else:
                print(f"{len(diffs)} differences found in XXAA.")
                for line_num, l1, l2, diff in diffs:
                    out.write(f"  Line {line_num}:\n")
                    out.write(f"    File1: {l1}\n")
                    out.write(f"    File2: {l2}\n")
                    out.write(f"           {diff}\n\n")

            out.write("=" * 60 + "\n\n")
            print(f"Moving to next file...\n{'-' * 50}")

    print("\nComparison complete.")
    print(f"Compared {total} file pairs: {no_diff} had no differences, {total - no_diff} had differences.")



if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python compare_wmo_directory.py <directory>")
    else:
        main(sys.argv[1])