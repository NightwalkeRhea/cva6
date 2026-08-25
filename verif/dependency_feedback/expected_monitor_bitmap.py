#!/usr/bin/env python3

"""Calculate the monitor bitmap independently from a RAW-checker CSV trace."""

import argparse
import csv
from pathlib import Path


def raw_matches(row):
    """Reconstruct the eight match bits that already exist inside raw_checker."""
    source = int(row["rs"], 16)
    source_is_fpr = int(row["rs_fpr"])
    destinations = int(row["rd_flat"], 16)
    destination_types = int(row["rd_fpr"], 16)
    live = int(row["still_issued"], 16)
    matches = 0

    for entry in range(8):
        destination = (destinations >> (entry * 5)) & 0x1F
        destination_is_fpr = (destination_types >> entry) & 1
        same_register = destination == source
        same_type = destination_is_fpr == source_is_fpr
        if ((live >> entry) & 1) and same_register and same_type:
            matches |= 1 << entry

    # Match the official checker rule: integer x0 never creates a RAW.
    if source == 0 and source_is_fpr == 0:
        matches = 0
    return matches


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("trace", type=Path)
    args = parser.parse_args()
    bitmap = 0

    with args.trace.open(newline="") as source:
        for row in csv.DictReader(source):
            # Skip operands that do not participate in this issue attempt.
            if not int(row["operand_used"]):
                continue

            valid = int(row["expected_valid"])
            producer = int(row["expected_idx"], 16)
            pointer = int(row["issue_pointer"], 16)
            live_entries = int(row["still_issued"], 16).bit_count()
            matching_entries = raw_matches(row).bit_count()

            # Apply the same public bit specification without using the RTL.
            bitmap |= valid << 0
            bitmap |= (valid and matching_entries >= 2) << 1
            bitmap |= (valid and producer >= pointer) << 2
            bitmap |= (valid and producer < pointer) << 3
            bitmap |= (live_entries == 0) << 4
            bitmap |= (1 <= live_entries <= 2) << 5
            bitmap |= (3 <= live_entries <= 4) << 6
            bitmap |= (live_entries >= 5) << 7

    print(f"{bitmap:02x}")


if __name__ == "__main__":
    main()
