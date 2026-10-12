
import requests
from pathlib import Path
from tqdm import tqdm


def download_file_with_bearer_token(
    url,
    token,
    folder_path,
    disable_bar=False,
):
    """
    Downloads an EarthCARE HDF5 file using a Bearer token.
    """

    headers = {"Authorization": f"Bearer {token}"}

    file_name = url.split("/")[-1]

    output_dir = Path(folder_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    file_path = output_dir / file_name

    if file_path.exists() and file_path.stat().st_size > 0:
        print(f"Skipping existing file: {file_path}")
        return file_path

    temporary_path = file_path.with_name(file_name + ".part")

    try:
        with requests.get(
            url,
            headers=headers,
            stream=True,
            timeout=120,
        ) as response:

            response.raise_for_status()

            file_size = int(
                response.headers.get("content-length", 0)
            )

            chunk_size = 8 * 1024 * 1024

            with open(temporary_path, "wb") as f, tqdm(
                desc=file_name,
                total=file_size or None,
                unit="iB",
                unit_scale=True,
                unit_divisor=1024,
                disable=disable_bar,
            ) as bar:

                for chunk in response.iter_content(
                    chunk_size=chunk_size
                ):
                    if chunk:
                        read_size = f.write(chunk)
                        bar.update(read_size)

        temporary_path.replace(file_path)

        if disable_bar:
            print(f"File downloaded successfully to {file_path}")

        return file_path

    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
