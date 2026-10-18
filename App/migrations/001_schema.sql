-- =====================================================================
-- RAGUACO · Esquema inicial de base de datos (Supabase / PostgreSQL)
-- Basado en el diagrama entidad-relación del proyecto.
-- Versión 2: incluye las columnas que pide el mockup y FRONTEND_SPEC.md
-- (progreso, num_paginas, titulo, fecha_actualizacion, orden).
-- Cómo usarlo: Supabase -> SQL Editor -> New query -> pegar -> Run.
-- IMPORTANTE: confirma con Juan el modelo de embeddings ANTES de correrlo
-- y cambia el 384 de la tabla chunk si el modelo usa otra dimensión.
-- =====================================================================

create extension if not exists vector;

-- 1) USUARIO ----------------------------------------------------------
create table usuario (
  id     uuid primary key default gen_random_uuid(),
  nombre text not null,
  email  text not null unique
);

-- 2) DOCUMENTO --------------------------------------------------------
create table documento (
  id            uuid primary key default gen_random_uuid(),
  usuario_id    uuid not null references usuario(id) on delete cascade,
  nombre        text not null,
  formato       text not null,                -- pdf, docx, txt
  ruta_original text,                         -- dónde quedó el archivo original
  categoria     text,
  estado        text not null default 'pendiente'
                check (estado in ('pendiente', 'procesando', 'listo', 'error')),
  fecha_carga   timestamptz not null default now(),
  num_paginas   int,                          -- "48 págs." (pantalla de inicio / detalle)
  progreso      int not null default 0
                check (progreso between 0 and 100),   -- "Indexando 62%"
  fecha_actualizacion timestamptz not null default now(),  -- "Actividad reciente"
  metadata      jsonb not null default '{}'::jsonb
);

-- 3) CHUNK (fragmentos + su vector) -----------------------------------
create table chunk (
  id           uuid primary key default gen_random_uuid(),
  documento_id uuid not null references documento(id) on delete cascade,
  contenido    text not null,
  indice       int  not null,
  pagina       int,
  metadata     jsonb not null default '{}'::jsonb,  -- p. ej. {"seccion": "4.2"} (pantalla de evidencia)
  embedding    vector(384),                   -- <-- la dimensión depende del modelo
  unique (documento_id, indice)
);

-- 4) CONVERSACION -----------------------------------------------------
create table conversacion (
  id             uuid primary key default gen_random_uuid(),
  usuario_id     uuid not null references usuario(id) on delete cascade,
  titulo         text,                        -- "Vacaciones y permisos" (Historial)
  fecha_creacion timestamptz not null default now(),
  fecha_actualizacion timestamptz not null default now()   -- fecha que muestra el Historial
);

-- 5) MENSAJE ----------------------------------------------------------
create table mensaje (
  id              uuid primary key default gen_random_uuid(),
  conversacion_id uuid not null references conversacion(id) on delete cascade,
  rol             text not null,              -- acordar valores con Juan (p. ej. 'user' / 'assistant')
  contenido       text not null,
  fecha           timestamptz not null default now()
);

-- 6) REFERENCIA_FUENTE (qué fragmentos respaldan cada respuesta) ------
create table referencia_fuente (
  id         uuid primary key default gen_random_uuid(),
  mensaje_id uuid not null references mensaje(id) on delete cascade,
  chunk_id   uuid not null references chunk(id) on delete cascade,
  similitud  real,                            -- "Relevancia 94%" (el mockup la muestra)
  orden      int                              -- "Fuente 1", "Fuente 2"
);

-- Índices -------------------------------------------------------------
create index on chunk (documento_id);
create index on mensaje (conversacion_id, fecha);
create index on referencia_fuente (mensaje_id);
create index on referencia_fuente (chunk_id);
-- Búsqueda por cercanía (similitud del coseno) rápida:
create index on chunk using hnsw (embedding vector_cosine_ops);

-- Seguridad: bloquea el acceso público directo por la API automática de
-- Supabase. El backend se conecta con la clave de la base de datos, que
-- no se ve afectada por esto.
alter table usuario           enable row level security;
alter table documento         enable row level security;
alter table chunk             enable row level security;
alter table conversacion      enable row level security;
alter table mensaje           enable row level security;
alter table referencia_fuente enable row level security;

-- Usuario de prueba (hasta que exista autenticación real) -------------
-- insert into usuario (nombre, email) values ('Demo', 'demo@raguaco.test');
