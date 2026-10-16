"""
Truth Shield MVP - Main Application Server
Flask Web Application for Investigating News, Images, and Videos.
"""
import os
import uuid
from flask import (
    Flask, render_template, request, redirect,
    url_for, jsonify, send_from_directory, flash, abort
)
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from database.db import save_report, get_report, get_recent_reports, init_db, add_confirmation, get_confirmations_for_report
from services.factcheck import verify_news_claim
from services.forensics import run_image_investigation, run_video_investigation

# Base paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
TEMP_FOLDER = os.path.join(UPLOAD_FOLDER, "temp")
FORENSIC_FOLDER = os.path.join(UPLOAD_FOLDER, "forensics")

os.makedirs(TEMP_FOLDER, exist_ok=True)
os.makedirs(FORENSIC_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "truth-shield-dev-key-2026")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("MAX_CONTENT_LENGTH", 50 * 1024 * 1024)) # 50 MB max

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "bmp"}
ALLOWED_VIDEO_EXTENSIONS = {"mp4", "mov", "avi", "webm", "mkv"}

def allowed_file(filename, allowed_set):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_set

@app.route("/")
def index():
    """Renders the Truth Shield homepage with checkers and recent reports."""
    recent = get_recent_reports(limit=8)
    return render_template("index.html", recent_reports=recent)

@app.route("/analyze/news", methods=["POST"])
def analyze_news():
    """Handles news headline and claim verification."""
    claim = request.form.get("claim", "").strip()
    source_url = request.form.get("source_url", "").strip()
    
    if not claim:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
            return jsonify({"error": "Please provide a news claim or headline to investigate."}), 400
        flash("Please enter a valid news claim or headline.", "warning")
        return redirect(url_for("index"))
        
    # Run fact checking pipeline
    result = verify_news_claim(claim, source_url)
    
    # Save report to SQLite
    report_id = save_report(
        claim_or_title=claim,
        media_type="news",
        verdict=result["verdict"],
        verdict_category=result["verdict_category"],
        confidence_score=result["confidence_score"],
        summary=result["summary"],
        evidence_data=result["evidence"],
        limitations=result["limitations"],
        thumbnail_path=None
    )
    
    if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
        return jsonify({
            "success": True,
            "report_id": report_id,
            "redirect_url": url_for("view_report", report_id=report_id)
        })
        
    return redirect(url_for("view_report", report_id=report_id))

@app.route("/analyze/image", methods=["POST"])
def analyze_image():
    """Handles image upload and forensic investigation."""
    if "image_file" not in request.files:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"error": "No image file provided."}), 400
        flash("No image file was uploaded.", "danger")
        return redirect(url_for("index"))
        
    file = request.files["image_file"]
    if file.filename == "":
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"error": "No image selected."}), 400
        flash("No image selected.", "warning")
        return redirect(url_for("index"))
        
    if not allowed_file(file.filename, ALLOWED_IMAGE_EXTENSIONS):
        msg = f"Invalid file type. Allowed formats: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"error": msg}), 400
        flash(msg, "danger")
        return redirect(url_for("index"))
        
    orig_filename = secure_filename(file.filename) or "image.jpg"
    unique_prefix = uuid.uuid4().hex[:8].upper()
    report_id = f"TS-{unique_prefix}"
    
    # Save temporary file for analysis
    temp_ext = orig_filename.rsplit(".", 1)[1].lower() if "." in orig_filename else "jpg"
    temp_filename = f"{report_id}_orig.{temp_ext}"
    temp_file_path = os.path.join(TEMP_FOLDER, temp_filename)
    file.save(temp_file_path)
    
    try:
        # Also save a scaled web preview thumbnail so the user can see original vs ELA side-by-side
        thumb_filename = f"{report_id}_preview.jpg"
        thumb_path = os.path.join(FORENSIC_FOLDER, thumb_filename)
        from PIL import Image
        with Image.open(temp_file_path) as im:
            rgb_im = im.convert("RGB")
            rgb_im.thumbnail((800, 800))
            rgb_im.save(thumb_path, "JPEG", quality=85)
            
        # Run forensic investigation
        result = run_image_investigation(temp_file_path, report_id, FORENSIC_FOLDER)
        
        # Package evidence with original preview
        evidence_data = result["evidence"]
        evidence_data.append({
            "type": "Preview Asset",
            "publisher": "Truth Shield Storage",
            "finding": f"Analyzed file '{orig_filename}'.",
            "url": f"/uploads/forensics/{thumb_filename}",
            "rating": "Asset Thumbnail",
            "reliability": "Local Upload"
        })
        
        # Save to database
        save_report(
            claim_or_title=f"Image: {orig_filename}",
            media_type="image",
            verdict=result["verdict"],
            verdict_category=result["verdict_category"],
            confidence_score=result["confidence_score"],
            summary=result["summary"],
            evidence_data=evidence_data,
            limitations=result["limitations"],
            thumbnail_path=f"/uploads/forensics/{thumb_filename}"
        )
        
    finally:
        # Prompt requirement: Delete temporary uploads when processing is complete
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as e:
                print(f"Cleanup note: {e}")
                
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({
            "success": True,
            "report_id": report_id,
            "redirect_url": url_for("view_report", report_id=report_id)
        })
        
    return redirect(url_for("view_report", report_id=report_id))

