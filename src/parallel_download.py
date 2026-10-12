import time
from concurrent.futures import ProcessPoolExecutor, as_completed


import pandas as pd
import requests
from aiohttp import ClientError, ClientResponseError

from tqdm import tqdm

from download_from_csv import download_products, download_selected_variables
from utils import is_retryable_error


def process_row(
    row_index,
    csv_path,
    output_dir,
    mode,
    variables_by_product,
    output_format,
    credentials_path,
    max_attempts,
    retry_delay,
):
    """
    Process one CSV row with automatic retries.
    Each attempt creates a new token/filesystem.
    """

    for attempt in range(1, max_attempts + 1):

        try:

            if mode == "native":

                download_products(
                    csv_path=csv_path,
                    output_dir=output_dir,
                    credentials_path=credentials_path,
                    row_index=row_index,
                )

            elif mode == "selected":

                download_selected_variables(
                    csv_path=csv_path,
                    output_dir=output_dir,
                    variables_by_product=variables_by_product,
                    output_format=output_format,
                    credentials_path=credentials_path,
                    row_index=row_index,
                )

            return {
                "row_index": row_index,
                "status": "success",
                "attempts": attempt,
                "error": None,
            }

        except Exception as error:

            if (
                attempt == max_attempts
                or not is_retryable_error(error)
            ):
                return {
                    "row_index": row_index,
                    "status": "failed",
                    "attempts": attempt,
                    "error": str(error),
                }

            delay = retry_delay * (2 ** (attempt - 1))

            print(
                f"Row {row_index}: attempt {attempt} failed. "
                f"Retrying in {delay}s. Error: {error}",
                flush=True,
            )

            time.sleep(delay)


def download_parallel(
    csv_path,
    output_dir,
    mode="native",
    variables_by_product=None,
    output_format="netcdf",
    credentials_path="credentials.txt",
    workers=2,
    max_attempts=3,
    retry_delay=10,
):
    """
    Download or extract EarthCARE products in parallel.

    Each worker processes one CSV row at a time.
    """

    if mode not in ("native", "selected"):
        raise ValueError("mode must be 'native' or 'selected'")

    if workers < 1 or max_attempts < 1 or retry_delay < 0:
        raise ValueError("Invalid parallel/retry settings.")

    if mode == "selected" and not variables_by_product:
        raise ValueError(
            "variables_by_product is required for selected mode."
        )

    df = pd.read_csv(
        csv_path,
        dtype={"orbit": str, "frame": str},
    )

    if df.empty:
        print("CSV is empty.")
        return pd.DataFrame()

    # Avoid workers writing to identical destinations.
    if {"orbit", "frame"}.issubset(df.columns):

        paired_columns = [
            col for col in df.columns
            if col.endswith("_url") and col != "url"
        ]

        if paired_columns and df.duplicated(
            subset=["orbit", "frame"]
        ).any():
            raise ValueError(
                "Duplicate orbit-frame rows in paired CSV."
            )

    results = []

    with ProcessPoolExecutor(max_workers=workers) as executor:

        futures = [
            executor.submit(
                process_row,
                row_index,
                str(csv_path),
                str(output_dir),
                mode,
                variables_by_product,
                output_format,
                str(credentials_path),
                max_attempts,
                retry_delay,
            )
            for row_index in range(len(df))
        ]

        for future in tqdm(
            as_completed(futures),
            total=len(futures),
            desc="EarthCARE downloads",
        ):

            result = future.result()
            results.append(result)

            if result["status"] == "failed":
                tqdm.write(
                    f"Row {result['row_index']} failed: "
                    f"{result['error']}"
                )

    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values("row_index")

    print(
        f"Successful: "
        f"{(results_df['status'] == 'success').sum()}"
    )

    print(
        f"Failed: "
        f"{(results_df['status'] == 'failed').sum()}"
    )

    return results_df
