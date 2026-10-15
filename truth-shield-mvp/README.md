# 🛡️ Truth Shield MVP — Media & News Verification Intelligence

> **Truth Shield** is an open-source forensic web application built to help journalists, researchers, and everyday citizens investigate questionable news claims, analyze images for digital splicing/tampering, and inspect video clips for temporal anomalies.

---

## 🌟 Key Features

1. **📰 News & Claim Checker**:
   - Analyzes headlines and statements against verified International Fact-Checking Network (IFCN) repositories (Snopes, PolitiFact, Reuters, etc.).
   - Cross-references Wikipedia knowledge graph entries.
   - Evaluates linguistic markers, sensationalist clickbait phrasing, and excessive capitalization.
   - Strictly enforces **"Unable to verify"** when evidence is insufficient or unindexed.

2. **🖼️ Image Forensics (Error Level Analysis - ELA)**:
   - **Error Level Analysis (ELA)**: Resaves image at 90% JPEG quality to compute pixel-level compression deltas, visually highlighting spliced foreign elements that compress at differing rates.
   - **EXIF Metadata Inspection**: Extracts camera make/model, original timestamps, and flags editing software tags (e.g. Adobe Photoshop, GIMP, Canva, Stable Diffusion).
   - **OpenCV Spatial Analysis**: Measures Laplacian focus variance and edge density.
   - Interactive side-by-side comparison slider between the original image and the ELA heatmap.

3. **🎥 Video Temporal Consistency**:
   - Extracts and displays chronological keyframes across the video stream.
   - Measures inter-frame pixel deltas to locate abrupt temporal splice cuts or dropped sequences.
   - Evaluates focus and blur stability across frames using OpenCV.

4. **📑 Evidence Dossier & Audit Trail**:
   - Generates persistent reports with unique IDs (e.g. `TS-A7B8C9D0`).
   - Stores report metadata and findings in a local SQLite database (`database/truth_shield.db`).
   - One-click **JSON Export**, **Printable Dossier**, and **Shareable URL**.

5. **🔒 Security, Privacy & Resource Cleanup**:
   - Validates file extensions and enforces size limits (16MB image / 50MB video).
   - **Deletes temporary uploaded raw files** immediately after forensic metrics and preview thumbnails are computed.
   - Built-in environment variable configuration (`.env`).

---

## 🏗️ Architecture & Project Structure

```text
truth-shield-mvp/
├── app.py                      # Flask backend application & routing
├── requirements.txt            # Python dependencies
├── .env                        # Environment configuration (API keys, ports)
├── README.md                   # Documentation & setup instructions
├── create_sample_assets.py     # Script generating demo test images & video
├── database/
│   ├── db.py                   # SQLite schema & report persistence
│   └── truth_shield.db         # Auto-generated SQLite database
├── services/
│   ├── factcheck.py            # News verification & fact-check integration
│   └── forensics.py            # Pillow & OpenCV image/video forensic engine
├── static/
│   ├── style.css               # Vanilla CSS design system (green, dark-green, white)
│   ├── script.js               # Client-side tab navigation, upload drag & drop, radar
│   ├── images/                 # Logo and icon assets
│   └── samples/                # Preset sample test media
├── templates/
│   ├── index.html              # Homepage with 3-tab forensic terminal
│   └── results.html            # Evidence dossier & forensic report view
└── uploads/
    ├── temp/                   # Temporary directory (auto-purged after analysis)
    └── forensics/              # Generated ELA maps & keyframe thumbnails
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- Python 3.10+ installed on your computer.
- Terminal / PowerShell.

### 2. Install Dependencies
Open your terminal in the `truth-shield-mvp` directory and run:

```bash
pip install -r requirements.txt
```

### 3. Start the Application
Run the Flask server:

```bash
python app.py
```

You should see:
```text
🛡️ Truth Shield MVP running at http://127.0.0.1:5000
 * Serving Flask app 'app'
 * Debug mode: on
```

### 4. Open in Your Browser
Navigate to:
```text
http://127.0.0.1:5000
```

---

## 🧪 Testing with Built-in Demo Presets

Truth Shield includes pre-packaged test cases accessible directly from the homepage with a single click:

- **🪐 Mars Alien City Claim**: Demonstrates debunked news claim cross-referencing and fact-checker rating synthesis.
- **⚡ EV Fire Misinformation**: Demonstrates statistical context and factual reference retrieval.
- **🟢 Authentic Photo Sample**: Demonstrates clean ELA compression with low quadrant variance.
- **🔴 Spliced / Tampered Photo Sample**: Demonstrates Error Level Analysis highlighting a foreign-compression spliced patch.
- **🎥 Video Stream Sample**: Demonstrates OpenCV frame demuxing, keyframe timeline extraction, and temporal delta measurement.

---

## 🔑 Optional API Configuration

To enable direct live queries against the Google Fact Check Tools API:
1. Obtain a free API key at [Google Fact Check Tools API](https://developers.google.com/fact-check/tools/api).
2. Open `.env` in the `truth-shield-mvp/` folder:
   ```env
   GOOGLE_FACTCHECK_API_KEY=your_google_api_key_here
   ```
3. Restart `python app.py`.

*Note: If no API key is provided, Truth Shield automatically utilizes open-source fact-checking cross-referencing and encyclopedia verification.*

---

## ⚖️ Methodological Disclaimers & Ethics

- **Zero Hallucination Policy**: Truth Shield will never label content as "100% Real" or "100% Fake" without empirical proof. If evidence is ambiguous or unavailable, the system states **"Unable to verify"**.
- **Not a "Magic AI"**: Media forensics relies on empirical mathematics (JPEG discrete cosine transform re-compression residuals, EXIF tags, frame-to-frame pixel differences). Deepfake detection requires specialized deep neural networks, and uniform re-compression may mask certain splices.

---

## 📄 License
Open source under the MIT License.
