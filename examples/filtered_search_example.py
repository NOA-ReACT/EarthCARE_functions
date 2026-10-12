
import sys
from pathlib import Path
from functools import partial

sys.path.append(
    str(Path(__file__).resolve().parent.parent / "src")
)

from filtered_search import (
    search_filtered,
    filter_consecutive_profiles,
)


# Define the filter
my_filter = partial(
    filter_consecutive_profiles,
    excluded_classes=[2, 3, 4, 5, 6, 7, 9, 10, 11, 12, 13, 14, 15, 16, 17, 19, 22, 23, 24, 25],
    min_consecutive=22,
)


# Search and apply the filter
df = search_filtered(
    product="AC__TC__2B",
    filter_fn=my_filter,
    version="ba",
    datetime=[
        "2025-01-01T00:00:00Z",
        "2025-01-31T23:59:59Z",
    ],
    bbox=[-11.0, 29.0, 40.0, 47.0],
    max_items=3,
    credentials_path="........................................./credentials.txt",
    output_csv="output/filtered_results.csv",
)

# print(df.head())
