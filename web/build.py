from pathlib import Path
import os

root = Path(__file__).resolve().parent
public = root / "public"
public.mkdir(parents=True, exist_ok=True)
html = (root / "index.html").read_text(encoding="utf-8")
api_url = os.getenv("UFCQUANT_API_URL", "https://YOUR-UFCQUANT-BACKEND.onrender.com").rstrip("/")
html = html.replace("__UFCQUANT_API_URL__", api_url)
(public / "index.html").write_text(html, encoding="utf-8")
print(f"Built UFCQuant static frontend into {public}; API URL={api_url}")
