import bz2
import gzip
import io
import json
import lzma
import struct
import subprocess
from typing import Optional

import fdt

try:
    import lz4.frame as _lz4_frame

    _HAS_LZ4 = True
except ImportError:
    _HAS_LZ4 = False

from .. import settings as app_settings
from .base import BaseMetadataExtractor
from .exceptions import DecompressionLimitExceeded, UnsupportedImageError

DTB_MAGIC = b"\xd0\x0d\xfe\xed"
DTB_MIN_SIZE = 64
DTB_MAX_SIZE = 10 * 1024 * 1024
UIMAGE_MAGIC = b"\x27\x05\x19\x56"
UIMAGE_HEADER_SIZE = 64
_CHUNK_SIZE = 64 * 1024


def _strip_uimage_header(data: bytes) -> bytes:
    if data[:4] == UIMAGE_MAGIC and len(data) > UIMAGE_HEADER_SIZE:
        payload_size = struct.unpack_from(">I", data, 12)[0]
        return data[UIMAGE_HEADER_SIZE : UIMAGE_HEADER_SIZE + payload_size]
    return data


def _check_limits(decompressed: int, compressed: int) -> None:
    if decompressed > app_settings.MAX_DECOMPRESSED_BYTES:
        raise DecompressionLimitExceeded(
            f"Decompressed size exceeded hard limit of "
            f"{app_settings.MAX_DECOMPRESSED_BYTES // (1024 * 1024)}MB. "
            f"Increase OPENWISP_FIRMWARE_UPGRADER_MAX_DECOMPRESSED_BYTES if required."
        )
    if (
        compressed > 0
        and (decompressed / compressed) > app_settings.MAX_DECOMPRESSED_RATIO
    ):
        raise DecompressionLimitExceeded(
            f"Compression ratio {decompressed // compressed}:1 exceeds limit of "
            f"{app_settings.MAX_DECOMPRESSED_RATIO}:1. "
            f"Increase OPENWISP_FIRMWARE_UPGRADER_MAX_DECOMPRESSED_RATIO if required."
        )


def _try_gzip(data: bytes) -> Optional[bytes]:
    if data[:2] != b"\x1f\x8b":
        return None
    chunks, total = [], 0
    compressed = len(data)
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(data)) as gz:
            while True:
                chunk = gz.read(_CHUNK_SIZE)
                if not chunk:
                    break
                chunks.append(chunk)
                total += len(chunk)
                _check_limits(total, compressed)
    except DecompressionLimitExceeded:
        raise
    except Exception:
        pass
    return b"".join(chunks) or None


def _try_xz(data: bytes) -> Optional[bytes]:
    if data[:6] != b"\xfd7zXZ\x00":
        return None
    try:
        result = lzma.decompress(data, format=lzma.FORMAT_XZ)
        _check_limits(len(result), len(data))
        return result
    except DecompressionLimitExceeded:
        raise
    except Exception:
        return None


def _try_lzma(data: bytes) -> Optional[bytes]:
    if data[0:1] != b"\x5d":
        return None
    try:
        result = lzma.decompress(data, format=lzma.FORMAT_ALONE)
        _check_limits(len(result), len(data))
        return result
    except DecompressionLimitExceeded:
        raise
    except Exception:
        return None


def _try_bz2(data: bytes) -> Optional[bytes]:
    if data[:3] != b"BZh":
        return None
    try:
        result = bz2.decompress(data)
        _check_limits(len(result), len(data))
        return result
    except DecompressionLimitExceeded:
        raise
    except Exception:
        return None


def _try_lz4(data: bytes) -> Optional[bytes]:
    if not _HAS_LZ4 or data[:4] != b"\x04\x22\x4d\x18":
        return None
    try:
        result = _lz4_frame.decompress(data)
        _check_limits(len(result), len(data))
        return result
    except DecompressionLimitExceeded:
        raise
    except Exception:
        return None


_DECOMPRESSORS = [_try_gzip, _try_xz, _try_lzma, _try_bz2, _try_lz4]


def _decompress(data: bytes) -> bytes:
    data = _strip_uimage_header(data)
    for fn in _DECOMPRESSORS:
        result = fn(data)
        if result is not None:
            return result
    return data


def _is_fit_image(dt: fdt.FDT) -> bool:
    try:
        return dt.get_node("/images") is not None
    except Exception:
        return False


