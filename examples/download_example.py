
import sys
from pathlib import Path

sys.path.append(
    str(Path(__file__).resolve().parent.parent / "src")
)

from download_from_csv import download_products, download_selected_variables
from parallel_download import download_parallel


credentials_path = Path("/home/dkarkani/Projects/EarthCARE_functions/credentials.txt")
csv_path =Path("output/no_other_frames.csv")

output_dir =Path("data")



#uncomment below if you want to download all netcdf files: stored in output_dir/orbit_frame/product_id/blabla.h5
# download_products(
#     csv_path="output/matched_frames.csv",
#     output_dir="data",
#     credentials_path=credentials_path,
# )


#uncomment below if you want to download selected variables
#identify variables
variables_by_product = {
    "AC__TC__2B": [
        "synergetic_target_classification_low_resolution",
        "latitude",
        "longitude",
        "height"
    ],
    "ACM_COM_2B": [
        "ice_water_content",
        "height_layer",
        "latitude"
    ],
}

# download_selected_variables(
#     csv_path=csv_path,
#     output_dir=output_dir,
#     variables_by_product=variables_by_product,
#     output_format="netcdf",
#     align=False,
#     credentials_path=credentials_path,
# )


##uncomment below for parallel processing

results = download_parallel(
        csv_path=csv_path,
        output_dir=output_dir,
        mode="selected",
        variables_by_product=variables_by_product,
        output_format="netcdf",
        credentials_path=credentials_path,
        workers=2,
        max_attempts=3,
        retry_delay=10,
    )

print(results)


if __name__ == "__main__":
    
    main()


