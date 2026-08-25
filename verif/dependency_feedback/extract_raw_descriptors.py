#!/usr/bin/env python3

"""Convert full RAW-checker vectors into compact, explainable descriptors."""

import argparse
import csv
from collections import Counter
from pathlib import Path


SCOREBOARD_ENTRIES = 8
REGISTER_BITS = 5


def occupancy_bin(occupancy):
    """Group occupancy so a monitor needs only four coverage bins."""
    if occupancy == 0:
        return "empty"
    if occupancy <= 2:
        return "low_1_2"
    if occupancy <= 4:
        return "medium_3_4"
    return "high_5_8"


def age_bin(age):
    """Keep nearby producers precise and merge older producer positions."""
    if age == 0:
        return "newest_0"
    if age == 1:
        return "next_1"
    if age <= 3:
        return "middle_2_3"
    return "old_4_7"


def match_bin(matches):
    """Separate no match, one producer, and an overwrite chain."""
    if matches == 0:
        return "none_0"
    if matches == 1:
        return "single_1"
    return "multiple_2_plus"


def scoreboard_register(rd_flat, entry):
    """Read one five-bit destination from the flat eight-entry scoreboard."""
    shift = entry * REGISTER_BITS
    return (rd_flat >> shift) & ((1 << REGISTER_BITS) - 1)


def describe(row):
    """Derive descriptors from one exact RAW-checker evaluation."""
    source = int(row["rs"], 16)
    source_is_fpr = int(row["rs_fpr"])
    rd_flat = int(row["rd_flat"], 16)
    rd_fpr = int(row["rd_fpr"], 16)
    live = int(row["still_issued"], 16)
    pointer = int(row["issue_pointer"], 16)
    producer = int(row["expected_idx"], 16)
    raw_valid = int(row["expected_valid"])

    # Count live entries before grouping the value into a compact bin.
    occupancy = live.bit_count()

    # Recreate every register/type match, not only the newest selected match.
    matches = 0
    for entry in range(SCOREBOARD_ENTRIES):
        entry_is_live = (live >> entry) & 1
        entry_is_fpr = (rd_fpr >> entry) & 1
        same_register = scoreboard_register(rd_flat, entry) == source
        matches += entry_is_live and entry_is_fpr == source_is_fpr and same_register

    # Integer x0 is hardwired to zero and cannot depend on a producer.
    if source == 0 and source_is_fpr == 0:
        matches = 0

    # Catch trace-decoding mistakes before they can contaminate the analysis.
    if raw_valid != int(matches > 0):
        raise ValueError(
            f"RAW-valid disagrees with reconstructed matches at cycle {row['cycle']}"
        )

    if raw_valid:
        # The issue pointer names the next insertion slot. Pointer-1 is newest.
        producer_age = (pointer - 1 - producer) % SCOREBOARD_ENTRIES
        producer_age_bin = age_bin(producer_age)

        # An index at/above the pointer comes from the wrapped scoreboard side.
        wrap_selection = int(producer >= pointer)
    else:
        producer_age = -1
        producer_age_bin = "none"
        wrap_selection = -1

    descriptor = {
        "cycle": row["cycle"],
        "issue_port": row["issue_port"],
        "operand": row["operand"],
        "pc": row["pc"],
        "occupancy": occupancy,
        "occupancy_bin": occupancy_bin(occupancy),
        "raw_valid": raw_valid,
        "producer_age": producer_age,
        "producer_age_bin": producer_age_bin,
        "matching_producers": matches,
        "matching_producers_bin": match_bin(matches),
        "wrap_selection": wrap_selection,
    }

    # This tuple is a candidate visited-bin address for a future monitor.
    descriptor["context_bin"] = "|".join([
        descriptor["occupancy_bin"],
        f"raw_{raw_valid}",
        descriptor["producer_age_bin"],
        descriptor["matching_producers_bin"],
        f"wrap_{wrap_selection}",
    ])
    return descriptor


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    args = parser.parse_args()

    with args.input.open(newline="") as source:
        descriptors = [describe(row) for row in csv.DictReader(source)]
    if not descriptors:
        raise SystemExit(f"No vectors in {args.input}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=descriptors[0].keys())
        writer.writeheader()
        writer.writerows(descriptors)

    # Emit one tidy count table so treatments can be compared with basic tools.
    counts = Counter()
    for item in descriptors:
        for descriptor_name in (
            "occupancy_bin", "raw_valid", "producer_age_bin",
            "matching_producers_bin", "wrap_selection", "context_bin",
        ):
            counts[(descriptor_name, str(item[descriptor_name]))] += 1

    args.summary.parent.mkdir(parents=True, exist_ok=True)
    with args.summary.open("w", newline="") as target:
        fields = ["descriptor", "bin", "count"]
        writer = csv.DictWriter(target, fieldnames=fields)
        writer.writeheader()
        for (name, value), count in sorted(counts.items()):
            writer.writerow({"descriptor": name, "bin": value, "count": count})

    print(f"{args.output}: {len(descriptors)} descriptor rows")
    print(f"{args.summary}: {len(counts)} populated bins")


if __name__ == "__main__":
    main()
