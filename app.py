"""
Root entry point for Truth Shield MVP.
Allows launching the server from either the workspace root or the truth-shield-mvp directory.
"""
import os
import sys

# Change working directory to truth-shield-mvp
target_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "truth-shield-mvp")
os.chdir(target_dir)
sys.path.insert(0, target_dir)

from app import app, init_db

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    print(f"[Truth Shield] MVP server running at http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=True)
