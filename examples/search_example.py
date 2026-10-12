
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

from search import Catalog, search_paired_products

catalog = Catalog()


# 1. General search using filters

items = catalog.search(
    product='ATL_EBD_2A' ,
    version= 'ba',
    datetime=[
        "2025-01-01T00:00:00Z",
        "2025-01-31T23:59:59Z",
    ],
)

print(f"Found {len(items)} items")


# 2. Search by product IDs

ids = [
    # Add exact EarthCARE product IDs here.
]

if ids:
    items = catalog.search_by_id(ids)

    print(f"Found {len(items)} items")


# 3. Paired search and CSV creation

products = {
    "ATL_EBD_2A": None,
    "AC__TC__2B": None,
    "ACM_COM_2B": None,
    "CPR_FMR_2A": None,
    "CPR_CD__2A": None,
    "MSI_RGR_1C": None,
}

df = search_paired_products(
    products=products,
    datetime=[
        "2025-01-01T00:00:00Z",
        "2025-01-31T23:59:59Z",
    ],
    bbox=[-11.0, 29.0, 40.0, 47.0],
    output_csv="output/matched_frames.csv",
)

# print(df.head())
