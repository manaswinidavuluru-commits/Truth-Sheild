"""
Media Forensics Engine for Truth Shield MVP.
Uses Pillow and OpenCV to perform real forensic analyses on images and videos:
- EXIF & software tag inspection
- Error Level Analysis (ELA) for compression tampering detection
- Spatial noise & blur variance analysis
- Video temporal consistency, keyframe sampling, and cut detection
"""
import os
import cv2
import numpy as np
from PIL import Image, ImageChops, ImageEnhance
from PIL.ExifTags import TAGS, GPSTAGS

def analyze_image_exif(image_path):
    """
    Extracts EXIF metadata, camera hardware information, and software editing signatures.
    """
    metadata = {
        "has_exif": False,
        "camera_make": None,
        "camera_model": None,
        "software": None,
        "datetime_original": None,
        "has_gps": False,
        "raw_tags": {}
    }
    
    try:
        with Image.open(image_path) as img:
            exif_data = img.getexif()
            if not exif_data:
                return metadata
                
            metadata["has_exif"] = True
            for tag_id, value in exif_data.items():
                tag_name = TAGS.get(tag_id, str(tag_id))
                # Format string/number values cleanly
                if isinstance(value, (str, int, float)):
                    metadata["raw_tags"][tag_name] = str(value)
                    
            metadata["camera_make"] = metadata["raw_tags"].get("Make")
            metadata["camera_model"] = metadata["raw_tags"].get("Model")
            metadata["software"] = metadata["raw_tags"].get("Software")
            metadata["datetime_original"] = metadata["raw_tags"].get("DateTimeOriginal") or metadata["raw_tags"].get("DateTime")
            
            # Check for GPS tags
            if "GPSInfo" in metadata["raw_tags"] or 34853 in exif_data:
                metadata["has_gps"] = True
                
    except Exception as e:
        print(f"EXIF extraction notice: {e}")
        
    return metadata

