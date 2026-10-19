import requests
from aiohttp import ClientError, ClientResponseError
import numpy as np
import pandas as pd
import pvlib


def save_dataset(ds, output_path, product, output_format):

    if output_format == "zarr":

        ds.to_zarr(
            output_path,
            group=product,
            mode="a",
            consolidated=False,
        )

    elif output_format == "netcdf":

        ds.to_netcdf(
            output_path,
            group=product,
            mode="a",
            engine="h5netcdf",
        )


RETRYABLE_STATUSES = {408, 425, 429, 500, 502, 503, 504}


def is_retryable_error(error):
    """
    Check whether an error is caused by a temporary
    network or server problem.
    """

    current = error
    seen = set()

    while current is not None and id(current) not in seen:
        seen.add(id(current))

        if isinstance(current, ClientResponseError):
            return current.status in RETRYABLE_STATUSES

        if isinstance(current, requests.exceptions.HTTPError):
            return (
                current.response is not None
                and current.response.status_code in RETRYABLE_STATUSES
            )

        if isinstance(
            current,
            (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                TimeoutError,
                ConnectionResetError,
            ),
        ):
            return True

        if isinstance(current, ClientError):
            return True

        current = current.__cause__ or current.__context__

    return False



def calculate_sza(latitude, longitude, time):
    """
    Calculate solar zenith angles for EarthCARE profiles.

    latitude, longitude: 1D arrays
    time: 1D array of corresponding observation times
    """

    times = pd.to_datetime(time, utc=True)

    sza = np.array([
        pvlib.solarposition.get_solarposition(
            times[i],
            latitude[i],
            longitude[i],
        )["zenith"].iloc[0]
        for i in range(len(latitude))
    ])

    return sza


