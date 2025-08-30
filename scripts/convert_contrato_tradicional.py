from pathlib import Path
import re
import html

# ruta al archivo original
SRC = Path("templates/contrato_tradicional.html").read_text(encoding="utf-8")

# 1) quita extends/bloques de jinja, nos quedamos con el cuerpo
def strip_jinja_wrappers(src: str) -> str:
    # elimina {% extends ... %} y los bloques de nivel superior
    src = re.sub(r'{%\s*extends\s+["\'][^"\']+["\']\s*%}\s*', '', src, flags=re.IGNORECASE)
    src = re.sub(r'{%\s*block\s+\w+\s*%}', '', src, flags=re.IGNORECASE)
    src = re.sub(r'{%\s*endblock\s*%}', '', src, flags=re.IGNORECASE)
    return src.strip()

# 2) extrae CSS de <style>…</style>
def extract_css(src: str):
    css_parts = re.findall(r'<style[^>]*>(.*?)</style>', src, flags=re.IGNORECASE|re.DOTALL)
    css = "\n\n".join(css_parts).strip()
    # elimina los <style> del HTML
    html_wo_css = re.sub(r'<style[^>]*>.*?</style>', '', src, flags=re.IGNORECASE|re.DOTALL)
    return html_wo_css, css

# 3) cambia rutas estáticas absolutas a url_for
def fix_static_paths(src: str) -> str:
    # src="/static/..." -> src="{{ url_for('static', filename='...') }}"
    src = re.sub(r'src="/static/([^"]+)"', r'src="{{ url_for(\'static\', filename=\'\1\') }}"', src)
    src = re.sub(r'href="/static/([^"]+)"', r'href="{{ url_for(\'static\', filename=\'\1\') }}"', src)
    return src

# 4) si quedó escapado, desescapa
def unescape_if_needed(s: str) -> str:
    return html.unescape(s)

# pipeline
body = strip_jinja_wrappers(SRC)
body, css = extract_css(body)
body = fix_static_paths(body)
body = unescape_if_needed(body).strip()

print("\n" + "="*80)
print("PEGAR EN CAMPO CONTENIDO (HTML + Jinja)")
print("="*80 + "\n")
print(body)

print("\n" + "="*80)
print("PEGAR EN CAMPO CSS")
print("="*80 + "\n")
print(css)
