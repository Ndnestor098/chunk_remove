from PIL import Image
import os

def split_images_folder_2x2(
    input_dir,
    output_dir,
    base_name="parque",
    quality=95
):
    os.makedirs(output_dir, exist_ok=True)

    counter = 1  # contador GLOBAL

    for file in sorted(os.listdir(input_dir)):
        if not file.lower().endswith((".png", ".jpg", ".jpeg")):
            continue

        input_path = os.path.join(input_dir, file)

        with Image.open(input_path) as img:
            width, height = img.size
            half_width = width // 2
            half_height = height // 2

            crops = [
                (0, 0, half_width, half_height),
                (half_width, 0, width, half_height),
                (0, half_height, half_width, height),
                (half_width, half_height, width, height),
            ]

            for box in crops:
                cropped = img.crop(box)

                output_path = os.path.join(
                    output_dir, f"{base_name} ({counter}).jpg"
                )

                cropped.convert("RGB").save(
                    output_path,
                    format="JPEG",
                    quality=quality,
                    subsampling=0
                )

                counter += 1


split_images_folder_2x2(
    "./no_shorting/",
    "./shorting/",
    base_name="Parque_Málaga"
)
