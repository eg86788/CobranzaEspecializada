# app/blueprints/directorio.py
# Editor del directorio jerárquico: alta/edición de personas y listado.
# Nota: requiere tabla 'directorio_personas' con las columnas referidas.

import os
from flask import Blueprint, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from ..db_legacy import fetchall, execute

directorio_bp = Blueprint("directorio", __name__)

@directorio_bp.route("/", methods=["GET"])
def ver():
    return render_template("directorio.html")

@directorio_bp.route("/editar", methods=["GET", "POST"])
def editar():
    if request.method == "POST":
        foto = request.files.get("foto")
        imagen = None
        if foto and foto.filename:
            nombre = secure_filename(foto.filename)
            ruta = os.path.join("static/images", nombre)
            os.makedirs(os.path.dirname(ruta), exist_ok=True)
            foto.save(ruta)
            imagen = nombre

        execute(
            """
            INSERT INTO directorio_personas
            (nombre_completo, correo, ubicacion, puesto, productos, imagen, superior_id)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                request.form.get("nombre"),
                request.form.get("correo"),
                request.form.get("ubicacion"),
                request.form.get("puesto"),
                request.form.get("productos"),
                imagen,
                request.form.get("superior_id") or None,
            ),
        )
        flash("Miembro agregado o actualizado correctamente", "success")
        return redirect(url_for("directorio.editar"))

    personas = fetchall("SELECT id, nombre_completo FROM directorio_personas ORDER BY nombre_completo")
    return render_template("editar_directorio.html", personas=personas)
