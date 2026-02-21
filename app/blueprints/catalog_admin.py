from flask import Blueprint, render_template, request, redirect, url_for, abort
from app.models import (
    CatalogoCPAE,
    CatalogoETV,
    CatalogoProcesadora,
    CatalogoEntidad,
    CatalogoMunicipio,
    Producto,
    TarifaComisionProducto
)
from app.extensions import db
from app.auth.decorators import permiso_required
from sqlalchemy import or_


catalog_admin_bp = Blueprint(
    "catalog_admin",
    __name__,
    url_prefix="/admin/catalogos"
)


# =====================================================
# CONFIGURACIÓN DE CATÁLOGOS
# =====================================================
CATALOGOS = {
    "cpae": {
        "modelo": CatalogoCPAE,
        "campos": ["clave", "descripcion", "abreviatura"],
        "titulo": "CPAE"
    },
    "etv": {
        "modelo": CatalogoETV,
        "campos": ["nombre"],
        "titulo": "ETV"
    },
    "procesadoras": {
        "modelo": CatalogoProcesadora,
        "campos": ["clave", "nombre"],
        "titulo": "Procesadoras"
    },
    "entidades": {
        "modelo": CatalogoEntidad,
        "campos": ["clave_inegi", "nombre"],
        "titulo": "Entidades"
    },
    "municipios": {
        "modelo": CatalogoMunicipio,
        "campos": ["clave_inegi", "nombre"],
        "titulo": "Municipios"
    },
    "productos": {
        "modelo": Producto,
        "campos": ["code", "nombre", "descripcion"],
        "titulo": "Productos"
    }
    ,"tarifas_comision": {
        "modelo": TarifaComisionProducto,
        "campos": ["producto_id", "nombre_comision", "valor", "moneda", "activo"],
        "titulo": "Tarifas de Comisión por Producto"
    }
}


# =====================================================
# HUB
# =====================================================
@catalog_admin_bp.route("/")
@permiso_required("manage_catalogs")
def index():
    return render_template("admin_catalogos/main.html")


# =====================================================
# ADMINISTRADOR GENÉRICO
# =====================================================
@catalog_admin_bp.route("/<catalogo>", methods=["GET", "POST"])
@permiso_required("manage_catalogs")
def administrar(catalogo):

    if catalogo not in CATALOGOS:
        abort(404)

    config = CATALOGOS[catalogo]
    Modelo = config["modelo"]
    campos = config["campos"]
    editar_id = request.args.get("edit")

    # Ajustes especiales para Tarifas de Comisión
    opciones = {}
    if catalogo == "tarifas_comision":
        # Lista de productos para dropdown
        opciones["producto_id"] = Producto.query.order_by(Producto.nombre).all()

        # Lista fija de monedas
        opciones["moneda"] = ["MXN", "USD"]

    # -------------------------
    # EDITAR
    # -------------------------
    if editar_id:
        item = Modelo.query.get_or_404(editar_id)

        if request.method == "POST":
            from decimal import Decimal

            for campo in campos:
                if campo == "activo":
                    setattr(item, "activo", True if request.form.get("activo") else False)

                elif campo == "valor":
                    raw_valor = request.form.get("valor", "")
                    limpio = raw_valor.replace("$", "").replace(",", "").strip()
                    setattr(item, "valor", Decimal(limpio) if limpio else Decimal("0"))

                else:
                    setattr(item, campo, request.form.get(campo))

            db.session.commit()
            return redirect(url_for("catalog_admin.administrar", catalogo=catalogo))

    else:
        item = None

    # -------------------------
    # CREAR
    # -------------------------
    if request.method == "POST" and not editar_id:
        from decimal import Decimal

        data = {}
        for campo in campos:
            if campo == "activo":
                data["activo"] = True if request.form.get("activo") else False

            elif campo == "valor":
                raw_valor = request.form.get("valor", "")
                limpio = raw_valor.replace("$", "").replace(",", "").strip()
                data["valor"] = Decimal(limpio) if limpio else Decimal("0")

            else:
                data[campo] = request.form.get(campo)

        nuevo = Modelo(**data)
        db.session.add(nuevo)
        db.session.commit()
        return redirect(url_for("catalog_admin.administrar", catalogo=catalogo))

    # -------------------------
    # BUSCAR
    # -------------------------
    q = request.args.get("q")
    query = Modelo.query

    if q:
        from sqlalchemy import cast, String
        filtros = []

        for c in campos:
            columna = getattr(Modelo, c)

            # Solo aplicar ILIKE directamente a columnas tipo texto
            if hasattr(columna.type, "python_type") and columna.type.python_type == str:
                filtros.append(columna.ilike(f"%{q}%"))
            else:
                # Para numéricos y otros tipos, convertir a texto
                filtros.append(cast(columna, String).ilike(f"%{q}%"))

        query = query.filter(or_(*filtros))

    registros = query.order_by(Modelo.id).all()

    return render_template(
        "admin_catalogos/catalogo.html",
        titulo=config["titulo"],
        campos=campos,
        registros=registros,
        catalogo=catalogo,
        opciones=opciones if catalogo == "tarifas_comision" else {},
        item=item
    )


# =====================================================
# ELIMINAR
# =====================================================
@catalog_admin_bp.route("/<catalogo>/<int:item_id>/delete", methods=["POST"])
@permiso_required("manage_catalogs")
def eliminar(catalogo, item_id):

    if catalogo not in CATALOGOS:
        abort(404)

    Modelo = CATALOGOS[catalogo]["modelo"]

    item = Modelo.query.get_or_404(item_id)

    # Para tarifas de comisión hacemos baja lógica
    if catalogo == "tarifas_comision" and hasattr(item, "activo"):
        item.activo = False
    else:
        db.session.delete(item)

    db.session.commit()

    return redirect(url_for("catalog_admin.administrar", catalogo=catalogo))


# =====================================================
# REACTIVAR
# =====================================================
@catalog_admin_bp.route("/<catalogo>/<int:item_id>/reactivar", methods=["POST"])
@permiso_required("manage_catalogs")
def reactivar(catalogo, item_id):

    if catalogo not in CATALOGOS:
        abort(404)

    Modelo = CATALOGOS[catalogo]["modelo"]

    item = Modelo.query.get_or_404(item_id)

    # Solo aplica si el modelo tiene campo activo
    if hasattr(item, "activo"):
        item.activo = True
        db.session.commit()

    return redirect(url_for("catalog_admin.administrar", catalogo=catalogo))
