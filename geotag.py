from __future__ import annotations
import json
import re
from pathlib import Path
import piexif


def get_place_from_filename(filename: str) -> str:
    """
    Soporta:
    - "Jardín_Floridablanca_1.jpg" -> "Jardín_Floridablanca"
    - "Parque_nacional_Acquestorte (1).jpg" -> "Parque_nacional_Acquestorte"
    - "Parque_nacional_Acquestorte (10).jpg" -> "Parque_nacional_Acquestorte"
    """
    stem = Path(filename).stem

    # 1) quitar sufijo tipo " (1)" o " (10)"
    stem = re.sub(r"\s*\(\d+\)$", "", stem)

    # 2) quitar sufijo tipo "_1" o "_10"
    stem = re.sub(r"_\d+$", "", stem)

    return stem.strip()


def deg_to_dms_rational(deg_float: float):
    """
    Convierte grados decimales a EXIF DMS racional.
    EXIF requiere ((deg,1),(min,1),(sec_num,sec_den))
    """
    deg_float = abs(deg_float)
    deg = int(deg_float)
    min_float = (deg_float - deg) * 60
    minute = int(min_float)
    sec_float = (min_float - minute) * 60

    # segundos con precisión
    sec_num = int(round(sec_float * 10000))
    sec_den = 10000

    return ((deg, 1), (minute, 1), (sec_num, sec_den))


def build_gps_ifd(lat: float, lon: float) -> dict:
    gps_ifd = {}

    gps_ifd[piexif.GPSIFD.GPSLatitudeRef] = b"N" if lat >= 0 else b"S"
    gps_ifd[piexif.GPSIFD.GPSLatitude] = deg_to_dms_rational(lat)

    gps_ifd[piexif.GPSIFD.GPSLongitudeRef] = b"E" if lon >= 0 else b"W"
    gps_ifd[piexif.GPSIFD.GPSLongitude] = deg_to_dms_rational(lon)

    gps_ifd[piexif.GPSIFD.GPSMapDatum] = b"WGS-84"
    return gps_ifd


def add_gps_exif(jpg_path: str | Path, lat: float, lon: float):
    """
    Inserta/actualiza EXIF GPS IFD en el JPG.
    """
    jpg_path = Path(jpg_path)

    # cargar exif existente (si no existe, creamos estructura)
    try:
        exif_dict = piexif.load(str(jpg_path))
    except Exception:
        exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}

    exif_dict["GPS"] = build_gps_ifd(lat, lon)
    exif_bytes = piexif.dump(exif_dict)

    piexif.insert(exif_bytes, str(jpg_path))


def geotag_working_folder(base_dir: str | Path = ".", geolocation_file="geolocation.json") -> dict:
    """
    Recorre working/*.jpg|*.jpeg y mete GPS EXIF en base al lugar detectado.
    """
    base_dir = Path(base_dir)
    working_dir = base_dir / "working"
    geo_path = base_dir / geolocation_file

    if not working_dir.exists():
        raise FileNotFoundError(f"No existe la carpeta working/: {working_dir}")
    if not geo_path.exists():
        raise FileNotFoundError(f"No existe {geolocation_file}: {geo_path}")

    geo_map = json.loads(geo_path.read_text(encoding="utf-8"))

    jpgs = [f for f in working_dir.iterdir()
            if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg")]
    jpgs.sort(key=lambda x: x.name.lower())

    total = ok = missing = failed = 0

    for img in jpgs:
        total += 1
        place = get_place_from_filename(img.name)

        if place not in geo_map:
            missing += 1
            print(f"[MISSING] {img.name} -> lugar '{place}' NO existe en geolocation.json")
            continue

        lat = geo_map[place]["lat"]
        lon = geo_map[place]["lon"]

        try:
            add_gps_exif(img, lat, lon)
            ok += 1
            print(f"[GEO OK] {img.name} -> {place} ({lat}, {lon})")
        except Exception as e:
            failed += 1
            print(f"[GEO ERROR] {img.name}: {e}")

    return {"total": total, "ok": ok, "missing": missing, "failed": failed}


def test_working_has_gps(base_dir: str | Path = ".") -> dict:
    base_dir = Path(base_dir)
    working_dir = base_dir / "working"

    jpgs = [f for f in working_dir.iterdir()
            if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg")]
    jpgs.sort(key=lambda x: x.name.lower())

    total = ok = failed = 0

    for img in jpgs:
        total += 1
        try:
            exif = piexif.load(str(img))
            gps = exif.get("GPS", {})
            if not gps:
                failed += 1
                print(f"[GPS FAIL] {img.name} -> no GPS IFD")
                continue

            if piexif.GPSIFD.GPSLatitude not in gps or piexif.GPSIFD.GPSLongitude not in gps:
                failed += 1
                print(f"[GPS FAIL] {img.name} -> GPS incompleto")
                continue

            ok += 1
            print(f"[GPS OK] {img.name}")

        except Exception as e:
            failed += 1
            print(f"[GPS ERROR] {img.name}: {e}")

    return {"total": total, "ok": ok, "failed": failed}
