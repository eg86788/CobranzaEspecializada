--
-- PostgreSQL database dump
--

-- Dumped from database version 14.18 (Homebrew)
-- Dumped by pg_dump version 14.18 (Homebrew)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: admin_users; Type: TABLE; Schema: public; Owner: edgargarcia
--

CREATE TABLE public.admin_users (
    id integer NOT NULL,
    username character varying(120) NOT NULL,
    fullname character varying(120) NOT NULL,
    password_hash character varying(255) NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp without time zone NOT NULL,
    role character varying(20) NOT NULL
);


ALTER TABLE public.admin_users OWNER TO edgargarcia;

--
-- Name: admin_users_id_seq; Type: SEQUENCE; Schema: public; Owner: edgargarcia
--

CREATE SEQUENCE public.admin_users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.admin_users_id_seq OWNER TO edgargarcia;

--
-- Name: admin_users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: edgargarcia
--

ALTER SEQUENCE public.admin_users_id_seq OWNED BY public.admin_users.id;


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: edgargarcia
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO edgargarcia;

--
-- Name: catalogo_adhesiones; Type: TABLE; Schema: public; Owner: edgargarcia
--

CREATE TABLE public.catalogo_adhesiones (
    id integer NOT NULL,
    clave character varying(100) NOT NULL,
    numero character varying(100) NOT NULL,
    vigente_desde date NOT NULL,
    vigente_hasta date,
    activo boolean DEFAULT true NOT NULL,
    updated_by character varying(120),
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.catalogo_adhesiones OWNER TO edgargarcia;

--
-- Name: catalogo_adhesiones_id_seq; Type: SEQUENCE; Schema: public; Owner: edgargarcia
--

CREATE SEQUENCE public.catalogo_adhesiones_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.catalogo_adhesiones_id_seq OWNER TO edgargarcia;

--
-- Name: catalogo_adhesiones_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: edgargarcia
--

ALTER SEQUENCE public.catalogo_adhesiones_id_seq OWNED BY public.catalogo_adhesiones.id;


--
-- Name: catalogo_cpae; Type: TABLE; Schema: public; Owner: edgargarcia
--

CREATE TABLE public.catalogo_cpae (
    id integer NOT NULL,
    clave character varying(10) NOT NULL,
    descripcion character varying(150) NOT NULL,
    activo boolean,
    abreviatura character varying(10) NOT NULL
);


ALTER TABLE public.catalogo_cpae OWNER TO edgargarcia;

--
-- Name: catalogo_cpae_id_seq; Type: SEQUENCE; Schema: public; Owner: edgargarcia
--

CREATE SEQUENCE public.catalogo_cpae_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.catalogo_cpae_id_seq OWNER TO edgargarcia;

--
-- Name: catalogo_cpae_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: edgargarcia
--

ALTER SEQUENCE public.catalogo_cpae_id_seq OWNED BY public.catalogo_cpae.id;


--
-- Name: catalogo_entidad; Type: TABLE; Schema: public; Owner: edgargarcia
--

CREATE TABLE public.catalogo_entidad (
    id integer NOT NULL,
    clave_inegi character varying(5) NOT NULL,
    nombre character varying(150) NOT NULL,
    activo boolean
);


ALTER TABLE public.catalogo_entidad OWNER TO edgargarcia;

--
-- Name: catalogo_entidad_id_seq; Type: SEQUENCE; Schema: public; Owner: edgargarcia
--

CREATE SEQUENCE public.catalogo_entidad_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.catalogo_entidad_id_seq OWNER TO edgargarcia;

--
-- Name: catalogo_entidad_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: edgargarcia
--

ALTER SEQUENCE public.catalogo_entidad_id_seq OWNED BY public.catalogo_entidad.id;


--
-- Name: catalogo_etv; Type: TABLE; Schema: public; Owner: edgargarcia
--

CREATE TABLE public.catalogo_etv (
    id integer NOT NULL,
    nombre character varying(150) NOT NULL,
    activo boolean
);


ALTER TABLE public.catalogo_etv OWNER TO edgargarcia;

--
-- Name: catalogo_etv_id_seq; Type: SEQUENCE; Schema: public; Owner: edgargarcia
--

CREATE SEQUENCE public.catalogo_etv_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.catalogo_etv_id_seq OWNER TO edgargarcia;

--
-- Name: catalogo_etv_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: edgargarcia
--

ALTER SEQUENCE public.catalogo_etv_id_seq OWNED BY public.catalogo_etv.id;


--
-- Name: catalogo_municipio; Type: TABLE; Schema: public; Owner: edgargarcia
--

CREATE TABLE public.catalogo_municipio (
    id integer NOT NULL,
    clave_inegi character varying(10),
    nombre character varying(150) NOT NULL,
    entidad_id integer NOT NULL,
    activo boolean
);


ALTER TABLE public.catalogo_municipio OWNER TO edgargarcia;

--
-- Name: catalogo_municipio_id_seq; Type: SEQUENCE; Schema: public; Owner: edgargarcia
--

CREATE SEQUENCE public.catalogo_municipio_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.catalogo_municipio_id_seq OWNER TO edgargarcia;

--
-- Name: catalogo_municipio_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: edgargarcia
--

ALTER SEQUENCE public.catalogo_municipio_id_seq OWNED BY public.catalogo_municipio.id;


--
-- Name: catalogo_procesadora; Type: TABLE; Schema: public; Owner: edgargarcia
--

CREATE TABLE public.catalogo_procesadora (
    id integer NOT NULL,
    clave character varying(10),
    nombre character varying(150) NOT NULL,
    etv_id integer,
    activo boolean,
    cpae_id integer
);


ALTER TABLE public.catalogo_procesadora OWNER TO edgargarcia;

--
-- Name: catalogo_procesadora_id_seq; Type: SEQUENCE; Schema: public; Owner: edgargarcia
--

CREATE SEQUENCE public.catalogo_procesadora_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.catalogo_procesadora_id_seq OWNER TO edgargarcia;

--
-- Name: catalogo_procesadora_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: edgargarcia
--

ALTER SEQUENCE public.catalogo_procesadora_id_seq OWNED BY public.catalogo_procesadora.id;


--
-- Name: catalogo_productos; Type: TABLE; Schema: public; Owner: edgargarcia
--

CREATE TABLE public.catalogo_productos (
    id integer NOT NULL,
    code character varying(50) NOT NULL,
    nombre character varying(120) NOT NULL,
    descripcion text,
    activo boolean NOT NULL,
    fecha_creacion timestamp without time zone NOT NULL
);


ALTER TABLE public.catalogo_productos OWNER TO edgargarcia;

--
-- Name: catalogo_productos_id_seq; Type: SEQUENCE; Schema: public; Owner: edgargarcia
--

CREATE SEQUENCE public.catalogo_productos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.catalogo_productos_id_seq OWNER TO edgargarcia;

--
-- Name: catalogo_productos_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: edgargarcia
--

ALTER SEQUENCE public.catalogo_productos_id_seq OWNED BY public.catalogo_productos.id;


--
-- Name: document_templates; Type: TABLE; Schema: public; Owner: edgargarcia
--

CREATE TABLE public.document_templates (
    id integer NOT NULL,
    slug text NOT NULL,
    name text NOT NULL,
    content_html text NOT NULL,
    css text DEFAULT ''::text,
    version integer DEFAULT 1 NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    updated_by text,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    cascaron integer
);


ALTER TABLE public.document_templates OWNER TO edgargarcia;

--
-- Name: document_templates_id_seq; Type: SEQUENCE; Schema: public; Owner: edgargarcia
--

CREATE SEQUENCE public.document_templates_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.document_templates_id_seq OWNER TO edgargarcia;

--
-- Name: document_templates_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: edgargarcia
--

ALTER SEQUENCE public.document_templates_id_seq OWNED BY public.document_templates.id;


--
-- Name: meeting_attendees; Type: TABLE; Schema: public; Owner: edgargarcia
--

CREATE TABLE public.meeting_attendees (
    id integer NOT NULL,
    meeting_id integer NOT NULL,
    nombre text NOT NULL,
    cargo text
);


ALTER TABLE public.meeting_attendees OWNER TO edgargarcia;

--
-- Name: meeting_attendees_id_seq; Type: SEQUENCE; Schema: public; Owner: edgargarcia
--

CREATE SEQUENCE public.meeting_attendees_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.meeting_attendees_id_seq OWNER TO edgargarcia;

--
-- Name: meeting_attendees_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: edgargarcia
--

ALTER SEQUENCE public.meeting_attendees_id_seq OWNED BY public.meeting_attendees.id;


--
-- Name: meeting_commitments; Type: TABLE; Schema: public; Owner: edgargarcia
--

CREATE TABLE public.meeting_commitments (
    id integer NOT NULL,
    meeting_id integer NOT NULL,
    descripcion text NOT NULL,
    responsable text NOT NULL,
    eta date,
    estatus text DEFAULT 'PENDIENTE'::text NOT NULL
);


ALTER TABLE public.meeting_commitments OWNER TO edgargarcia;

--
-- Name: meeting_commitments_id_seq; Type: SEQUENCE; Schema: public; Owner: edgargarcia
--

CREATE SEQUENCE public.meeting_commitments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.meeting_commitments_id_seq OWNER TO edgargarcia;

--
-- Name: meeting_commitments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: edgargarcia
--

ALTER SEQUENCE public.meeting_commitments_id_seq OWNED BY public.meeting_commitments.id;


--
-- Name: meeting_minutes; Type: TABLE; Schema: public; Owner: edgargarcia
--

CREATE TABLE public.meeting_minutes (
    id integer NOT NULL,
    fecha_reunion date NOT NULL,
    asunto text NOT NULL,
    notas text,
    acuerdos text,
    created_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.meeting_minutes OWNER TO edgargarcia;

--
-- Name: meeting_minutes_id_seq; Type: SEQUENCE; Schema: public; Owner: edgargarcia
--

CREATE SEQUENCE public.meeting_minutes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.meeting_minutes_id_seq OWNER TO edgargarcia;

--
-- Name: meeting_minutes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: edgargarcia
--

ALTER SEQUENCE public.meeting_minutes_id_seq OWNED BY public.meeting_minutes.id;


--
-- Name: permisos; Type: TABLE; Schema: public; Owner: edgargarcia
--

CREATE TABLE public.permisos (
    id integer NOT NULL,
    code character varying(50) NOT NULL,
    descripcion text
);


ALTER TABLE public.permisos OWNER TO edgargarcia;

--
-- Name: permisos_id_seq; Type: SEQUENCE; Schema: public; Owner: edgargarcia
--

CREATE SEQUENCE public.permisos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.permisos_id_seq OWNER TO edgargarcia;

--
-- Name: permisos_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: edgargarcia
--

ALTER SEQUENCE public.permisos_id_seq OWNED BY public.permisos.id;


--
-- Name: role_permisos; Type: TABLE; Schema: public; Owner: edgargarcia
--

CREATE TABLE public.role_permisos (
    id integer NOT NULL,
    role character varying(20) NOT NULL,
    permiso_code character varying(50) NOT NULL
);


ALTER TABLE public.role_permisos OWNER TO edgargarcia;

--
-- Name: role_permisos_id_seq; Type: SEQUENCE; Schema: public; Owner: edgargarcia
--

CREATE SEQUENCE public.role_permisos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.role_permisos_id_seq OWNER TO edgargarcia;

--
-- Name: role_permisos_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: edgargarcia
--

ALTER SEQUENCE public.role_permisos_id_seq OWNED BY public.role_permisos.id;


--
-- Name: role_product_access; Type: TABLE; Schema: public; Owner: edgargarcia
--

CREATE TABLE public.role_product_access (
    id integer NOT NULL,
    role character varying(20) NOT NULL,
    producto_code character varying(50) NOT NULL,
    habilitado boolean NOT NULL
);


ALTER TABLE public.role_product_access OWNER TO edgargarcia;

--
-- Name: role_product_access_id_seq; Type: SEQUENCE; Schema: public; Owner: edgargarcia
--

CREATE SEQUENCE public.role_product_access_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.role_product_access_id_seq OWNER TO edgargarcia;

--
-- Name: role_product_access_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: edgargarcia
--

ALTER SEQUENCE public.role_product_access_id_seq OWNED BY public.role_product_access.id;


--
-- Name: roles; Type: TABLE; Schema: public; Owner: edgargarcia
--

CREATE TABLE public.roles (
    id integer NOT NULL,
    code character varying(50) NOT NULL,
    descripcion character varying(150),
    activo boolean DEFAULT true
);


ALTER TABLE public.roles OWNER TO edgargarcia;

--
-- Name: roles_id_seq; Type: SEQUENCE; Schema: public; Owner: edgargarcia
--

CREATE SEQUENCE public.roles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.roles_id_seq OWNER TO edgargarcia;

--
-- Name: roles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: edgargarcia
--

ALTER SEQUENCE public.roles_id_seq OWNED BY public.roles.id;


--
-- Name: solicitudes; Type: TABLE; Schema: public; Owner: edgargarcia
--

CREATE TABLE public.solicitudes (
    id integer NOT NULL,
    producto character varying(50) NOT NULL,
    estado_actual character varying(50) NOT NULL,
    estatus character varying(20) NOT NULL,
    usuario_creador character varying(50) NOT NULL,
    data_json jsonb NOT NULL,
    fecha_creacion timestamp without time zone NOT NULL,
    fecha_actualizacion timestamp without time zone NOT NULL,
    numero_cliente character varying(50),
    numero_contrato character varying(20),
    razon_social character varying(255),
    observaciones text,
    rfc character varying(20),
    tipo_tramite character varying(50)
);


ALTER TABLE public.solicitudes OWNER TO edgargarcia;

--
-- Name: solicitudes_id_seq; Type: SEQUENCE; Schema: public; Owner: edgargarcia
--

CREATE SEQUENCE public.solicitudes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.solicitudes_id_seq OWNER TO edgargarcia;

--
-- Name: solicitudes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: edgargarcia
--

ALTER SEQUENCE public.solicitudes_id_seq OWNED BY public.solicitudes.id;


--
-- Name: solicitudes_sef; Type: TABLE; Schema: public; Owner: edgargarcia
--

CREATE TABLE public.solicitudes_sef (
    id integer NOT NULL,
    solicitud_id integer NOT NULL,
    tipo_contrato character varying(100),
    tipo_servicio character varying(150),
    servicio_adicional character varying(150),
    tipo_cobro character varying(50),
    importe_maximo_dif numeric(15,2),
    segmento character varying(50),
    tipo_persona character varying(150),
    apoderado_legal character varying(150),
    correo_apoderado_legal character varying(150),
    telefono_cliente character varying(20),
    domicilio_cliente character varying(250),
    sust_mod_unidades boolean,
    sust_mod_cuentas boolean,
    sust_mod_usuarios boolean,
    sust_mod_contactos boolean,
    sust_mod_tipocobro boolean,
    sust_mod_impdif boolean,
    sust_crea_unidades boolean,
    sust_crea_cuentas boolean,
    sust_crea_usuarios boolean,
    sust_crea_contactos boolean,
    cortes_envio character varying(250)
);


ALTER TABLE public.solicitudes_sef OWNER TO edgargarcia;

--
-- Name: solicitudes_sef_id_seq; Type: SEQUENCE; Schema: public; Owner: edgargarcia
--

CREATE SEQUENCE public.solicitudes_sef_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.solicitudes_sef_id_seq OWNER TO edgargarcia;

--
-- Name: solicitudes_sef_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: edgargarcia
--

ALTER SEQUENCE public.solicitudes_sef_id_seq OWNED BY public.solicitudes_sef.id;


--
-- Name: solicitudes_sef_unidades; Type: TABLE; Schema: public; Owner: edgargarcia
--

CREATE TABLE public.solicitudes_sef_unidades (
    id integer NOT NULL,
    accion_unidad character varying(20),
    nombre_unidad character varying(150),
    servicio_verificacion_tradicional boolean NOT NULL,
    servicio_verificacion_electronica boolean NOT NULL,
    servicio_cliente_certificado_central boolean NOT NULL,
    servicio_dotacion_centralizada boolean NOT NULL,
    servicio_integradora boolean NOT NULL,
    servicio_dotacion boolean NOT NULL,
    servicio_traslado boolean NOT NULL,
    servicio_cofre boolean NOT NULL,
    cofre_modelo character varying(50),
    relacion_dot_centralizada character varying(50),
    relacion_cc_centralizada character varying(50),
    calle_numero character varying(255),
    codigo_postal character varying(10),
    sef_id integer NOT NULL,
    cpae_id integer,
    etv_id integer,
    procesadora_id integer,
    entidad_id integer,
    municipio_id integer
);


ALTER TABLE public.solicitudes_sef_unidades OWNER TO edgargarcia;

--
-- Name: solicitudes_sef_unidades_id_seq; Type: SEQUENCE; Schema: public; Owner: edgargarcia
--

CREATE SEQUENCE public.solicitudes_sef_unidades_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.solicitudes_sef_unidades_id_seq OWNER TO edgargarcia;

--
-- Name: solicitudes_sef_unidades_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: edgargarcia
--

ALTER SEQUENCE public.solicitudes_sef_unidades_id_seq OWNED BY public.solicitudes_sef_unidades.id;


--
-- Name: system_params; Type: TABLE; Schema: public; Owner: edgargarcia
--

CREATE TABLE public.system_params (
    key character varying(100) NOT NULL,
    value character varying(255) NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_by character varying(100),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.system_params OWNER TO edgargarcia;

--
-- Name: admin_users id; Type: DEFAULT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.admin_users ALTER COLUMN id SET DEFAULT nextval('public.admin_users_id_seq'::regclass);


--
-- Name: catalogo_adhesiones id; Type: DEFAULT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.catalogo_adhesiones ALTER COLUMN id SET DEFAULT nextval('public.catalogo_adhesiones_id_seq'::regclass);


--
-- Name: catalogo_cpae id; Type: DEFAULT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.catalogo_cpae ALTER COLUMN id SET DEFAULT nextval('public.catalogo_cpae_id_seq'::regclass);


--
-- Name: catalogo_entidad id; Type: DEFAULT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.catalogo_entidad ALTER COLUMN id SET DEFAULT nextval('public.catalogo_entidad_id_seq'::regclass);


--
-- Name: catalogo_etv id; Type: DEFAULT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.catalogo_etv ALTER COLUMN id SET DEFAULT nextval('public.catalogo_etv_id_seq'::regclass);


--
-- Name: catalogo_municipio id; Type: DEFAULT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.catalogo_municipio ALTER COLUMN id SET DEFAULT nextval('public.catalogo_municipio_id_seq'::regclass);


--
-- Name: catalogo_procesadora id; Type: DEFAULT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.catalogo_procesadora ALTER COLUMN id SET DEFAULT nextval('public.catalogo_procesadora_id_seq'::regclass);


--
-- Name: catalogo_productos id; Type: DEFAULT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.catalogo_productos ALTER COLUMN id SET DEFAULT nextval('public.catalogo_productos_id_seq'::regclass);


--
-- Name: document_templates id; Type: DEFAULT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.document_templates ALTER COLUMN id SET DEFAULT nextval('public.document_templates_id_seq'::regclass);


--
-- Name: meeting_attendees id; Type: DEFAULT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.meeting_attendees ALTER COLUMN id SET DEFAULT nextval('public.meeting_attendees_id_seq'::regclass);


--
-- Name: meeting_commitments id; Type: DEFAULT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.meeting_commitments ALTER COLUMN id SET DEFAULT nextval('public.meeting_commitments_id_seq'::regclass);


--
-- Name: meeting_minutes id; Type: DEFAULT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.meeting_minutes ALTER COLUMN id SET DEFAULT nextval('public.meeting_minutes_id_seq'::regclass);


--
-- Name: permisos id; Type: DEFAULT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.permisos ALTER COLUMN id SET DEFAULT nextval('public.permisos_id_seq'::regclass);


--
-- Name: role_permisos id; Type: DEFAULT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.role_permisos ALTER COLUMN id SET DEFAULT nextval('public.role_permisos_id_seq'::regclass);


--
-- Name: role_product_access id; Type: DEFAULT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.role_product_access ALTER COLUMN id SET DEFAULT nextval('public.role_product_access_id_seq'::regclass);


--
-- Name: roles id; Type: DEFAULT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.roles ALTER COLUMN id SET DEFAULT nextval('public.roles_id_seq'::regclass);


--
-- Name: solicitudes id; Type: DEFAULT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.solicitudes ALTER COLUMN id SET DEFAULT nextval('public.solicitudes_id_seq'::regclass);


--
-- Name: solicitudes_sef id; Type: DEFAULT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.solicitudes_sef ALTER COLUMN id SET DEFAULT nextval('public.solicitudes_sef_id_seq'::regclass);


--
-- Name: solicitudes_sef_unidades id; Type: DEFAULT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.solicitudes_sef_unidades ALTER COLUMN id SET DEFAULT nextval('public.solicitudes_sef_unidades_id_seq'::regclass);


--
-- Name: admin_users admin_users_pkey; Type: CONSTRAINT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.admin_users
    ADD CONSTRAINT admin_users_pkey PRIMARY KEY (id);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: catalogo_adhesiones catalogo_adhesiones_pkey; Type: CONSTRAINT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.catalogo_adhesiones
    ADD CONSTRAINT catalogo_adhesiones_pkey PRIMARY KEY (id);


--
-- Name: catalogo_cpae catalogo_cpae_pkey; Type: CONSTRAINT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.catalogo_cpae
    ADD CONSTRAINT catalogo_cpae_pkey PRIMARY KEY (id);


--
-- Name: catalogo_entidad catalogo_entidad_pkey; Type: CONSTRAINT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.catalogo_entidad
    ADD CONSTRAINT catalogo_entidad_pkey PRIMARY KEY (id);


--
-- Name: catalogo_etv catalogo_etv_pkey; Type: CONSTRAINT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.catalogo_etv
    ADD CONSTRAINT catalogo_etv_pkey PRIMARY KEY (id);


--
-- Name: catalogo_municipio catalogo_municipio_pkey; Type: CONSTRAINT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.catalogo_municipio
    ADD CONSTRAINT catalogo_municipio_pkey PRIMARY KEY (id);


--
-- Name: catalogo_procesadora catalogo_procesadora_pkey; Type: CONSTRAINT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.catalogo_procesadora
    ADD CONSTRAINT catalogo_procesadora_pkey PRIMARY KEY (id);


--
-- Name: catalogo_productos catalogo_productos_pkey; Type: CONSTRAINT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.catalogo_productos
    ADD CONSTRAINT catalogo_productos_pkey PRIMARY KEY (id);


--
-- Name: document_templates document_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.document_templates
    ADD CONSTRAINT document_templates_pkey PRIMARY KEY (id);


--
-- Name: document_templates document_templates_slug_version_key; Type: CONSTRAINT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.document_templates
    ADD CONSTRAINT document_templates_slug_version_key UNIQUE (slug, version);


--
-- Name: meeting_attendees meeting_attendees_pkey; Type: CONSTRAINT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.meeting_attendees
    ADD CONSTRAINT meeting_attendees_pkey PRIMARY KEY (id);


--
-- Name: meeting_commitments meeting_commitments_pkey; Type: CONSTRAINT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.meeting_commitments
    ADD CONSTRAINT meeting_commitments_pkey PRIMARY KEY (id);


--
-- Name: meeting_minutes meeting_minutes_pkey; Type: CONSTRAINT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.meeting_minutes
    ADD CONSTRAINT meeting_minutes_pkey PRIMARY KEY (id);


--
-- Name: permisos permisos_pkey; Type: CONSTRAINT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.permisos
    ADD CONSTRAINT permisos_pkey PRIMARY KEY (id);


--
-- Name: role_permisos role_permisos_pkey; Type: CONSTRAINT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.role_permisos
    ADD CONSTRAINT role_permisos_pkey PRIMARY KEY (id);


--
-- Name: role_product_access role_product_access_pkey; Type: CONSTRAINT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.role_product_access
    ADD CONSTRAINT role_product_access_pkey PRIMARY KEY (id);


--
-- Name: roles roles_code_key; Type: CONSTRAINT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_code_key UNIQUE (code);


--
-- Name: roles roles_pkey; Type: CONSTRAINT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_pkey PRIMARY KEY (id);


--
-- Name: solicitudes solicitudes_pkey; Type: CONSTRAINT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.solicitudes
    ADD CONSTRAINT solicitudes_pkey PRIMARY KEY (id);


--
-- Name: solicitudes_sef solicitudes_sef_pkey; Type: CONSTRAINT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.solicitudes_sef
    ADD CONSTRAINT solicitudes_sef_pkey PRIMARY KEY (id);


--
-- Name: solicitudes_sef solicitudes_sef_solicitud_id_key; Type: CONSTRAINT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.solicitudes_sef
    ADD CONSTRAINT solicitudes_sef_solicitud_id_key UNIQUE (solicitud_id);


--
-- Name: solicitudes_sef_unidades solicitudes_sef_unidades_pkey; Type: CONSTRAINT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.solicitudes_sef_unidades
    ADD CONSTRAINT solicitudes_sef_unidades_pkey PRIMARY KEY (id);


--
-- Name: system_params system_params_pkey; Type: CONSTRAINT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.system_params
    ADD CONSTRAINT system_params_pkey PRIMARY KEY (key);


--
-- Name: role_permisos uq_role_permiso; Type: CONSTRAINT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.role_permisos
    ADD CONSTRAINT uq_role_permiso UNIQUE (role, permiso_code);


--
-- Name: idx_adhesiones_clave; Type: INDEX; Schema: public; Owner: edgargarcia
--

CREATE INDEX idx_adhesiones_clave ON public.catalogo_adhesiones USING btree (clave);


--
-- Name: idx_cpae_descripcion; Type: INDEX; Schema: public; Owner: edgargarcia
--

CREATE INDEX idx_cpae_descripcion ON public.catalogo_cpae USING btree (descripcion);


--
-- Name: idx_etv_nombre; Type: INDEX; Schema: public; Owner: edgargarcia
--

CREATE INDEX idx_etv_nombre ON public.catalogo_etv USING btree (nombre);


--
-- Name: idx_municipio_entidad; Type: INDEX; Schema: public; Owner: edgargarcia
--

CREATE INDEX idx_municipio_entidad ON public.catalogo_municipio USING btree (entidad_id);


--
-- Name: idx_proc_nombre; Type: INDEX; Schema: public; Owner: edgargarcia
--

CREATE INDEX idx_proc_nombre ON public.catalogo_procesadora USING btree (nombre);


--
-- Name: ix_admin_users_fullname; Type: INDEX; Schema: public; Owner: edgargarcia
--

CREATE UNIQUE INDEX ix_admin_users_fullname ON public.admin_users USING btree (fullname);


--
-- Name: ix_admin_users_role; Type: INDEX; Schema: public; Owner: edgargarcia
--

CREATE INDEX ix_admin_users_role ON public.admin_users USING btree (role);


--
-- Name: ix_admin_users_username; Type: INDEX; Schema: public; Owner: edgargarcia
--

CREATE UNIQUE INDEX ix_admin_users_username ON public.admin_users USING btree (username);


--
-- Name: ix_catalogo_productos_code; Type: INDEX; Schema: public; Owner: edgargarcia
--

CREATE UNIQUE INDEX ix_catalogo_productos_code ON public.catalogo_productos USING btree (code);


--
-- Name: ix_permisos_code; Type: INDEX; Schema: public; Owner: edgargarcia
--

CREATE UNIQUE INDEX ix_permisos_code ON public.permisos USING btree (code);


--
-- Name: ix_role_permisos_permiso_code; Type: INDEX; Schema: public; Owner: edgargarcia
--

CREATE INDEX ix_role_permisos_permiso_code ON public.role_permisos USING btree (permiso_code);


--
-- Name: ix_role_permisos_role; Type: INDEX; Schema: public; Owner: edgargarcia
--

CREATE INDEX ix_role_permisos_role ON public.role_permisos USING btree (role);


--
-- Name: ix_role_product_access_producto_code; Type: INDEX; Schema: public; Owner: edgargarcia
--

CREATE INDEX ix_role_product_access_producto_code ON public.role_product_access USING btree (producto_code);


--
-- Name: ix_role_product_access_role; Type: INDEX; Schema: public; Owner: edgargarcia
--

CREATE INDEX ix_role_product_access_role ON public.role_product_access USING btree (role);


--
-- Name: ix_solicitudes_estatus; Type: INDEX; Schema: public; Owner: edgargarcia
--

CREATE INDEX ix_solicitudes_estatus ON public.solicitudes USING btree (estatus);


--
-- Name: ix_solicitudes_producto; Type: INDEX; Schema: public; Owner: edgargarcia
--

CREATE INDEX ix_solicitudes_producto ON public.solicitudes USING btree (producto);


--
-- Name: ix_solicitudes_sef_unidades_sef_id; Type: INDEX; Schema: public; Owner: edgargarcia
--

CREATE INDEX ix_solicitudes_sef_unidades_sef_id ON public.solicitudes_sef_unidades USING btree (sef_id);


--
-- Name: catalogo_municipio catalogo_municipio_entidad_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.catalogo_municipio
    ADD CONSTRAINT catalogo_municipio_entidad_id_fkey FOREIGN KEY (entidad_id) REFERENCES public.catalogo_entidad(id);


--
-- Name: catalogo_procesadora catalogo_procesadora_cpae_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.catalogo_procesadora
    ADD CONSTRAINT catalogo_procesadora_cpae_id_fkey FOREIGN KEY (cpae_id) REFERENCES public.catalogo_cpae(id);


--
-- Name: catalogo_procesadora catalogo_procesadora_etv_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.catalogo_procesadora
    ADD CONSTRAINT catalogo_procesadora_etv_id_fkey FOREIGN KEY (etv_id) REFERENCES public.catalogo_etv(id);


--
-- Name: meeting_attendees meeting_attendees_meeting_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.meeting_attendees
    ADD CONSTRAINT meeting_attendees_meeting_id_fkey FOREIGN KEY (meeting_id) REFERENCES public.meeting_minutes(id) ON DELETE CASCADE;


--
-- Name: meeting_commitments meeting_commitments_meeting_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.meeting_commitments
    ADD CONSTRAINT meeting_commitments_meeting_id_fkey FOREIGN KEY (meeting_id) REFERENCES public.meeting_minutes(id) ON DELETE CASCADE;


--
-- Name: role_permisos role_permisos_permiso_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.role_permisos
    ADD CONSTRAINT role_permisos_permiso_code_fkey FOREIGN KEY (permiso_code) REFERENCES public.permisos(code);


--
-- Name: solicitudes_sef solicitudes_sef_solicitud_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.solicitudes_sef
    ADD CONSTRAINT solicitudes_sef_solicitud_id_fkey FOREIGN KEY (solicitud_id) REFERENCES public.solicitudes(id) ON DELETE CASCADE;


--
-- Name: solicitudes_sef_unidades solicitudes_sef_unidades_cpae_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.solicitudes_sef_unidades
    ADD CONSTRAINT solicitudes_sef_unidades_cpae_id_fkey FOREIGN KEY (cpae_id) REFERENCES public.catalogo_cpae(id);


--
-- Name: solicitudes_sef_unidades solicitudes_sef_unidades_entidad_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.solicitudes_sef_unidades
    ADD CONSTRAINT solicitudes_sef_unidades_entidad_id_fkey FOREIGN KEY (entidad_id) REFERENCES public.catalogo_entidad(id);


--
-- Name: solicitudes_sef_unidades solicitudes_sef_unidades_etv_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.solicitudes_sef_unidades
    ADD CONSTRAINT solicitudes_sef_unidades_etv_id_fkey FOREIGN KEY (etv_id) REFERENCES public.catalogo_etv(id);


--
-- Name: solicitudes_sef_unidades solicitudes_sef_unidades_municipio_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.solicitudes_sef_unidades
    ADD CONSTRAINT solicitudes_sef_unidades_municipio_id_fkey FOREIGN KEY (municipio_id) REFERENCES public.catalogo_municipio(id);


--
-- Name: solicitudes_sef_unidades solicitudes_sef_unidades_procesadora_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.solicitudes_sef_unidades
    ADD CONSTRAINT solicitudes_sef_unidades_procesadora_id_fkey FOREIGN KEY (procesadora_id) REFERENCES public.catalogo_procesadora(id);


--
-- Name: solicitudes_sef_unidades solicitudes_sef_unidades_sef_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: edgargarcia
--

ALTER TABLE ONLY public.solicitudes_sef_unidades
    ADD CONSTRAINT solicitudes_sef_unidades_sef_id_fkey FOREIGN KEY (sef_id) REFERENCES public.solicitudes_sef(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