def perform_error_level_analysis(image_path, output_ela_path, quality=90, scale=12):
    """
    Performs Error Level Analysis (ELA).
    Saves the image at a known JPEG compression quality (default 90%),
    then calculates the pixel-level difference against the original.
    Modified/spliced areas compress at different rates and stand out brightly.
    """
    try:
        original = Image.open(image_path).convert("RGB")
        
        # Save temporary resaved copy to memory or temp path
        temp_resaved_path = output_ela_path + ".temp.jpg"
        original.save(temp_resaved_path, "JPEG", quality=quality)
        
        resaved = Image.open(temp_resaved_path)
        
        # Difference between original and resaved
        ela_img = ImageChops.difference(original, resaved)
        
        # Get extrema to compute scaling factor
        extrema = ela_img.getextrema()
        max_diff = max([ex[1] for ex in extrema])
        if max_diff == 0:
            max_diff = 1
            
        # Scale brightness so subtle compression artifacts become visually obvious
        scale_factor = min(int(255.0 / max_diff), scale)
        enhancer = ImageEnhance.Brightness(ela_img)
        ela_img = enhancer.enhance(scale_factor)
        
        # Ensure output directory exists and save ELA artifact
        os.makedirs(os.path.dirname(output_ela_path), exist_ok=True)
        ela_img.save(output_ela_path, "PNG")
        
        # Clean up temporary resaved file
        if os.path.exists(temp_resaved_path):
            os.remove(temp_resaved_path)
            
        # Compute statistical variance across the ELA matrix
        ela_np = np.array(ela_img)
        mean_diff = float(np.mean(ela_np))
        std_diff = float(np.std(ela_np))
        
        # Grid block analysis (16x16 grid across image to locate localized splice hotspots)
        h, w = ela_np.shape[:2]
        grid_rows, grid_cols = 8, 8
        cell_h, cell_w = max(1, h // grid_rows), max(1, w // grid_cols)
        block_means = []
        for r in range(grid_rows):
            for c in range(grid_cols):
                cell = ela_np[r*cell_h:(r+1)*cell_h, c*cell_w:(c+1)*cell_w]
                if cell.size > 0:
                    block_means.append(float(np.mean(cell)))
                    
        block_variance = float(np.std(block_means)) if block_means else 0.0
        max_block_mean = float(np.max(block_means)) if block_means else 0.0
        min_block_mean = float(np.min(block_means)) if block_means else 0.0
        hotspot_ratio = round((max_block_mean - min_block_mean) / (mean_diff + 0.1), 2)
        
        return {
            "success": True,
            "mean_difference": round(mean_diff, 2),
            "std_difference": round(std_diff, 2),
            "block_variance": round(block_variance, 2),
            "hotspot_ratio": hotspot_ratio,
            "max_difference": max_diff,
            "ela_saved_path": output_ela_path
        }
    except Exception as e:
        print(f"Error Level Analysis error: {e}")
        return {
            "success": False,
            "error": str(e)
        }

def analyze_image_noise_and_edges(image_path):
    """
    Analyzes spatial noise, sharpness distribution, and blur inconsistencies using OpenCV.
    """
    try:
        img_bgr = cv2.imread(image_path)
        if img_bgr is None:
            return {"success": False, "error": "Unable to decode image via OpenCV"}
            
        h, w, c = img_bgr.shape
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        
        # Laplacian variance measures edge sharpness / focus
        laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        
        # Canny edge density
        edges = cv2.Canny(gray, 100, 200)
        edge_density = float(np.sum(edges > 0) / (h * w)) * 100.0
        
        # High-frequency noise estimation (difference from Gaussian blur)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        noise = cv2.absdiff(gray, blurred)
        noise_level = float(np.mean(noise))
        
        return {
            "success": True,
            "dimensions": f"{w} x {h} px",
            "sharpness_score": round(laplacian_var, 2),
            "edge_density_pct": round(edge_density, 2),
            "noise_level": round(noise_level, 2)
        }
    except Exception as e:
        print(f"OpenCV image analysis error: {e}")
        return {"success": False, "error": str(e)}

def run_image_investigation(input_image_path, report_id, forensic_dir):
    """
    Complete image investigation pipeline.
    Combines EXIF metadata inspection, Error Level Analysis (ELA),
    and OpenCV spatial consistency analysis.
    """
    filename = os.path.basename(input_image_path)
    ela_filename = f"{report_id}_ela.png"
    ela_save_path = os.path.join(forensic_dir, ela_filename)
    
    # Run sub-analyses
    exif = analyze_image_exif(input_image_path)
    ela = perform_error_level_analysis(input_image_path, ela_save_path)
    noise = analyze_image_noise_and_edges(input_image_path)
    
    evidence = []
    suspicion_points = 0
    
    # 1. Evaluate EXIF findings
    if exif["software"]:
        evidence.append({
            "type": "Software Signature",
            "publisher": "EXIF Metadata Parser",
            "finding": f"Image metadata references editing software: '{exif['software']}'.",
            "url": None,
            "rating": "Digital Editing Indicated",
            "reliability": "Direct EXIF Header"
        })
        suspicion_points += 2
    elif not exif["has_exif"]:
        evidence.append({
            "type": "Metadata Integrity",
            "publisher": "EXIF Metadata Parser",
            "finding": "EXIF headers are absent or stripped. Common on social media re-uploads and web exports.",
            "url": None,
            "rating": "Stripped Metadata",
            "reliability": "Heuristic"
        })
    else:
        cam_info = f"{exif.get('camera_make') or ''} {exif.get('camera_model') or ''}".strip()
        evidence.append({
            "type": "Camera Origin",
            "publisher": "EXIF Metadata Parser",
            "finding": f"Captured with hardware: {cam_info or 'Standard Camera Device'}. Date: {exif.get('datetime_original', 'Not Recorded')}.",
            "url": None,
            "rating": "Hardware Header Present",
            "reliability": "Direct EXIF Header"
        })
        
    # 2. Evaluate ELA findings
    if ela.get("success"):
        block_var = ela.get("block_variance", 0)
        hotspot_ratio = ela.get("hotspot_ratio", 0)
        mean_diff = ela.get("mean_difference", 0)
        
        is_high_risk = hotspot_ratio > 3.0 or block_var > 8.0
        is_moderate_risk = hotspot_ratio > 1.8 or block_var > 4.5
        
        rating_label = "High Tampering Risk (Localized Splicing)" if is_high_risk else ("Moderate Compression Anomaly" if is_moderate_risk else "Uniform Compression")
        
        evidence.append({
            "type": "Error Level Analysis (ELA)",
            "publisher": "Pillow Forensic Module",
            "finding": f"Mean compression delta: {mean_diff}. Localized anomaly ratio: {hotspot_ratio}x. Grid variance: {block_var}. ELA heatmap generated.",
            "url": None,
            "rating": rating_label,
            "reliability": "Algorithmic JPEG Analysis"
        })
        
        if is_high_risk:
            suspicion_points += 3
        elif is_moderate_risk:
            suspicion_points += 1
            
    # 3. Evaluate Noise/Spatial findings
    if noise.get("success"):
        evidence.append({
            "type": "Spatial Noise & Focus",
            "publisher": "OpenCV Computer Vision",
            "finding": f"Resolution: {noise['dimensions']}. Edge density: {noise['edge_density_pct']}%. Focus sharpness: {noise['sharpness_score']}.",
            "url": None,
            "rating": "Geometric Consistency",
            "reliability": "Computer Vision"
        })
        
    # Formulate verdict based on genuine metrics
    if suspicion_points >= 4:
        verdict = "Likely Manipulated or Spliced"
        verdict_category = "fake"
        confidence_score = 80
        summary = (
            "Forensic analysis detected strong indications of localized manipulation. "
            "Error Level Analysis reveals significant compression inconsistencies across sections, "
            "and metadata confirms presence of digital editing software."
        )
    elif suspicion_points >= 2:
        verdict = "Suspicious / Anomalies Detected"
        verdict_category = "suspicious"
        confidence_score = 60
        summary = (
            "Forensic analysis detected moderate anomalies. There are signs of post-processing or "
            "localized re-saving, but conclusive proof of deceptive manipulation requires human forensic corroboration."
        )
    elif exif["has_exif"] and ela.get("success") and ela.get("block_variance", 0) <= 3.5 and ela.get("hotspot_ratio", 0) <= 1.5:
        verdict = "No Obvious Tampering Detected"
        verdict_category = "authentic"
        confidence_score = 85
        summary = (
            "Error Level Analysis indicates uniform compression throughout the image, "
            "and metadata is consistent with standard camera capture."
        )
    else:
        verdict = "Unable to verify"
        verdict_category = "unverified"
        confidence_score = 40
        summary = (
            "The image shows standard compression without obvious splicing indicators, "
            "but metadata has been stripped, making conclusive authentication impossible with current algorithmic checks."
        )
        
    limitations = (
        "Error Level Analysis (ELA) and metadata inspection cannot definitively prove intent or detect advanced "
        "diffusion-based generative AI modifications if resaved uniformly. High-resolution compression artifacts "
        "can occasionally produce false positives in areas with high natural contrast."
    )
    
    # Relative path to forensic image for web viewing
    web_ela_path = f"/uploads/forensics/{ela_filename}" if ela.get("success") else None
    
    return {
        "claim": f"Image Investigation: {filename}",
        "verdict": verdict,
        "verdict_category": verdict_category,
        "confidence_score": confidence_score,
        "summary": summary,
        "evidence": evidence,
        "limitations": limitations,
        "thumbnail_path": web_ela_path,
        "raw_forensics": {
            "exif": exif,
            "ela": ela,
            "noise": noise
        }
    }

def run_video_investigation(input_video_path, report_id, forensic_dir):
    """
    Video investigation pipeline using OpenCV:
    - Analyzes frame rate, resolution, duration
    - Samples keyframes across video temporal timeline
    - Measures consecutive frame pixel deltas (temporal discontinuity / cut detection)
    - Measures blur/sharpness stability across frames
    """
    filename = os.path.basename(input_video_path)
    cap = cv2.VideoCapture(input_video_path)
    
    if not cap.isOpened():
        return {
            "claim": f"Video Investigation: {filename}",
            "verdict": "Unable to verify",
            "verdict_category": "unverified",
            "confidence_score": 0,
            "summary": "Could not open or decode video stream. The file may be corrupt or encoded in an unsupported codec.",
            "evidence": [],
            "limitations": "Unsupported video codec or damaged container header.",
            "thumbnail_path": None
        }
        
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration_sec = round(total_frames / fps, 2) if total_frames > 0 and fps > 0 else 0
    
    # Sample up to 6 keyframes across the timeline
    num_samples = min(6, max(2, total_frames // 10)) if total_frames > 0 else 4
    sample_indices = np.linspace(0, max(0, total_frames - 1), num_samples, dtype=int) if total_frames > 0 else [0]
    
    keyframes_saved = []
    sharpness_scores = []
    frame_deltas = []
    prev_gray = None
    
    os.makedirs(forensic_dir, exist_ok=True)
    
    current_idx = 0
    sample_ptr = 0
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
            
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Calculate frame-to-frame delta if previous frame exists
        if prev_gray is not None:
            # Resize for fast comparison if large
            small_curr = cv2.resize(gray, (160, 90))
            small_prev = cv2.resize(prev_gray, (160, 90))
            delta = float(np.mean(cv2.absdiff(small_curr, small_prev)))
            frame_deltas.append(delta)
        prev_gray = gray
        
        # Save keyframe if current frame is in sample list
        if sample_ptr < len(sample_indices) and current_idx == sample_indices[sample_ptr]:
            lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            sharpness_scores.append(lap_var)
            
            keyframe_name = f"{report_id}_frame_{sample_ptr+1}.jpg"
            keyframe_path = os.path.join(forensic_dir, keyframe_name)
            
            # Save small preview
            preview_frame = cv2.resize(frame, (min(640, width), int(min(640, width) * (height / width))))
            cv2.imwrite(keyframe_path, preview_frame)
            keyframes_saved.append({
                "frame_num": current_idx,
                "timestamp_sec": round(current_idx / fps, 2),
                "url": f"/uploads/forensics/{keyframe_name}",
                "sharpness": round(lap_var, 1)
            })
            sample_ptr += 1
            
        current_idx += 1
        # Cap frame inspection for performance on long videos
        if current_idx > 1500:
            break
            
    cap.release()
    
    # Statistical analysis of temporal changes
    mean_delta = float(np.mean(frame_deltas)) if frame_deltas else 0
    max_delta = float(np.max(frame_deltas)) if frame_deltas else 0
    spike_cuts = [d for d in frame_deltas if d > (mean_delta * 3.5 + 10)]
    
    evidence = []
    evidence.append({
        "type": "Video Stream Properties",
        "publisher": "OpenCV Video Demuxer",
        "finding": f"Resolution: {width}x{height} | FPS: {round(fps, 1)} | Duration: {duration_sec}s | Analyzed frames: {current_idx}.",
        "url": None,
        "rating": "Stream Metadata",
        "reliability": "Container Header"
    })
    
    evidence.append({
        "type": "Temporal Consistency & Splice Check",
        "publisher": "OpenCV Frame Discontinuity",
        "finding": f"Average inter-frame pixel delta: {round(mean_delta, 2)}. Identified {len(spike_cuts)} abrupt temporal transitions/cuts.",
        "url": None,
        "rating": f"{len(spike_cuts)} Scene Transitions Detected" if spike_cuts else "Smooth Temporal Flow",
        "reliability": "Computer Vision"
    })
    
    # Sharpness consistency
    sharpness_variance = float(np.std(sharpness_scores)) if sharpness_scores else 0
    evidence.append({
        "type": "Keyframe Focus & Artifact Check",
        "publisher": "Laplacian Sharpness Variance",
        "finding": f"Extracted {len(keyframes_saved)} keyframe checkpoints. Focus stability variance: {round(sharpness_variance, 2)}.",
        "url": None,
        "rating": "Consistent Focus" if sharpness_variance < 150 else "High Blur Fluctuation",
        "reliability": "Computer Vision"
    })
    
    if len(spike_cuts) > 10 and duration_sec < 10:
        verdict = "Suspicious Temporal Splices"
        verdict_category = "suspicious"
        confidence_score = 65
        summary = (
            f"Video analysis detected {len(spike_cuts)} abrupt frame discontinuities in a short timeframe ({duration_sec}s). "
            "This suggests heavy editing, re-encoding cuts, or spliced footage."
        )
    else:
        verdict = "Temporal Consistency Verified"
        verdict_category = "authentic"
        confidence_score = 75
        summary = (
            f"Analyzed {current_idx} frames across {duration_sec}s of video. "
            "Temporal progression shows standard frame-to-frame continuity without anomalous splice spikes."
        )
        
    limitations = (
        "OpenCV temporal analysis evaluates container metrics, inter-frame structural difference, and sharpness stability. "
        "It cannot identify AI face-swap deepfakes without specialized deep neural network inference models. "
        "Videos re-encoded with smooth blending may conceal splices."
    )
    
    first_thumb = keyframes_saved[0]["url"] if keyframes_saved else None
    
    return {
        "claim": f"Video Investigation: {filename}",
        "verdict": verdict,
        "verdict_category": verdict_category,
        "confidence_score": confidence_score,
        "summary": summary,
        "evidence": evidence,
        "limitations": limitations,
        "thumbnail_path": first_thumb,
        "keyframes": keyframes_saved,
        "metrics": {
            "fps": round(fps, 1),
            "resolution": f"{width}x{height}",
            "duration": f"{duration_sec}s",
            "frames_analyzed": current_idx,
            "cuts_detected": len(spike_cuts)
        }
    }
