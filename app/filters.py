from datetime import datetime

MESES = {1:"enero",2:"febrero",3:"marzo",4:"abril",5:"mayo",6:"junio",
         7:"julio",8:"agosto",9:"septiembre",10:"octubre",11:"noviembre",12:"diciembre"}

def fecha_a_texto(fecha_str: str) -> str:
    if not fecha_str:
        return ""
    fecha_str = fecha_str.strip()
    dt = None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            dt = datetime.strptime(fecha_str, fmt)
            break
        except ValueError:
            pass
    if not dt:
        return fecha_str  # no lo rompas si llega en otro formato
    return f"a los {dt.day} días del mes de {MESES[dt.month]} del año {dt.year}"

def register_filters(app):
    app.jinja_env.filters["fecha_a_texto"] = fecha_a_texto
    app.jinja_env.filters["FECHA_A_TEXTO"] = fecha_a_texto   # alias tolerante