def _dtb_from_fit(fit_data: bytes) -> Optional[bytes]:
    offset = 4
    while True:
        offset = fit_data.find(DTB_MAGIC, offset)
        if offset == -1:
            return None
        if offset + 8 > len(fit_data):
            break
        total_size = struct.unpack_from(">I", fit_data, offset + 4)[0]
        max_size = min(DTB_MAX_SIZE, len(fit_data) // 2)
        if DTB_MIN_SIZE < total_size < max_size:
            end = offset + total_size
            if end <= len(fit_data):
                candidate = fit_data[offset:end]
                try:
                    dt = fdt.parse_dtb(candidate)
                    root = dt.get_node("/")
                    if any(p.name in ("model", "compatible") for p in root.props):
                        return candidate
                except Exception:
                    pass
        offset += 1
    return None


def _locate_dtb(data: bytes) -> Optional[bytes]:
    offset = 0
    fit_candidate = None
    while True:
        offset = data.find(DTB_MAGIC, offset)
        if offset == -1:
            break
        if offset + 8 > len(data):
            break
        total_size = struct.unpack_from(">I", data, offset + 4)[0]
        if DTB_MIN_SIZE < total_size < DTB_MAX_SIZE:
            end = offset + total_size
            if end <= len(data):
                candidate = data[offset:end]
                try:
                    dt = fdt.parse_dtb(candidate)
                    root = dt.get_node("/")
                    prop_names = {p.name for p in root.props}
                    if "model" in prop_names or "compatible" in prop_names:
                        return candidate
                    if _is_fit_image(dt) and fit_candidate is None:
                        fit_candidate = candidate
                except Exception:
                    pass
        offset += 1
    if fit_candidate is not None:
        return _dtb_from_fit(fit_candidate)
    return None


def _prop_str(value) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value.rstrip("\x00")
    if isinstance(value, (list, tuple)) and value:
        return str(value[0]).rstrip("\x00")
    return str(value)


def _prop_strlist(value) -> list:
    if value is None:
        return []
    if isinstance(value, str):
        return [s for s in value.split("\x00") if s]
    if isinstance(value, (list, tuple)):
        return [str(s).rstrip("\x00") for s in value if s]
    return [str(value)]


def _parse_supported_devices(meta):
    if meta.get("compat_version", "1.0") != "1.0":
        return meta.get("new_supported_devices", [])
    return meta.get("supported_devices", [])


def _metadata_from_dtb(dtb_bytes: bytes) -> dict:
    dt = fdt.parse_dtb(dtb_bytes)
    root = dt.get_node("/")
    model, compatible = None, []
    for prop in root.props:
        if prop.name == "model":
            model = _prop_str(prop.value)
        elif prop.name == "compatible":
            compatible = _prop_strlist(prop.value)
    return {"model": model, "compatible": compatible, "source": "dtb"}


class OpenWrtMetadataExtractor(BaseMetadataExtractor):

    def extract_from_image(self) -> dict:
        return self._extract_from_fwtool()

    def _extract_from_fwtool(self) -> dict:
        try:
            result = subprocess.run(
                ["fwtool", "-q", "-i", "-", self.image_path],
                capture_output=True,
                timeout=30,
            )
        except FileNotFoundError:
            raise UnsupportedImageError("fwtool is not installed")
        except subprocess.TimeoutExpired:
            raise UnsupportedImageError("fwtool timed out")

        if result.returncode != 0:
            raise UnsupportedImageError(
                f"fwtool exited {result.returncode}: "
                f'{result.stderr.decode(errors="replace").strip()}'
            )
        try:
            meta = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise UnsupportedImageError(
                f"fwtool output is not valid JSON: {exc}"
            ) from exc

        version = meta.get("version", {})
        compatible = _parse_supported_devices(meta)
        return {
            "model": version.get("board", ""),
            "compatible": compatible,
            "target": version.get("target", ""),
            "version": version.get("version", ""),
            "compat_version": meta.get("compat_version", ""),
            "source": "fwtool",
        }

    def _read_kernel_bytes(self) -> bytes:
        with open(self.image_path, "rb") as f:
            data = f.read(app_settings.MAX_KERNEL_BYTES)
        return _decompress(data)

    def _read_kernel_from_tar(self) -> bytes:
        import tarfile

        with tarfile.open(self.image_path, "r:*") as tar:
            for member in tar.getmembers():
                if "kernel" in member.name.lower():
                    return _decompress(tar.extractfile(member).read())
        raise UnsupportedImageError("No kernel found in tar image")

    def extract_from_dtb(self) -> dict:
        try:
            kernel_bytes = self._read_kernel_bytes()
        except DecompressionLimitExceeded:
            raise
        except Exception:
            try:
                kernel_bytes = self._read_kernel_from_tar()
            except DecompressionLimitExceeded:
                raise
            except Exception:
                raise UnsupportedImageError("Cannot extract kernel data")
        dtb = _locate_dtb(kernel_bytes)
        if dtb is None:
            raise UnsupportedImageError("No valid DTB found")
        return _metadata_from_dtb(dtb)

    def extract(self) -> dict:
        result = None
        try:
            result = self._extract_from_fwtool()
        except UnsupportedImageError:
            pass
        if result is None:
            return self.extract_from_dtb()
        try:
            dtb_meta = self.extract_from_dtb()
            if dtb_meta.get("model"):
                result["model"] = dtb_meta["model"]
            if dtb_meta.get("compatible"):
                result.setdefault("compatible", dtb_meta["compatible"])
        except (UnsupportedImageError, DecompressionLimitExceeded):
            pass
        return result
