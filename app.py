from chunk_removal import process_folder_no_working, test_working_folder
from geotag import geotag_working_folder, test_working_has_gps

if __name__ == "__main__":
    stats = process_folder_no_working(".")
    print("\n=== RESUMEN ===")
    print(f"Origen:   {stats['src_dir']}")
    print(f"Destino:  {stats['dst_dir']}")
    print(f"Total:    {stats['total']}")
    print(f"OK:       {stats['ok']}")
    print(f"Fallos:   {stats['failed']}")

    print("\n=== TEST WORKING (CHUNK REMOVAL VERIFICATION) ===")
    test_stats = test_working_folder(".")
    print(f"Total:  {test_stats['total']}")
    print(f"OK:     {test_stats['ok']}")
    print(f"Fallos: {test_stats['failed']}")

    print("\n=== ADD GEOLOCATION (GPS EXIF) ===")
    geotag_working_folder(".", geolocation_file="geolocation.json")

    print("\n=== TEST GPS ===")
    test_working_has_gps(".")
