from pathlib import Path
import mimetypes
import base64
from PIL import Image
import numpy as np


def load_image_as_data_uri(image_path: Path) -> str:
    if not image_path.exists():
        raise FileNotFoundError(f"Icon '{image_path.name}' not found")
    mime, _ = mimetypes.guess_type(image_path)
    with open(image_path, "rb") as f:
        base_64_string = base64.b64encode(f.read())
        encoded_string = f"data:{mime};base64,{base_64_string.decode()}"
    return encoded_string


def load_image_as_np_array(image_path: Path) -> tuple[np.array, int, int]:
    p_img = Image.open(image_path).convert('RGBA')
    width, height = p_img.size
    img = np.empty((height, width), dtype=np.uint32)
    view = img.view(dtype=np.uint8).reshape((height, width, 4))
    view[:, :, :] = np.flipud(np.asarray(p_img))
    return img, width, height
