import pandas as pd
import xarray as xr
import requests
from pathlib import Path
from tqdm import tqdm
import shutil

from utils import save_dataset
from authenticate import get_access_token, get_filesystem
from download import download_file_with_bearer_token

#Use this function to download the whole h5 file
def download_products(
    csv_path,
    output_dir,
    credentials_path,
    row_index=None,
):
    """
    Download EarthCARE HDF5 products listed in a CSV.

    Supports csvs created using : filtered_search, search_paired_products

    Files are saved in output_dir/orbit_frame/product_type/
    """

    df = pd.read_csv(
        csv_path,
        dtype={"orbit": str, "frame": str},
    )

    if row_index is not None:
        df = df.iloc[[row_index]]

    if df.empty:
        print("The CSV is empty.")
        return

    

    # Identify the CSV format.
    product_columns = [
        col for col in df.columns
        if col.endswith("_url") and col != "url"
    ]

    if product_columns:
        csv_type = "paired"

    elif {"product_type", "url"}.issubset(df.columns):
        csv_type = "filtered"

    else:
        raise ValueError(
            "CSV must contain PRODUCT_url columns "
            "or product_type and url columns."
        )

    access_token = get_access_token(credentials_path)

    for _, row in df.iterrows():

        orbit = str(row["orbit"])
        frame = str(row["frame"])

        frame_folder = (
            Path(output_dir) / f"{orbit}_{frame}"
        )

        if csv_type == "paired":

            for column in product_columns:

                product = column.removesuffix("_url")
                url = row[column]

                if pd.isna(url) or not str(url).strip():
                    continue

                folder_path = frame_folder / product

                download_file_with_bearer_token(
                    url=url,
                    token=access_token,
                    folder_path=folder_path,
                )

        else:

            product = str(row["product_type"])
            url = row["url"]

            if pd.isna(url) or not str(url).strip():
                continue

            folder_path = frame_folder / product

            download_file_with_bearer_token(
                url=url,
                token=access_token,
                folder_path=folder_path,
            )

    print("Finished downloading products.")


#use this function to download selected varianles

def download_selected_variables(
    csv_path,
    output_dir,
    variables_by_product,
    output_format="netcdf",
    align=False,
    credentials_path="credentials.txt",
    row_index=None,
):
    """
    Extract selected EarthCARE variables into Zarr or NetCDF.

    Supports paired-search and filtered-search CSVs.

    Selected variables preserve their native dimensions.
    JSG alignment is not yet implemented.

    variables_by_product: dict with product_id: list of var names
    """

    if align:
        raise NotImplementedError(
            "JSG alignment will be implemented later."
        )

    if output_format not in ("zarr", "netcdf"):
        raise ValueError(
            "output_format must be 'zarr' or 'netcdf'."
        )

    if not variables_by_product:
        raise ValueError(
            "variables_by_product cannot be empty."
        )

    df = pd.read_csv(
        csv_path,
        dtype={"orbit": str, "frame": str},
    )

    if row_index is not None:
        df = df.iloc[[row_index]]

    if df.empty:
        print("The CSV is empty.")
        return []

    

    
    product_columns = [
        col for col in df.columns
        if col.endswith("_url") and col != "url"
    ]

    #csv_type is defined so that it can work with csvs produced either with filter function or with pair function
    #the names of the columns are different
    #NOTE: add new if you provide a csv with other column names

    if product_columns:
        csv_type = "paired"

    elif {"product_type", "url"}.issubset(df.columns):
        csv_type = "filtered"

    else:
        raise ValueError(
            "CSV must contain PRODUCT_url columns "
            "or product_type and url columns."
        )

    access_token = get_access_token(credentials_path)
    fs = get_filesystem(access_token)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    extension = ".zarr" if output_format == "zarr" else ".nc"
    output_paths = []

    for _, row in df.iterrows():

        orbit = str(row["orbit"])
        frame = str(row["frame"])

        if csv_type == "paired":

            row_products = {product: row[f"{product}_url"] for product in variables_by_product}

            output_name = f"EarthCARE_{orbit}_{frame}"

        else:

            product = row["product_type"]

            if pd.isna(product) or not str(product).strip():
                raise ValueError(
                    "Filtered CSV has a missing product_type."
                )

            product = str(product)

            row_products = {product: row["url"]}

            # Include product ID to distinguish multiple
            # files/versions from the same orbit-frame.
            output_name = str(row["product_id"])

        output_path = output_dir / f"{output_name}{extension}"

        if output_path.exists():
            print(f"Skipping existing output: {output_path}")
            output_paths.append(output_path)
            continue

        temporary_path = output_dir / f"{output_name}.partial{extension}"

        if temporary_path.exists():
            if temporary_path.is_dir():
                shutil.rmtree(temporary_path)
            else:
                temporary_path.unlink()

        root = xr.Dataset(
            attrs={
                "orbit": orbit,
                "frame": frame,
            }
        )

        try:

            # Create the output before adding product groups.
            if output_format == "zarr":
                root.to_zarr(
                    temporary_path,
                    mode="w",
                    consolidated=False,
                )
            else:
                root.to_netcdf(
                    temporary_path,
                    mode="w",
                    engine="h5netcdf",
                )

            for product, url in row_products.items():

                if product not in variables_by_product:
                    raise KeyError(
                        f"No variables configured for {product}."
                    )

                variables = variables_by_product[product]

                if not variables:
                    raise ValueError(
                        f"No variables selected for {product}."
                    )

                if pd.isna(url) or not str(url).strip():
                    raise ValueError(
                        f"Missing URL for {product}, "
                        f"orbit {orbit}, frame {frame}."
                    )

                print(
                    f"Processing {orbit}_{frame}: {product}"
                )

                with fs.open(url, "rb") as file:

                    with xr.open_dataset(
                        file,
                        group="ScienceData",
                        engine="h5netcdf",
                    ) as ds:

                        missing = [var for var in variables if var not in ds.variables]

                        if missing:
                            raise KeyError(
                                f"{product} missing variables: "
                                f"{missing}"
                            )

                        selected = ds[variables].copy(deep=False)

                        selected = selected.drop_encoding()

                        selected.attrs = {
                            "earthcare_product": product,
                            "source_file": str(url).split("/")[-1],
                            "source_url": str(url),
                        }

                        # Placeholder for JSG alignment.
                        #if align:
                        # selected = align_to_jsg(
                        #     selected,
                        #     product,
                        #     reference_grid,
                        # )

                        save_dataset(
                            ds=selected,
                            output_path=temporary_path,
                            product=product,
                            output_format=output_format,
                        )

            temporary_path.rename(output_path)

        except Exception:

            if temporary_path.exists():
                if temporary_path.is_dir():
                    shutil.rmtree(temporary_path)
                else:
                    temporary_path.unlink()

            raise

        print(f"Saved: {output_path}")
        output_paths.append(output_path)

    return output_paths
