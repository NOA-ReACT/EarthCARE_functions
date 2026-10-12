This repository contains some useful functions for searching and downloading EarthCARE products through ESA MAAP catalogue.


## Repository structure:

```text
EarthCARE_functions/
|___src/
|   |____authenticate.py
|   |____download_from_csv.py
|   |____download.py
|   |____filtered_search.py
|   |____parallel_download.py
|   |____search.py
|   |____utils.py
|___examples/
|   |____download_example.py
|   |____filtered_search_example.py
|   |____search_example.py
|____notebooks/
|   |____data.ipynb
|____pixi.lock
|____pixi.toml
|____readme.md
|____.gitignore

```


## Install dependencies using pixi
After downloading and installing pixi to create the environment run:
pixi install

and to activate it run from the root dir
pixi shell 

## Access token- ESA MAAP

In order to download or process data (not search), an access token is needed. 
To generate an ESA MAAP access token, login using your credentials here [https://portal.maap.eo.esa.int/ini/services/auth/token/] and generate the token. Then create a credentials.txt file and copy paste ONLY the token there without "" or anything else. Then add the credentials.txt path where needed.

authenticate.py contains functions to get access token and authenticate before downloading or processing

## Search products- Available functionalities:
an example of each use can be found on examples/search_example.py

To search and find items, we can create a catalog object and request some collections and then search for:
a. specific products, versions, datetime, bbox
b. specific ids if we already have for example a list of the ids of the products we want eg. [ECA_EXBA_AC__TC__2B_20250131T231133Z_20250919T004743Z_03859B]

with search_paired_products we can specify:
a. products: a dictionary of {product_type}: version, (version can be set to None) 
b. datetime
c.bbox
and create a csv where each row corresponds to an orbit/frame and the columns contain the urls of all the requested products for that orbit/frame


## Filtered search:

Apart from the filters concerning the product/version/date/bbox we can define a filtering function that is applied to single products

(an example function is implemented here that searches for consecutive along track pixels for which the corresponding vertical profiles do not contain pixels classified as some specific classes)

The filtering function receives an xarray Dataset and returns the matching indices.

The results are stored in a csv that contains in each row an orbit/frame, the url of the product that satisfies the filters and the corresponding indices

## Download

Contains a basic download function


## Download from csv

There are two functions:

Both can receive as input one of the csvs produced by the previous functions but:

1. download_products: Downloads the whole .h5 files
2. download_selected_variables: Downloads selected variables from each file using variables_by_product dict

Function (2) can download file either as an nc or as a zarr file. An align flag will be shortly implemented to perform an alignment to a common grid before downloading.

In notebooks/data.ipynb an example of how the different products and their variables can be loaded is shown. groups=product_type need to be used and each downloaded file corresponds to an orbit/frame


in parallel_download parallel processing of the csv is implemented where each of the workers processes a row of the csv and more than one attempts are possible if failures from ESA MAAP occur that can be temporary




## Running with tmux (Recommended)

For long-running downloads and processing tasks, it is recommended to use `tmux` to keep scripts running even after disconnecting from an SSH session.

Create a new tmux session:


tmux new -s earthcare


Inside the session, navigate to the project and run the desired script using Pixi:


cd ~/Projects/EarthCARE_functions
pixi run python examples/download_example.py


To detach from the session without stopping the script, press **Ctrl+B**, then **D**.

To reconnect later:


tmux attach -t earthcare


To list active sessions:


tmux ls


To terminate the session after the script finishes:


tmux kill-session -t earthcare


Using `tmux` is particularly useful for large EarthCARE downloads and parallel processing, as the process continues running when the SSH connection is closed, provided the remote server remains running.