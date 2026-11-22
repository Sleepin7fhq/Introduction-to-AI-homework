"""上传图和参考图使用相同的解码、方向校正和缩放流程。"""

from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from guide_data import GuideError

MAX_BYTES = 12 * 1024 * 1024
MAX_PIXELS = 36_000_000


def prepare_photo(raw: bytes, side: int = 1280) -> bytes:
    if len(raw) > MAX_BYTES:
        raise GuideError("照片超过 12 MB，请缩小后重试。")
    try:
        with Image.open(BytesIO(raw), formats=("JPEG", "PNG")) as check:
            if check.width * check.height > MAX_PIXELS:
                raise GuideError("照片超过 3600 万像素，请缩小后重试。")
            check.verify()
        with Image.open(BytesIO(raw), formats=("JPEG", "PNG")) as source:
            upright = ImageOps.exif_transpose(source)
            upright.thumbnail((side, side), Image.Resampling.LANCZOS)
            if upright.has_transparency_data:
                rgba = upright.convert("RGBA")
                rgb = Image.new("RGB", rgba.size, "white")
                rgb.paste(rgba, mask=rgba.getchannel("A"))
            else:
                rgb = upright.convert("RGB")
            rgb.info.clear()
            out = BytesIO()
            rgb.save(out, format="JPEG", quality=82, optimize=True)
            return out.getvalue()
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise GuideError("照片像素过高，请缩小后重试。") from None
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError, EOFError):
        raise GuideError("照片无法解码，请选择完整的 JPG 或 PNG 文件。") from None


def read_photo(path: Path, side: int = 1280) -> bytes:
    try:
        with path.open("rb") as file:
            return prepare_photo(file.read(MAX_BYTES + 1), side)
    except OSError:
        raise GuideError("照片文件缺失或无法读取。") from None


def reference_photos(directory, buildings):
    refs = []
    for building in buildings.values():
        for name in building.reference_images:
            path = directory / name
            try:
                if path.resolve().parent != directory.resolve():
                    raise GuideError("请使用参考图目录内的文件。")
                photo = read_photo(path, side=768)
            except (OSError, RuntimeError):
                raise GuideError(f"{building.name} 的参考图 {name} 路径不可用。") from None
            except GuideError as exc:
                raise GuideError(f"{building.name} 的参考图 {name} 无法使用。{exc}") from None
            refs.append((building.id, photo))
    return refs
