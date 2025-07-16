from PIL import Image
import os

def optimize_image(filepath):
    # Open the image
    with Image.open(filepath) as img:
        # Convert to RGB if image is in RGBA mode
        if img.mode in ('RGBA', 'LA'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1])
            img = background
        
        # Calculate new size while maintaining aspect ratio
        max_size = (1920, 1080)  # Full HD resolution
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Get the original filename without extension
        filename, ext = os.path.splitext(filepath)
        # Create the new filename
        new_filepath = f"{filename}_optimized{ext}"
        
        # Save with optimization
        img.save(new_filepath, 'JPEG', quality=85, optimize=True)
        
        # If optimization was successful, replace the original file
        if os.path.exists(new_filepath):
            original_size = os.path.getsize(filepath) / (1024 * 1024)  # MB
            optimized_size = os.path.getsize(new_filepath) / (1024 * 1024)  # MB
            print(f"Optimized {filepath}")
            print(f"Original size: {original_size:.2f}MB")
            print(f"Optimized size: {optimized_size:.2f}MB")
            print(f"Reduction: {((original_size - optimized_size) / original_size * 100):.2f}%")
            
            # Replace original with optimized version
            os.replace(new_filepath, filepath)

def main():
    image_dir = 'src/static'
    for filename in os.listdir(image_dir):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            filepath = os.path.join(image_dir, filename)
            optimize_image(filepath)

if __name__ == '__main__':
    main() 