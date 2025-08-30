# app/utils/session_utils.py
# Utilidades para manejo de sesión y normalización de datos.

from flask import session

DEPENDENCIAS = ("unidades", "cuentas", "usuarios", "contactos", "rdc_reporte")

def limpiar_sesion():
    for k in ("frame1",) + DEPENDENCIAS:
        session.pop(k, None)

def limpiar_dependientes():
    for k in DEPENDENCIAS:
        session.pop(k, None)

def hay_dependientes():
    return bool(session.get("unidades") or session.get("cuentas") or session.get("usuarios") or session.get("contactos"))

def normalizar_unidad(form_dict):
    """Unifica nombres de claves para que BD y vistas no se contradigan."""
    # Del formulario: "tipo_servicio_unidad" => guardamos como 'tipo_unidad' y 'tipo_servicio' según tu uso en BD
    return {
        "numero_terminal_sef": form_dict.get("numero_terminal_sef") or None,
        "nombre_unidad": form_dict.get("nombre_unidad"),
        "cpae": form_dict.get("cpae"),
        "origen_unidad": form_dict.get("origen_unidad"),
        # Se usan estos dos nombres de forma consistente en BD:
        "tipo_unidad": form_dict.get("tipo_servicio_unidad"),  # mapeo al nombre esperado por INSERT
        "tipo_servicio": form_dict.get("tipo_servicio_unidad"),  # mismo valor si tu BD lo requiere
        "empresa_traslado": form_dict.get("empresa_traslado"),
        "calle_numero": form_dict.get("calle_numero"),
        "colonia": form_dict.get("colonia"),
        "municipio_id": form_dict.get("municipio_id"),
        "estado": form_dict.get("estado"),
        "codigo_postal": form_dict.get("codigo_postal"),
        "terminal_integradora": form_dict.get("terminal_integradora"),
        "terminal_dotacion_centralizada": form_dict.get("terminal_dotacion_centralizada"),
        "terminal_certificado_centralizada": form_dict.get("terminal_certificado_centralizada"),
    }

from datetime import datetime

MESES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio",
    7: "julio", 8: "agosto", 9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
}

def fecha_a_texto(fecha_str):
    try:
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d")
    except:
        try:
            fecha = datetime.strptime(fecha_str, "%d/%m/%Y")
        except:
            return fecha_str  # si falla, retorna sin formato

    dia = fecha.day
    mes = MESES[fecha.month]
    año = fecha.year

    return f"a los {dia} días del mes de {mes} del año {año}"

