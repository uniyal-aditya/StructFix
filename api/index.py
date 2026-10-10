"""Vercel Serverless Function entrypoint for StructFix."""

from pathlib import Path
import sys

# Ensure project root is in sys.path so 'structfix' package can be imported
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from structfix.web import create_app

app = create_app()

if __name__ == "__main__":
    app.run()
