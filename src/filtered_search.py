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
    credentials_path="credentials.txt",
    output_csv="output/filtered_results.csv",
):

    catalog = Catalog()

    if ids is not None:
        items = catalog.search_by_id(ids)

    else:
        items = catalog.search(product=product, version=version, datetime=datetime, bbox=bbox, max_items=max_items)
       
    access_token = get_access_token(credentials_path)
    fs = get_filesystem(access_token)

    results = []

    for item in items:

        asset = item.assets.get("enclosure_h5")

        if asset is None:
            continue

        # print(f"Filtering {item.id}")

        with fs.open(asset.href, "rb") as file:
            with xr.open_dataset(
                file,
                group="ScienceData",
                engine="h5netcdf",
            ) as ds:
                

                indices = np.asarray(filter_fn(ds))

                if indices.ndim != 2:
                    raise ValueError(
                        "Filter function must return a 2D array of indices."
                    )

                        

        results.append({
            "orbit": item.id[-6:-1],
            "frame": item.id[-1],
            "product_id": item.id,
            "product_type": product,
            "version": item.properties.get("version"),
            "time": item.properties.get(
                "start_datetime"
            ),
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
            "shape",
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
):


    """
    This function is for ACTC files, it searches if there are min_consecutive along track profiles for which no pixels
    are classified as one of the classes in excluded classes
    """
    
    classification = ds[var].values
    
    excluded = np.isin(
        classification,
        excluded_classes,
    )

    # A profile is valid only if none of its pixels belong to the excluded classes.
    valid_profiles = ~np.any(excluded, axis=1)

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




