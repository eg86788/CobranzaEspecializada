# app/blueprints/users_admin.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
from werkzeug.security import generate_password_hash
from app.extensions import db
from app.models import AdminUser, Permiso, RolePermiso

users_admin = Blueprint("users_admin", __name__, url_prefix="/admin/usuarios")

# Define los roles que maneja tu sistema
ROLES_DISPONIBLES = ["admin", "user"]

@users_admin.before_request
def admin_guard():
    if session.get("role") != "admin":
        flash("Acceso restringido: se requiere rol administrador.", "warning")
        return redirect(url_for("auth_admin.login", next=request.path))

# --------- Helpers ----------
def get_all_users():
    return AdminUser.query.order_by(AdminUser.id.asc()).all()

def get_user(user_id: int):
    return AdminUser.query.get(user_id)

def get_all_permisos():
    return Permiso.query.order_by(Permiso.code.asc()).all()

def get_permisos_de_role(role: str):
    """Devuelve set de códigos de permiso para el rol dado."""
    rows = RolePermiso.query.filter_by(role=role).all()
    return {r.permiso_code for r in rows}

def set_permisos_de_role(role: str, nuevos_codes: list[str]):
    """Sincroniza los permisos (por code) de un rol string en role_permisos."""
    actuales = RolePermiso.query.filter_by(role=role).all()
    actuales_codes = {r.permiso_code for r in actuales}

    nuevos = set(nuevos_codes)
    a_agregar = nuevos - actuales_codes
    a_borrar  = actuales_codes - nuevos

    # Agregar
    if a_agregar:
        permisos = Permiso.query.filter(Permiso.code.in_(list(a_agregar))).all()
        for p in permisos:
            db.session.add(RolePermiso(role=role, permiso_code=p.code))

    # Borrar
    if a_borrar:
        RolePermiso.query.filter(
            RolePermiso.role == role,
            RolePermiso.permiso_code.in_(list(a_borrar))
        ).delete(synchronize_session=False)

    db.session.commit()
    return True

# --------- Vistas Usuarios ----------
@users_admin.route("/")
def listar_usuarios():
    users = get_all_users()
    return render_template("/usuarios_list.html", users=users, roles=None)

@users_admin.route("/nuevo", methods=["GET", "POST"])
def crear_usuario():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        role     = (request.form.get("role") or "user").strip()
        activo   = request.form.get("is_active") == "1"
        fullname = request.form.get("fullname", "").strip()


        password  = request.form.get("password") or ""
        password2 = request.form.get("password2") or ""

        if not username:
            flash("El nombre de usuario es obligatorio.", "danger")
            return redirect(url_for(".crear_usuario"))
        
        if not fullname:
            flash("El nombre completo es obligatorio.", "danger")
            return redirect(url_for(".crear_usuario"))

        if role not in ROLES_DISPONIBLES:
            flash("Rol inválido.", "danger")
            return redirect(url_for(".crear_usuario"))

        if AdminUser.query.filter_by(username=username).first():
            flash("El nombre de usuario ya existe.", "danger")
            return redirect(url_for(".crear_usuario"))

        # Validación de contraseña (requerida al crear)
        if len(password) < 8:
            flash("La contraseña debe tener al menos 8 caracteres.", "danger")
            return redirect(url_for(".crear_usuario"))
        if password != password2:
            flash("Las contraseñas no coinciden.", "danger")
            return redirect(url_for(".crear_usuario"))

        u = AdminUser(
            username=username,
            is_active=activo,
            role=role,
            fullname=fullname,
            password_hash=generate_password_hash(password),
        )
        db.session.add(u)
        db.session.commit()

        flash("Usuario creado correctamente.", "success")
        return redirect(url_for(".listar_usuarios"))

    return render_template("/usuarios_form.html", modo="crear", roles=ROLES_DISPONIBLES, user=None)

@users_admin.route("/<int:user_id>/editar", methods=["GET", "POST"])
def editar_usuario(user_id):
    user = get_user(user_id)
    if not user:
        abort(404)

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        role     = (request.form.get("role") or "user").strip()
        activo   = request.form.get("is_active") == "1"
        fullname = request.form.get("fullname", "").strip()


        # Contraseña opcional al editar
        new_password  = request.form.get("password") or ""
        new_password2 = request.form.get("password2") or ""

        if not username:
            flash("El nombre de usuario es obligatorio.", "danger")
            return redirect(url_for(".editar_usuario", user_id=user_id))
        
        if not fullname:
            flash("El nombre completo es obligatorio.", "danger")
            return redirect(url_for(".editar_usuario", user_id=user_id))

        if role not in ROLES_DISPONIBLES:
            flash("Rol inválido.", "danger")
            return redirect(url_for(".editar_usuario", user_id=user_id))

        # Unicidad de username (excluyendo el actual)
        if AdminUser.query.filter(AdminUser.username == username, AdminUser.id != user.id).first():
            flash("El nombre de usuario ya existe.", "danger")
            return redirect(url_for(".editar_usuario", user_id=user_id))

        user.username = username
        user.is_active = activo
        user.role = role
        user.fullname = fullname  # ← importante


        # Si se quiere cambiar la contraseña
        if new_password or new_password2:
            if len(new_password) < 8:
                flash("La contraseña debe tener al menos 8 caracteres.", "danger")
                return redirect(url_for(".editar_usuario", user_id=user_id))
            if new_password != new_password2:
                flash("Las contraseñas no coinciden.", "danger")
                return redirect(url_for(".editar_usuario", user_id=user_id))
            user.password_hash = generate_password_hash(new_password)

        db.session.commit()
        flash("Usuario actualizado.", "success")
        return redirect(url_for(".listar_usuarios"))

    return render_template("/usuarios_form.html", modo="editar", roles=ROLES_DISPONIBLES, user=user)

@users_admin.route("/<int:user_id>/eliminar", methods=["POST"])
def eliminar_usuario(user_id):
    user = get_user(user_id)
    if not user:
        abort(404)
    db.session.delete(user)
    db.session.commit()
    flash("Usuario eliminado.", "success")
    return redirect(url_for(".listar_usuarios"))

# --------- Vistas Roles & Permisos ----------
@users_admin.route("/roles-permisos", methods=["GET", "POST"])
def roles_permisos():
    permisos = get_all_permisos()

    if request.method == "POST":
        role = (request.form.get("role_id") or "user").strip()
        if role not in ROLES_DISPONIBLES:
            flash("Rol inválido.", "danger")
            return redirect(url_for(".roles_permisos"))

        perm_codes = request.form.getlist("permisos")  # lista de códigos (strings)
        set_permisos_de_role(role, perm_codes)
        flash("Permisos actualizados.", "success")
        return redirect(url_for(".roles_permisos", role_id=role))

    selected_role = (request.args.get("role_id") or ROLES_DISPONIBLES[0]).strip()
    if selected_role not in ROLES_DISPONIBLES:
        selected_role = ROLES_DISPONIBLES[0]

    role_perm_codes = get_permisos_de_role(selected_role)

    return render_template(
        "/roles_permisos.html",
        roles=ROLES_DISPONIBLES,
        permisos=permisos,
        selected_role=selected_role,
        role_perm_codes=role_perm_codes
    )
