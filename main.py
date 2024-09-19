import os
from PIL import Image
from pillow_heif import register_heif_opener

QUALITY = 80  # Можно настроить качество сжатия

def compress_image(input_path, output_path):
    with Image.open(input_path) as img:
        img.save(output_path, "HEIF", quality=QUALITY)
    print(f"Сжато: {input_path} -> {output_path}")

def process_directory(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                input_path = os.path.join(root, file)
                output_path = os.path.splitext(input_path)[0] + '.heic'
                compress_image(input_path, output_path)

def main(input_path):
    register_heif_opener()
    input_path = input_path.strip('"')
    
    if os.path.exists(input_path):
        if os.path.isfile(input_path):
            print(f"Обрабатываем файл: {input_path}")
            output_path = os.path.splitext(input_path)[0] + '.heic'
            compress_image(input_path, output_path)
        elif os.path.isdir(input_path):
            print(f"Обрабатываем директорию: {input_path}")
            process_directory(input_path)
    else:
        print("Указанный путь не существует")

if __name__ == "__main__":
    input_path = input("Введите путь к файлу или директории: ")
    main(input_path)