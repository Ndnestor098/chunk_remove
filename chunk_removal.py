from __future__ import annotations
from pathlib import Path


# Markers esenciales que conservamos (segmentos con length)
KEEP_MARKERS = {
    0xC0,  # SOF0 (baseline DCT)
    0xC1,  # SOF1
    0xC2,  # SOF2 (progressive)
    0xC3,  # SOF3
    0xC5,  # SOF5
    0xC6,  # SOF6
    0xC7,  # SOF7
    0xC9,  # SOF9
    0xCA,  # SOF10
    0xCB,  # SOF11
    0xCD,  # SOF13
    0xCE,  # SOF14
    0xCF,  # SOF15

    0xDB,  # DQT
    0xC4,  # DHT
    0xDD,  # DRI
    0xDA,  # SOS (manejado aparte)
}

# Markers sin length
NO_LENGTH_MARKERS = {0xD8, 0xD9} | set(range(0xD0, 0xD8))  # SOI, EOI, RST0..RST7


def _read_u16_be(buf: bytes, offset: int) -> int:
    return (buf[offset] << 8) | buf[offset + 1]


def chunk_removal_jpeg_strict(input_path: str | Path, output_path: str | Path) -> Path:
    """
    Chunk Removal estricto para JPEG:
    - Reescribe JPEG conservando SOLO segmentos esenciales para decodificar.
    - Remueve toda metadata y segmentos no esenciales.
    - LOSSLESS: no recompresión (copiamos stream comprimido después de SOS).
    """
    input_path = Path(input_path)
    output_path = Path(output_path)

    data = input_path.read_bytes()

    # Validación mínima
    if len(data) < 4 or data[0:2] != b"\xFF\xD8":
        raise ValueError(f"Archivo no es JPEG válido: {input_path.name}")

    out = bytearray()
    out += b"\xFF\xD8"  # SOI

    i = 2

    while i < len(data):
        if data[i] != 0xFF:
            raise ValueError(f"JPEG corrupto: marker inválido en {input_path.name}")

        # saltar padding 0xFF
        while i < len(data) and data[i] == 0xFF:
            i += 1
        if i >= len(data):
            break

        marker = data[i]
        i += 1

        # EOI
        if marker == 0xD9:
            out += b"\xFF\xD9"
            break

        # RST0..RST7
        if 0xD0 <= marker <= 0xD7:
            out += bytes([0xFF, marker])
            continue

        # SOS: copiar segmento SOS + copiar todo el stream comprimido hasta el final
        if marker == 0xDA:
            if i + 2 > len(data):
                raise ValueError(f"JPEG corrupto (SOS sin length) en {input_path.name}")
            seglen = _read_u16_be(data, i)
            if seglen < 2 or i + seglen > len(data):
                raise ValueError(f"JPEG corrupto (SOS length inválido) en {input_path.name}")

            out += b"\xFF\xDA" + data[i:i + seglen]
            i += seglen

            # copiar TODO el stream comprimido restante (incluye EOI si existe)
            out += data[i:]
            break

        # Segmentos normales con length
        if i + 2 > len(data):
            raise ValueError(f"JPEG corrupto (segment sin length) en {input_path.name}")

        seglen = _read_u16_be(data, i)
        if seglen < 2:
            raise ValueError(f"JPEG corrupto (seglen < 2) en {input_path.name}")

        seg_start = i
        seg_end = i + seglen
        if seg_end > len(data):
            raise ValueError(f"JPEG corrupto (segment fuera de rango) en {input_path.name}")

        segment_payload = data[seg_start:seg_end]
        i = seg_end

        # Conservar sólo marcadores esenciales
        if marker in KEEP_MARKERS:
            out += bytes([0xFF, marker]) + segment_payload
        else:
            continue

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(out)
    return output_path


# ------------------ TEST / VERIFY ------------------

