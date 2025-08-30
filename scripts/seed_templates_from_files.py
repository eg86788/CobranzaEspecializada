# scripts/seed_templates_from_files.py
from pathlib import Path
from datetime import datetime
from app.db_legacy import conectar

FILES = {
  "finalizar": "finalizar.html",
  "anexo_usd14k": "anexo_usd14k.html",
  "contrato_tradicional": "contrato_tradicional.html",
  "contrato_electronico": "contrato_electronico.html",
}

root = Path(__file__).resolve().parents[1]  # carpeta del proyecto
tpl_dir = root / "templates"

with conectar() as conn, conn.cursor() as cur:
    for slug, fname in FILES.items():
        content = (tpl_dir / fname).read_text(encoding="utf-8")
        cur.execute("""
          INSERT INTO document_templates (slug,name,content_html,css,version,is_active,updated_by,updated_at)
          VALUES (%s,%s,%s,%s,1,TRUE,%s,%s)
        """, (slug, slug.replace("_"," ").title(), content, "", "seed@local", datetime.utcnow()))
    conn.commit()
print("Listo.")
