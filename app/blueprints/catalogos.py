from flask import Blueprint, render_template, request, redirect, url_for
from app.extensions import db
from app.models import (
    CatalogoCPAE,
    CatalogoETV,
    CatalogoProcesadora,
    CatalogoEntidad,
    CatalogoMunicipio
)


catalogos_bp = Blueprint(
    "catalogos",
    __name__,
    url_prefix="/catalogos"
)

@catalogos_bp.route("/")
def ver_catalogos():
    return render_template("catalogos/index.html")


# ==========================================
# CPAE
# ==========================================

@catalogos_bp.route("/cpae", methods=["GET", "POST"])
def cpae_admin():

    if request.method == "POST":
        nuevo = CatalogoCPAE(
            clave=request.form.get("clave"),
            descripcion=request.form.get("descripcion"),
            abreviatura=request.form.get("abreviatura")
        )
        db.session.add(nuevo)
        db.session.commit()
        return redirect(url_for("catalogos.cpae_admin"))

    registros = CatalogoCPAE.query.order_by(CatalogoCPAE.clave).all()
    return render_template("catalogos/cpae.html", registros=registros)

from app.extensions import db

@catalogos_bp.route("/buscar/cpae")
def buscar_cpae():
    q = request.args.get("q", "")

    resultados = CatalogoCPAE.query.filter(
        CatalogoCPAE.descripcion.ilike(f"%{q}%")
    ).limit(10).all()

    return {
        "results": [
            {"id": r.id, "text": f"{r.clave} - {r.descripcion}"}
            for r in resultados
        ]
    }

@catalogos_bp.route("/municipios/<int:entidad_id>")
def municipios_por_entidad(entidad_id):

    municipios = CatalogoMunicipio.query.filter_by(
        entidad_id=entidad_id
    ).all()

    return {
        "results": [
            {"id": m.id, "text": m.nombre}
            for m in municipios
        ]
    }

@catalogos_bp.route("/buscar/etv")
def buscar_etv():
    q = request.args.get("q", "")
    resultados = CatalogoETV.query.filter(
        CatalogoETV.nombre.ilike(f"%{q}%")
    ).limit(10).all()

    return {
        "results": [{"id": r.id, "text": r.nombre} for r in resultados]
    }


@catalogos_bp.route("/buscar/procesadora")
def buscar_procesadora():
    q = request.args.get("q", "")
    etv_id = request.args.get("etv_id")
    cpae_id = request.args.get("cpae_id")

    query = CatalogoProcesadora.query

    if etv_id:
        query = query.filter_by(etv_id=etv_id)

    if cpae_id:
        query = query.filter(CatalogoProcesadora.cpae_id == cpae_id)

    if q:
        query = query.filter(CatalogoProcesadora.nombre.ilike(f"%{q}%"))

    resultados = query.limit(10).all()

    return {
        "results": [{"id": r.id, "text": r.nombre} for r in resultados]
    }
