"""
define a filter function
perform search that returns a csv with the info of the products requested that also satisfy the criteria of the filter function
the specific parts of the file where the criteria are met are returned
"""


import json
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
import xarray as xr
import time
from aiohttp import ClientResponseError
from search import Catalog
from authenticate import get_access_token, get_filesystem




def search_filtered(
    product,
    filter_fn,
    ids=None,
    version=None,
    datetime=None,
    bbox=None,
    max_items=None,
    daytime_only=False,
    credentials_path="credentials.txt",
    output_csv="output/filtered_results.csv",
    max_attempts=3,
    retry_delay=10,
):

    catalog = Catalog()

    if ids is not None:
        items = catalog.search_by_id(ids)

    else:
        items = catalog.search(
            product=product,
            version=version,
            datetime=datetime,
            bbox=bbox,
            max_items=2200,
        )

    access_token = get_access_token(credentials_path)
    fs = get_filesystem(access_token)

    results = []

    for item in items:

        if max_items is not None and len(results) > max_items:
            break

        frame = item.id[-1]

        if daytime_only and frame not in ("D", "E", "F"):
            continue

        asset = item.assets.get("enclosure_h5")

        if asset is None:
            continue

        # print(f"Filtering {item.id}")

        for attempt in range(1, max_attempts + 1):

            try:
                
                if attempt > 1:
                    access_token = get_access_token(credentials_path)
                    fs = get_filesystem(access_token)

                with fs.open(asset.href, "rb") as file:
                    with xr.open_dataset(
                        file,
                        group="ScienceData",
                        engine="h5netcdf",
                    ) as ds:

                        indices = np.asarray(filter_fn(ds))

                        if indices.ndim != 2 or indices.shape[1] != 2:
                            raise ValueError(
                                "Filter must return [start, stop] ranges."
                            )

                break

            except ClientResponseError as e:

                if e.status not in (408, 429, 500, 502, 503, 504):
                    raise

                if attempt == max_attempts:
                    raise

                delay = retry_delay * (2 ** (attempt - 1))

                # print(
                #     f"Temporary ESA MAAP error {e.status} "
                #     f"for {item.id}. "
                #     f"Retrying in {delay} seconds..."
                # )

                time.sleep(delay)

        if len(indices) == 0:
            continue

        results.append({
            "orbit": item.id[-6:-1],
            "frame": frame,
            "product_id": item.id,
            "product_type": product,
            "version": item.properties.get("version"),
            "time": item.properties.get("start_datetime"),
            "url": asset.href,
            "indices": json.dumps(indices.tolist()),
        })

    df = pd.DataFrame(
        results,
        columns=[
            "orbit",
            "frame",
            "product_id",
            "product_type",
            "version",
            "time",
            "url",
            "indices",
        ],
    )

    if output_csv is not None:

        output_path = Path(output_csv)
        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        df.to_csv(output_path, index=False)

        print(f"Saved results to {output_path}")

    print(f"Files passing filter: {len(df)}")

    return df





#example filter function

def filter_consecutive_profiles(
    ds,
    excluded_classes,
    var='synergetic_target_classification_low_resolution',
    min_consecutive=22,
    lat_range=(-45, 45),
    lon_range=(-45, 45),
):


    """
    This function is for ACTC files, it searches if there are min_consecutive along track profiles for which no pixels
    are classified as one of the classes in excluded classes
    """
    
    classification = ds[var].values

    latitude = ds["latitude"].values
    longitude = ds["longitude"].values
    
    excluded = np.isin(
        classification,
        excluded_classes,
    )

    # A profile is valid only if none of its pixels belong to the excluded classes.
    valid_profiles = ~np.any(excluded, axis=1)
    #filter to be inside the acceptable MTG disk: -45,45
    valid_location = (
        (latitude >= lat_range[0]) &
        (latitude <= lat_range[1]) &
        (longitude >= lon_range[0]) &
        (longitude <= lon_range[1])
    )

    valid_profiles = valid_profiles & valid_location

    # Find the starts and ends of consecutive valid runs.
    padded = np.concatenate((
        [False],
        valid_profiles,
        [False],
    ))

    changes = np.diff(padded.astype(int))

    starts = np.where(changes == 1)[0]
    ends = np.where(changes == -1)[0]

    ranges = []

    for start, end in zip(starts, ends):

        if end - start >= min_consecutive:
            ranges.append([int(start),int(end)])

    return np.asarray(ranges, dtype=int).reshape(-1, 2)



