# drive_zip_utils.py
import os
import gdown
import zipfile

def download_and_unzip_from_drive(file_id, out_dir="acciones", output_zip="acciones.zip", quiet=False):
    """
    Descarga un ZIP público desde Google Drive (file_id) y lo descomprime en out_dir.
    Requiere que el archivo ZIP esté compartido en modo 'Cualquiera con el enlace - Lector'.
    """
    os.makedirs(out_dir, exist_ok=True)
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    gdown.download(url, output_zip, quiet=quiet)
    with zipfile.ZipFile(output_zip, "r") as zf:
        zf.extractall(out_dir)
    # Opcional: borrar el ZIP después de descomprimir si no lo necesitas
    # os.remove(output_zip)
    return out_dir
