import re
from datetime import datetime

# ===============================
# NUMERO CLIENTE (10 dígitos)
# ===============================
def format_numero_cliente(value: str) -> str:
    if not value:
        return None

    value = re.sub(r"\D", "", value)

    if len(value) > 10:
        raise ValueError("Número de cliente máximo 10 dígitos")

    return value.zfill(10)


# ===============================
# NUMERO CONTRATO (12 dígitos)
# ===============================
def format_numero_contrato(value: str) -> str:
    if not value:
        return None

    value = re.sub(r"\D", "", value)

    if len(value) > 12:
        raise ValueError("Número de contrato máximo 12 dígitos")

    return value.zfill(12)


# ===============================
# CODIGO POSTAL (5 dígitos)
# ===============================
def format_codigo_postal(value: str) -> str:
    if not value:
        return None

    value = re.sub(r"\D", "", value)

    if len(value) > 5:
        raise ValueError("Código postal máximo 5 dígitos")

    return value.zfill(5)


# ===============================
# TELEFONO (10 dígitos)
# ===============================
def format_telefono(value: str) -> str:
    if not value:
        return None

    value = re.sub(r"\D", "", value)

    if len(value) != 10:
        raise ValueError("El teléfono debe tener 10 dígitos")

    return value


# ===============================
# EMAIL
# ===============================
def format_email(value: str) -> str:
    if not value:
        return None

    value = value.strip().lower()

    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    if not re.match(pattern, value):
        raise ValueError("Correo electrónico inválido")

    return value


# ===============================
# FECHA (DD/MM/YYYY)
# ===============================
def parse_fecha(value: str):
    if not value:
        return None

    try:
        return datetime.strptime(value, "%d/%m/%Y").date()
    except ValueError:
        raise ValueError("Formato de fecha inválido (DD/MM/YYYY)")