@app.route("/analyze/video", methods=["POST"])
def analyze_video():
    """Handles video upload and temporal forensic investigation."""
    if "video_file" not in request.files:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"error": "No video file provided."}), 400
        flash("No video file uploaded.", "danger")
        return redirect(url_for("index"))
        
    file = request.files["video_file"]
    if file.filename == "":
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"error": "No video selected."}), 400
        flash("No video selected.", "warning")
        return redirect(url_for("index"))
        
    if not allowed_file(file.filename, ALLOWED_VIDEO_EXTENSIONS):
        msg = f"Invalid file type. Allowed formats: {', '.join(ALLOWED_VIDEO_EXTENSIONS)}"
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"error": msg}), 400
        flash(msg, "danger")
        return redirect(url_for("index"))
        
    orig_filename = secure_filename(file.filename) or "video.mp4"
    unique_prefix = uuid.uuid4().hex[:8].upper()
    report_id = f"TS-{unique_prefix}"
    
    # Save temporary file for analysis
    temp_ext = orig_filename.rsplit(".", 1)[1].lower() if "." in orig_filename else "mp4"
    temp_filename = f"{report_id}_orig.{temp_ext}"
    temp_file_path = os.path.join(TEMP_FOLDER, temp_filename)
    file.save(temp_file_path)
    
    try:
        # Run video investigation
        result = run_video_investigation(temp_file_path, report_id, FORENSIC_FOLDER)
        
        # Save to database
        save_report(
            claim_or_title=f"Video: {orig_filename}",
            media_type="video",
            verdict=result["verdict"],
            verdict_category=result["verdict_category"],
            confidence_score=result["confidence_score"],
            summary=result["summary"],
            evidence_data=result["evidence"],
            limitations=result["limitations"],
            thumbnail_path=result.get("thumbnail_path")
        )
        
    finally:
        # Prompt requirement: Delete temporary uploads when processing is complete
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as e:
                print(f"Cleanup note: {e}")
                
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({
            "success": True,
            "report_id": report_id,
            "redirect_url": url_for("view_report", report_id=report_id)
        })
        
    return redirect(url_for("view_report", report_id=report_id))

@app.route("/analyze/demo", methods=["POST"])
def analyze_demo():
    """Provides instant 1-click testing using built-in verified sample cases."""
    import shutil
    sample_type = request.form.get("sample_type", "")
    
    if sample_type == "news_mars":
        claim = "NASA discovers alien city on Mars with pyramids and canals"
        res = verify_news_claim(claim)
        rep_id = save_report(claim, "news", res["verdict"], res["verdict_category"], res["confidence_score"], res["summary"], res["evidence"], res["limitations"])
        return jsonify({"success": True, "report_id": rep_id, "redirect_url": url_for("view_report", report_id=rep_id)})
        
    elif sample_type == "news_ev":
        claim = "Electric vehicles catch fire 10 times more frequently than gasoline cars"
        res = verify_news_claim(claim)
        rep_id = save_report(claim, "news", res["verdict"], res["verdict_category"], res["confidence_score"], res["summary"], res["evidence"], res["limitations"])
        return jsonify({"success": True, "report_id": rep_id, "redirect_url": url_for("view_report", report_id=rep_id)})
        
    elif sample_type in ["image_auth", "image_spliced"]:
        source_name = "authentic_photo.jpg" if sample_type == "image_auth" else "manipulated_photo.jpg"
        source_path = os.path.join(BASE_DIR, "static", "samples", source_name)
        if not os.path.exists(source_path):
            return jsonify({"error": "Sample asset not found"}), 404
            
        report_id = f"TS-{uuid.uuid4().hex[:8].upper()}"
        temp_path = os.path.join(TEMP_FOLDER, f"{report_id}_demo.jpg")
        shutil.copyfile(source_path, temp_path)
        
        # Save preview thumbnail
        thumb_filename = f"{report_id}_preview.jpg"
        thumb_path = os.path.join(FORENSIC_FOLDER, thumb_filename)
        from PIL import Image
        with Image.open(temp_path) as im:
            rgb_im = im.convert("RGB")
            rgb_im.thumbnail((800, 800))
            rgb_im.save(thumb_path, "JPEG", quality=85)
            
        result = run_image_investigation(temp_path, report_id, FORENSIC_FOLDER)
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
        evidence_data = result["evidence"]
        evidence_data.append({
            "type": "Demo Sample Asset",
            "publisher": "Truth Shield Preset",
            "finding": f"Analyzed preset sample: '{source_name}'.",
            "url": f"/uploads/forensics/{thumb_filename}",
            "rating": "Preset Asset",
            "reliability": "Verification Showcase"
        })
        
        save_report(
            claim_or_title=f"Sample Image ({'Authentic' if sample_type == 'image_auth' else 'Manipulated'})",
            media_type="image",
            verdict=result["verdict"],
            verdict_category=result["verdict_category"],
            confidence_score=result["confidence_score"],
            summary=result["summary"],
            evidence_data=evidence_data,
            limitations=result["limitations"],
            thumbnail_path=f"/uploads/forensics/{thumb_filename}"
        )
        return jsonify({"success": True, "report_id": report_id, "redirect_url": url_for("view_report", report_id=report_id)})
        
    elif sample_type == "video_sample":
        source_path = os.path.join(BASE_DIR, "static", "samples", "sample_clip.mp4")
        if not os.path.exists(source_path):
            return jsonify({"error": "Sample video asset not found"}), 404
            
        report_id = f"TS-{uuid.uuid4().hex[:8].upper()}"
        temp_path = os.path.join(TEMP_FOLDER, f"{report_id}_demo.mp4")
        shutil.copyfile(source_path, temp_path)
        
        result = run_video_investigation(temp_path, report_id, FORENSIC_FOLDER)
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
        save_report(
            claim_or_title="Sample Video (Temporal Motion Analysis)",
            media_type="video",
            verdict=result["verdict"],
            verdict_category=result["verdict_category"],
            confidence_score=result["confidence_score"],
            summary=result["summary"],
            evidence_data=result["evidence"],
            limitations=result["limitations"],
            thumbnail_path=result.get("thumbnail_path")
        )
        return jsonify({"success": True, "report_id": report_id, "redirect_url": url_for("view_report", report_id=report_id)})
        
    return jsonify({"error": "Unknown sample type"}), 400

