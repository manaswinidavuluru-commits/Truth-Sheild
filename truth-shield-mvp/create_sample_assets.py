"""
Generates clean and spliced test assets for demonstrating Truth Shield's
image ELA (Error Level Analysis) and video temporal consistency capabilities.
"""
import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

STATIC_SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "static", "samples")
os.makedirs(STATIC_SAMPLES_DIR, exist_ok=True)

def create_sample_images():
    w, h = 640, 480
    
    # 1. Authentic sample: smooth gradient with shapes, saved uniformly
    img1 = Image.new("RGB", (w, h), color=(14, 71, 53))
    draw1 = ImageDraw.Draw(img1)
    # Draw geometric gradients and patterns
    for i in range(0, w, 20):
        draw1.line([(i, 0), (i, h)], fill=(16, 185, 129, 60), width=2)
    draw1.rectangle([100, 100, 540, 380], outline=(52, 211, 153), width=4)
    draw1.ellipse([220, 140, 420, 340], fill=(5, 150, 105), outline=(255, 255, 255), width=3)
    
    auth_path = os.path.join(STATIC_SAMPLES_DIR, "authentic_photo.jpg")
    img1.save(auth_path, "JPEG", quality=95)
    print(f"Created authentic sample: {auth_path}")
    
    # 2. Manipulated sample: resaved base, then pasted with a high-compression spliced object
    # First save base at high quality
    base = img1.copy()
    
    # Create foreign badge / spliced text patch
    patch = Image.new("RGB", (260, 100), color=(220, 38, 38))
    patch_draw = ImageDraw.Draw(patch)
    patch_draw.rectangle([5, 5, 255, 95], outline=(255, 255, 255), width=2)
    # Resave patch at very low quality (quality=30) to simulate foreign compression artifact
    temp_patch_path = os.path.join(STATIC_SAMPLES_DIR, "temp_patch.jpg")
    patch.save(temp_patch_path, "JPEG", quality=25)
    patch_low = Image.open(temp_patch_path)
    
    # Paste heavily compressed foreign patch onto base
    base.paste(patch_low, (190, 190))
    manip_path = os.path.join(STATIC_SAMPLES_DIR, "manipulated_photo.jpg")
    base.save(manip_path, "JPEG", quality=95)
    
    if os.path.exists(temp_patch_path):
        os.remove(temp_patch_path)
    print(f"Created manipulated sample: {manip_path}")

def create_sample_video():
    video_path = os.path.join(STATIC_SAMPLES_DIR, "sample_clip.mp4")
    w, h = 640, 360
    fps = 24
    num_frames = 72 # 3 seconds
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(video_path, fourcc, fps, (w, h))
    
    for i in range(num_frames):
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        # Background dark forest green
        frame[:] = (25, 59, 11) # BGR
        
        # Moving emerald circle
        cx = int(100 + (i / num_frames) * (w - 200))
        cy = int(h / 2 + 50 * np.sin(i / 10.0))
        cv2.circle(frame, (cx, cy), 45, (129, 185, 16), -1) # BGR emerald
        cv2.circle(frame, (cx, cy), 45, (255, 255, 255), 2)
        
        # Add frame counter text
        cv2.putText(frame, f"TRUTH SHIELD TEST FRAME {i+1}/{num_frames}", (30, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 240, 220), 2)
                    
        out.write(frame)
        
    out.release()
    print(f"Created sample video: {video_path}")

if __name__ == "__main__":
    create_sample_images()
    create_sample_video()