def verify_jpeg_is_chunk_removed(path: str | Path) -> tuple[bool, list[str]]:
    """
    Verifica que el JPG está realmente 'chunk removed':
      - NO APP0..APP15 (0xE0..0xEF)
      - NO COM (0xFE)
      - NO otros markers no esenciales antes de SOS
    Retorna:
      (ok, problemas[])
    """
    path = Path(path)
    data = path.read_bytes()

    if len(data) < 4 or data[:2] != b"\xFF\xD8":
        return False, ["No es JPEG válido (SOI faltante)"]

    i = 2
    problems = []

    while i < len(data):
        if data[i] != 0xFF:
            problems.append("JPEG corrupto: marker inválido")
            return False, problems

        # saltar padding
        while i < len(data) and data[i] == 0xFF:
            i += 1
        if i >= len(data):
            break

        marker = data[i]
        i += 1

        # EOI
        if marker == 0xD9:
            break

        # RST0..RST7 sin length
        if 0xD0 <= marker <= 0xD7:
            continue

        # SOS: desde acá es scan data, no se parsea más (correcto)
        if marker == 0xDA:
            # Si quieres ultra-estricto, podrías verificar que NO haya 0xFFEx antes de SOS
            return (len(problems) == 0), problems

        # length
        if i + 2 > len(data):
            problems.append(f"JPEG corrupto: segment length incompleto (marker=0xFF{marker:02X})")
            return False, problems

        seglen = _read_u16_be(data, i)
        if seglen < 2:
            problems.append(f"JPEG corrupto: seglen < 2 (marker=0xFF{marker:02X})")
            return False, problems

        # Detectar metadata / no-esencial
        if 0xE0 <= marker <= 0xEF:
            problems.append(f"Encontrado APP{marker - 0xE0} (0xFF{marker:02X})")
        elif marker == 0xFE:
            problems.append("Encontrado COM (0xFFFE)")
        elif marker not in KEEP_MARKERS:
            problems.append(f"Encontrado marker no-esencial (0xFF{marker:02X})")

        i += seglen

    return (len(problems) == 0), problems


def test_working_folder(base_dir: str | Path = ".") -> dict:
    """
    Testea TODOS los JPG de working/ y confirma que están chunk removed de verdad.
    """
    base_dir = Path(base_dir)
    working_dir = base_dir / "working"

    if not working_dir.exists():
        raise FileNotFoundError(f"No existe la carpeta: {working_dir}")

    files = [f for f in working_dir.iterdir()
             if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg")]
    files.sort(key=lambda x: x.name.lower())

    total = 0
    ok = 0
    failed = 0

    for f in files:
        total += 1
        valid, problems = verify_jpeg_is_chunk_removed(f)
        if valid:
            ok += 1
            print(f"[TEST OK] {f.name}")
        else:
            failed += 1
            print(f"[TEST FAIL] {f.name}")
            for p in problems:
                print("   -", p)

    return {"total": total, "ok": ok, "failed": failed, "dir": str(working_dir)}


def process_folder_no_working(base_dir: str | Path = ".") -> dict:
    """
    Lee base_dir/no_working/*.jpg|*.jpeg
    Hace chunk removal estricto y guarda en base_dir/working/ (mismo nombre)
    """
    base_dir = Path(base_dir)
    src_dir = base_dir / "no_working"
    dst_dir = base_dir / "working"

    if not src_dir.exists():
        raise FileNotFoundError(f"No existe la carpeta: {src_dir}")

    dst_dir.mkdir(parents=True, exist_ok=True)

    # 🔥 Esto evita duplicados en Windows por mayúsculas/minúsculas
    files = [f for f in src_dir.iterdir()
             if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg")]
    files.sort(key=lambda x: x.name.lower())

    total, ok, failed = 0, 0, 0

    for f in files:
        total += 1
        try:
            out_path = dst_dir / f.name
            chunk_removal_jpeg_strict(f, out_path)
            ok += 1
            print(f"[OK] {f.name}")
        except Exception as e:
            failed += 1
            print(f"[ERROR] {f.name}: {e}")

    return {
        "total": total,
        "ok": ok,
        "failed": failed,
        "src_dir": str(src_dir),
        "dst_dir": str(dst_dir),
    }
