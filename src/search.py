
"""
Search ESA MAAP for :
1. products that satisfy filters relative to version, datetime, bbox
2. products with specific ids
3. products for the same orbit/frame number: returns a csv where each row is an orbit and the columns contain info on the requested products
this csv can be later used to download or stream
"""

import numpy as np
import pandas as pd
from pathlib import Path
from pystac_client import Client
import time
import re
from pystac_client.exceptions import APIError


CATALOG_URL = "https://catalog.maap.eo.esa.int/catalogue/"


#add more if needed, these are just the main
EC_multiple_COLLECTIONS = [
    "EarthCAREL2Validated_MAAP",
    "EarthCAREL1Validated_MAAP",
    "EarthCAREXMETL1DProducts10_MAAP",
]


class Catalog:

    def __init__(self, catalog_url=CATALOG_URL):

        self.catalog_url = catalog_url
        self.catalog = Client.open(self.catalog_url)

    def search(
        self,
        product,
        collections=EC_multiple_COLLECTIONS,
        version=None,
        datetime=None,
        bbox=None,
        max_items=None,
        max_attempts=3,
        retry_delay=10,
    ):
        """
        Search by product, version, datetime and bbox.

        Retry temporary ESA MAAP catalogue errors during pagination.
        """

        filter_query = f"productType = '{product}'"

        if version is not None:
            filter_query += (
                f" and version = '{version.lower()}'"
            )

        retryable_statuses = (408, 429, 500, 502, 503, 504)

        for attempt in range(1, max_attempts + 1):

            try:
                item_search = self.catalog.search(
                    collections=collections,
                    filter=filter_query,
                    datetime=datetime,
                    bbox=bbox,
                    method="GET",
                    max_items=max_items,
                    limit=50,
                )

                items = []

                for page_number, page in enumerate(
                    item_search.pages(), start=1
                ):
                    page_items = list(page.items)
                    items.extend(page_items)

                return items

            except APIError as e:

                # pystac-client may expose the HTTP status only in the error message.
                match = re.search(r"\b(408|429|500|502|503|504)\b", str(e))

                if match is None:
                    raise

                status = int(match.group(1))

                if status not in retryable_statuses:
                    raise

                if attempt == max_attempts:
                    raise

                delay = retry_delay * (2 ** (attempt - 1))

                time.sleep(delay)


    def search_by_id(self, ids):
        """
        Search products using their exact STAC IDs.
        """

        item_search = self.catalog.search(
            collections=EC_multiple_COLLECTIONS,
            ids=ids,
            method="GET",
            max_items=None,
        )

        return list(item_search.items())





def search_paired_products(
    products,
    datetime=None,
    bbox=None,
    output_csv="output/matched_frames.csv",
):

    """
    dictionary = {
    'AC__TC__2B': 'ba',
    'ACM_CAP_2B': 'ba'
    }
    products: dict with key: product_name (eg AC__TC__2B) and value version eg ba

    search for products and match them by orbit-frame
    save a csv of matched products (save in row only if all requested products are available for this frame)
    """

    catalog = Catalog()

    data_matching = {}

    for product, version in products.items():

        print(f"Processing {product}")

        items = catalog.search(
            product=product,
            version=version,
            datetime=datetime,
            bbox=bbox,
        )

        for item in items:

            curr_frame = item.id[-6:]

            asset = item.assets.get("enclosure_h5")

            if asset is None:
                continue

            h5_url = asset.href

            item_version = str(
                item.properties.get("version", "")
            ).lower()

            # Keep the latest version for each product/frame.
            if curr_frame not in data_matching:
                data_matching[curr_frame] = {
                    "time": item.properties.get(
                        "start_datetime"
                    )
                }

            if product not in data_matching[curr_frame]:
                data_matching[curr_frame][product] = {
                    "id": item.id,
                    "version": item_version,
                    "url": h5_url,
                }

            else:

                previous = data_matching[curr_frame][product]

                if item_version > previous["version"]:
                    data_matching[curr_frame][product] = {
                        "id": item.id,
                        "version": item_version,
                        "url": h5_url,
                    }

        print(f"Found {len(items)} items for {product}")

    # Keep only frames containing every requested product.
    matched_frames = {}

    for frame, data in data_matching.items():

        if all(product in data for product in products):
            matched_frames[frame] = data

    # Prepare CSV.
    rows = []

    for frame, data in matched_frames.items():

        row = {
            "orbit": frame[:5],
            "frame": frame[5],
            "time": data["time"],
        }

        for product in products:

            row[f"{product}_id"] = data[product]["id"]
            row[f"{product}_version"] = (
                data[product]["version"]
            )
            row[f"{product}_url"] = data[product]["url"]

        rows.append(row)

    df = pd.DataFrame(
        rows,
        columns=[
            "orbit", "frame", "time",
            *[
                f"{product}_{field}"
                for product in products
                for field in ("id", "version", "url")
            ],
        ],
    )

    output_path = Path(output_csv)
    output_path.parent.mkdir(
        parents=True, exist_ok=True
    )

    df.to_csv(output_path, index=False)

    print(f"Matched frames: {len(df)}")
    print(f"Saved to {output_path}")

    return df