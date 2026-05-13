from __future__ import annotations

from backend.app.ingest.loader import load_pdfs_from_sources


if __name__ == "__main__":
    count = load_pdfs_from_sources()
    print(f"Indexed {count} documents")