@app.route("/report/<report_id>")
def view_report(report_id):
    """Renders the detailed forensic report page."""
    report = get_report(report_id)
    if not report:
        return render_template("results.html", error=f"Report '{report_id}' was not found."), 404
    return render_template("results.html", report=report)

@app.route("/report/<report_id>/json")
def download_report_json(report_id):
    """Exports the report data as JSON."""
    report = get_report(report_id)
    if not report:
        abort(404)
    return jsonify(report)

@app.route("/api/reports")
def api_reports():
    """Returns recent reports in JSON format."""
    recent = get_recent_reports(limit=10)
    return jsonify({"reports": recent})

@app.route("/report/<report_id>/confirm", methods=["POST"])
def confirm_report(report_id):
    """Handles submission of an official peer investigator confirmation."""
    report = get_report(report_id)
    if not report:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
            return jsonify({"error": "Report not found."}), 404
        flash("Report not found.", "danger")
        return redirect(url_for("index"))
        
    reviewer_name = request.form.get("reviewer_name", "").strip()
    reviewer_role = request.form.get("reviewer_role", "").strip()
    organization = request.form.get("organization", "").strip()
    confirmation_status = request.form.get("confirmation_status", "").strip()
    peer_review_notes = request.form.get("peer_review_notes", "").strip()
    methodology = request.form.getlist("methodology[]") or request.form.getlist("methodology")
    
    if not reviewer_name or not reviewer_role or not confirmation_status or not peer_review_notes:
        err_msg = "Please fill in all required confirmation fields (Name, Role, Status, and Review Notes)."
        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
            return jsonify({"error": err_msg}), 400
        flash(err_msg, "warning")
        return redirect(url_for("view_report", report_id=report_id))
        
    conf_result = add_confirmation(
        report_id=report_id,
        reviewer_name=reviewer_name,
        reviewer_role=reviewer_role,
        organization=organization or "Independent Investigator",
        confirmation_status=confirmation_status,
        peer_review_notes=peer_review_notes,
        methodology_checklist=methodology
    )
    
    if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
        return jsonify({
            "success": True,
            "confirmation_id": conf_result["confirmation_id"],
            "digital_signature": conf_result["digital_signature"],
            "redirect_url": url_for("view_report", report_id=report_id) + "#confirmation-section"
        })
        
    flash("Peer investigator confirmation recorded with digital cryptographic seal.", "success")
    return redirect(url_for("view_report", report_id=report_id) + "#confirmation-section")

@app.route("/report/<report_id>/certificate")
def view_certificate(report_id):
    """Renders an official, printable Certificate of Verification with digital seal."""
    report = get_report(report_id)
    if not report:
        return render_template("results.html", error=f"Report '{report_id}' was not found."), 404
    return render_template("certificate.html", report=report)

@app.route("/uploads/forensics/<path:filename>")
def serve_forensic_file(filename):
    """Serves forensic artifacts (ELA images, video keyframe thumbnails)."""
    return send_from_directory(FORENSIC_FOLDER, filename)

@app.errorhandler(413)
def request_entity_too_large(error):
    msg = "File exceeds the 50MB maximum upload limit. Please upload a smaller file."
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"error": msg}), 413
    return render_template("results.html", error=msg), 413

@app.errorhandler(404)
def not_found_error(error):
    return render_template("results.html", error="The requested page or report does not exist."), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template("results.html", error="An internal server error occurred during investigation."), 500

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    print(f"[Truth Shield] MVP server running at http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=True)
