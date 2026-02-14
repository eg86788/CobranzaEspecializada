# app/services/field_config.py
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

log = logging.getLogger(__name__)

# Debe existir fetchall / fetchone
try:
    from ..db_legacy import fetchall, fetchone
except Exception:
    from app.db_legacy import fetchall, fetchone

_CONFIG: Dict[str, Dict[str, Any]] = {}
_LAST_TS: Optional[datetime] = None

def _read_last_ts() -> Optional[datetime]:
    row = fetchone("SELECT MAX(updated_at) AS ts FROM config_campos") or {}
    return row.get("ts")

def _load_all() -> Dict[str, Dict[str, Any]]:
    rows = fetchall("SELECT * FROM config_campos ORDER BY frame, orden, field_name") or []
    cfg: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        f = r["frame"]; name = r["field_name"]
        cfg.setdefault(f, {})[name] = {
            "visible_default": bool(r.get("visible_default", True)),
            "required_default": bool(r.get("required_default", False)),
            "disabled_default": bool(r.get("disabled_default", False)),
            "conditions": r.get("conditions") or [],
            "grupo": r.get("grupo"),
            "orden": r.get("orden", 0),
        }
    return cfg

def ensure_loaded(force: bool = False) -> None:
    global _CONFIG, _LAST_TS
    try:
        if force or not _CONFIG:
            _CONFIG = _load_all()
            _LAST_TS = _read_last_ts()
            log.info("config_campos cargado: %d frames", len(_CONFIG))
            return
        current_ts = _read_last_ts()
        if current_ts and (_LAST_TS is None or current_ts > _LAST_TS):
            _CONFIG = _load_all()
            _LAST_TS = current_ts
            log.info("config_campos refrescado por updated_at")
    except Exception as e:
        log.error("No se pudo cargar config_campos: %s", e)

def get_rules_for_frame(frame: str, contexto: Dict[str, Any]) -> Dict[str, Any]:
    """
    Devuelve un dict por campo:
    { field_name: {visible, required, disabled} }
    y un nodo especial __overrides__ con merges por sección (si existen).
    """
    ensure_loaded()
    frame_cfg = _CONFIG.get(frame, {})
    result: Dict[str, Any] = {}
    overrides_section: Dict[str, Any] = {}

    def matches(when: Dict[str, Any]) -> bool:
        # igualdad exacta (normaliza a str sin tildes si quieres)
        return all(str(contexto.get(k, "")) == str(v) for k, v in (when or {}).items())

    for fname, meta in frame_cfg.items():
        vis = meta["visible_default"]
        req = meta["required_default"]
        dis = meta["disabled_default"]
        conds: List[Dict[str, Any]] = meta.get("conditions") or []

        # Campo "falso" para transportar overrides de sección
        if fname.startswith("_overrides_"):
            for c in conds:
                if matches(c.get("when", {})):
                    # merge de overrides por sección
                    ov = c.get("overrides", {})
                    for k, v in ov.items():
                        overrides_section[k] = v
            continue

        for c in conds:
            if matches(c.get("when", {})):
                sets = c.get("set", {})
                if "visible" in sets:   vis = bool(sets["visible"])
                if "required" in sets:  req = bool(sets["required"])
                if "disabled" in sets:  dis = bool(sets["disabled"])

        result[fname] = {"visible": vis, "required": req, "disabled": dis}

    if overrides_section:
        result["__overrides__"] = overrides_section
    return result
