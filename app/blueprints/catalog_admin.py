from flask import Blueprint, render_template, request, redirect, url_for, abort
from app.models import (
    CatalogoCPAE,
    CatalogoETV,
    CatalogoProcesadora,
    CatalogoEntidad,
    CatalogoMunicipio,
    Producto
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

    # -------------------------
    # CREAR
    # -------------------------
    if request.method == "POST":
        data = {campo: request.form.get(campo) for campo in campos}
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
        filtros = [getattr(Modelo, c).ilike(f"%{q}%") for c in campos]
        query = query.filter(or_(*filtros))

    registros = query.order_by(Modelo.id).all()

    return render_template(
        "admin_catalogos/catalogo.html",
        titulo=config["titulo"],
        campos=campos,
        registros=registros,
        catalogo=catalogo
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
    db.session.delete(item)
    db.session.commit()

    return redirect(url_for("catalog_admin.administrar", catalogo=catalogo))
