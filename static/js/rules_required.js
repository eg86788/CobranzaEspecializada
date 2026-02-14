// static/js/rules_required.js
(function(){
    const $ = (s)=>document.querySelector(s);
    const norm = (s)=> (s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toUpperCase().trim();
  
    function setReqByName(name, on){
      const nodes = document.querySelectorAll(`[name="${name}"]`);
      nodes.forEach(el => {
        if (on) el.setAttribute('required','required');
        else el.removeAttribute('required');
      });
    }
    function setReq(el, on){ if(!el) return; on ? el.setAttribute('required','required') : el.removeAttribute('required'); }
  
    function getStateFallback(){
      // Estado mínimo desde el DOM, por si no nos pasan overrides
      const tipo_tramite  = norm($('#tipo_tramite')?.value);
      const tipo_contrato = norm($('#tipo_contrato')?.value);
      const tipo_servicio = norm($('#tipo_servicio')?.value);
      const tipo_cobro    = norm($('#tipo_cobro')?.value);
  
      // Sustitución múltiple (DOM checkboxes si existen)
      const pick = (ids, labels)=> ids.map((id,i)=>[$(id),labels[i]]).filter(([el])=>el&&el.checked).map(([,lbl])=>lbl);
      const mod  = pick(['#smod_unidades','#smod_cuentas','#smod_usuarios','#smod_contactos'], ['UNIDADES','CUENTAS','USUARIOS','CONTACTOS']);
      const crea = pick(['#screa_unidades','#screa_cuentas','#screa_usuarios','#screa_contactos'], ['UNIDADES','CUENTAS','USUARIOS','CONTACTOS']);
      const extras = pick(['#smod_tipocobro','#smod_impdif'], ['TIPOCOBRO','IMPDIF']);
  
      let sust_accion = '';
      if ((mod.length+extras.length)>0 && crea.length===0) sust_accion='MODIFICAR';
      if (crea.length>0 && (mod.length+extras.length)===0) sust_accion='CREAR';
  
      return { tipo_tramite, tipo_contrato, tipo_servicio, tipo_cobro, sust_mod:mod, sust_crea:crea, sust_mod_extras:extras, sust_accion };
    }
  
    function applyRequiredRules(state){
      const s = { ...getStateFallback(), ...(state||{}) };
      const esAlta = s.tipo_tramite === 'ALTA';
      const esSust = s.tipo_tramite === 'SUSTITUCION' || s.tipo_tramite === 'SUSTITUCIÓN';
  
      // Base siempre razonable
      setReqByName('nombre_ejecutivo', true);
      setReqByName('segmento', true);
      setReqByName('razon_social', true);
      setReqByName('tipo_persona', true);
      setReqByName('numero_cliente', true);
  
      // Contrato: requerido solo en SUSTITUCIÓN
      setReq($('#numero_contrato'), esSust);
  
      // Datos de contacto: solo en ALTA
      setReqByName('correo_apoderado_legal', esAlta);
      setReqByName('telefono_cliente',       esAlta);
      setReqByName('domicilio_cliente',      esAlta);
  
      // Servicio/Contrato:
      // En ALTA sí o sí; en SUST, libres a menos que el usuario quiera modificar config
      const tocaConfig = esSust && s.sust_accion === 'MODIFICAR' && Array.isArray(s.sust_mod_extras);
      setReqByName('tipo_contrato', esAlta || tocaConfig);
      setReqByName('tipo_servicio', esAlta);  // servicio solo es clave en alta
      // Tipo de cobro requerido si se va a modificar explícitamente
      setReqByName('tipo_cobro', esAlta || (tocaConfig && s.sust_mod_extras.includes('TIPOCOBRO')));
  
      // Importe: requerido si el servicio lo muestra en ALTA o si el usuario lo elige como extra en SUST
      const impInput = $('#importe_maximo_dif');
      const impPorServicioAlta = esAlta && ['DEPOSITO TRADICIONAL','DEPOSITO ELECTRONICO','DEPOSITO ELECTRONICO Y DOTACION ELECTRONICA'].includes(
        norm($('#tipo_servicio')?.value)
      );
      const impPorExtraSust = esSust && s.sust_accion==='MODIFICAR' && s.sust_mod_extras.includes('IMPDIF');
      setReq(impInput, !!(impPorServicioAlta || impPorExtraSust));
    }
  
    function initRequiredRulesEngine(){
      // no-op; aquí podrías preparar listeners si quisieras
    }
    function getCurrentFormState(){
      return getStateFallback();
    }
  
    window.RequiredRules = { initRequiredRulesEngine, applyRequiredRules, getCurrentFormState };
  })();
  