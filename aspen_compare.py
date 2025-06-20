import sys
import difflib

def extract_xxaa_block(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()

    in_xxaa = False
    block = []

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("XXAA"):
            in_xxaa = True
            block.append(stripped)
            continue

        if in_xxaa:
            # Stop if we hit a new section code or something clearly not part of XXAA
            if (stripped.startswith(("XX", "31313", "62626", "61616", "6 REL")) or
                stripped == "" or
                not any(char.isdigit() for char in stripped)):
                break

            block.append(stripped)

    return block


def highlight_diff(line1, line2):
    diff = []
    for c1, c2 in zip(line1, line2):
        diff.append("^" if c1 != c2 else " ")
    # Pad the shorter line
    max_len = max(len(line1), len(line2))
    line1 = line1.ljust(max_len)
    line2 = line2.ljust(max_len)
    diff_line = "".join(diff).ljust(max_len)
    return line1, line2, diff_line

def compare_blocks(block1, block2):
    max_len = max(len(block1), len(block2))
    print("Comparing XXAA Mandatory Levels:\n")

    for i in range(max_len):
        l1 = block1[i] if i < len(block1) else ""
        l2 = block2[i] if i < len(block2) else ""

        if l1 != l2:
            print(f"Line {i+1}:")
            l1_disp, l2_disp, diff = highlight_diff(l1, l2)
            print(f"  File1: {l1_disp}")
            print(f"  File2: {l2_disp}")
            print(f"         {diff}\n")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python compare_xxaa.py file1.txt file2.txt")
        sys.exit(1)

    file1 = sys.argv[1]
    file2 = sys.argv[2]

    xxaa1 = extract_xxaa_block(file1)
    xxaa2 = extract_xxaa_block(file2)

    compare_blocks(xxaa1, xxaa2)
