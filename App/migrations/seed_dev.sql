-- =====================================================================
-- RAGUACO · Datos de prueba para desarrollo local
-- Se ejecuta DESPUÉS de 001_schema.sql.
--
-- Objetivo: poblar la base con datos con la misma forma que producirá la
-- aplicación, para revisar el schema, las relaciones y las consultas sin
-- esperar a que el backend escriba en Postgres (hoy usa dicts en memoria).
--
-- IMPORTANTE:
--   * Los embeddings son aleatorios de 384 dimensiones. Sirven para probar
--     que el tipo `vector` y el operador `<=>` funcionan, pero la similitud
--     que devuelven no tiene significado semántico.
--   * Los UUID son fijos para que el seed se pueda reejecutar sin duplicar
--     filas y para que las consultas de la guía sean copiables.
--   * Para dejar la base como nueva:
--       truncate table referencia_fuente, mensaje, conversacion,
--                      chunk, documento, usuario cascade;
--     y volver a ejecutar este archivo.
-- =====================================================================

begin;

-- 1) USUARIO ----------------------------------------------------------
insert into usuario (id, nombre, email)
values (
  '00000000-0000-4000-8000-000000000001',
  'Ana García',
  'ana.garcia@raguaco.com'
)
on conflict do nothing;

-- 2) DOCUMENTO --------------------------------------------------------
-- Tres estados distintos: listo, procesando (62 %) y error.
insert into documento (
  id, usuario_id, nombre, formato, ruta_original, categoria, estado,
  fecha_carga, num_paginas, progreso, fecha_actualizacion, metadata
)
values
  (
    '10000000-0000-4000-8000-000000000001',
    '00000000-0000-4000-8000-000000000001',
    'reglamento_estudiantil.pdf',
    'pdf',
    'storage/ana/reglamento_estudiantil.pdf',
    'Normativa',
    'listo',
    now() - interval '6 days',
    48,
    100,
    now() - interval '6 days' + interval '12 minutes',
    '{"autor": "Secretaría Académica", "idioma": "es"}'::jsonb
  ),
  (
    '10000000-0000-4000-8000-000000000002',
    '00000000-0000-4000-8000-000000000001',
    'politica_vacaciones.pdf',
    'pdf',
    'storage/ana/politica_vacaciones.pdf',
    'Talento humano',
    'procesando',
    now() - interval '12 minutes',
    null,
    62,
    now() - interval '2 minutes',
    '{}'::jsonb
  ),
  (
    '10000000-0000-4000-8000-000000000003',
    '00000000-0000-4000-8000-000000000001',
    'acta_consejo_2025.pdf',
    'pdf',
    'storage/ana/acta_consejo_2025.pdf',
    'Actas',
    'error',
    now() - interval '1 day',
    8,
    18,
    now() - interval '23 hours',
    '{"error": "PDF escaneado sin capa de texto (OCR pendiente)"}'::jsonb
  )
on conflict do nothing;

-- 3) CHUNK ------------------------------------------------------------
-- El embedding se genera con una subconsulta LATERAL para que cada fila
-- tenga un vector distinto. `array_agg(...)::vector` produce vector(384).
-- El último chunk queda sin vector a propósito: representa un fragmento
-- extraído de un documento que falló antes de la fase de embeddings.
insert into chunk (id, documento_id, contenido, indice, pagina, metadata, embedding)
select
  v.id,
  v.documento_id,
  v.contenido,
  v.indice,
  v.pagina,
  v.metadata,
  e.embedding
from (values
  (
    '20000000-0000-4000-8000-000000000001'::uuid,
    '10000000-0000-4000-8000-000000000001'::uuid,
    'Artículo 12. Para formalizar la matrícula, el estudiante debe presentar documento de identidad, diploma de bachiller y el recibo de pago de derechos académicos. La Secretaría Académica verifica los requisitos antes de activar el registro.',
    0, 12, '{"seccion": "3.1"}'::jsonb, true
  ),
  (
    '20000000-0000-4000-8000-000000000002'::uuid,
    '10000000-0000-4000-8000-000000000001'::uuid,
    'Artículo 45. Son deberes del estudiante asistir puntualmente a las actividades académicas, respetar los reglamentos y cuidar los bienes de la universidad. El incumplimiento reiterado da lugar a un proceso disciplinario.',
    1, 24, '{"seccion": "5.2"}'::jsonb, true
  ),
  (
    '20000000-0000-4000-8000-000000000003'::uuid,
    '10000000-0000-4000-8000-000000000001'::uuid,
    'Artículo 60. Las solicitudes de homologación se radican ante la facultad dentro de los primeros cinco días hábiles del semestre, acompañadas del programa de la asignatura cursada y su certificado de notas.',
    2, 31, '{"seccion": "7.1"}'::jsonb, true
  ),
  (
    '20000000-0000-4000-8000-000000000004'::uuid,
    '10000000-0000-4000-8000-000000000002'::uuid,
    'Todo colaborador vinculado mediante contrato laboral tiene derecho a 15 días hábiles de vacaciones remuneradas por cada año de servicio. Los días se contabilizan de lunes a viernes y no incluyen festivos.',
    0, 3, '{"seccion": "2.1"}'::jsonb, true
  ),
  (
    '20000000-0000-4000-8000-000000000005'::uuid,
    '10000000-0000-4000-8000-000000000002'::uuid,
    'La solicitud de vacaciones debe radicarse en el sistema de Talento Humano con al menos 15 días hábiles de anticipación y contar con la aprobación del jefe inmediato.',
    1, 4, '{"seccion": "2.2"}'::jsonb, true
  ),
  (
    '20000000-0000-4000-8000-000000000006'::uuid,
    '10000000-0000-4000-8000-000000000003'::uuid,
    'Acta 04 del Consejo Académico. Se discute la actualización del calendario académico para el periodo 2025-1. La votación queda pendiente hasta contar con el concepto de la Vicerrectoría Académica.',
    0, 2, '{"ocr": false}'::jsonb, false
  )
) as v(id, documento_id, contenido, indice, pagina, metadata, con_vector)
cross join lateral (
  select case
           when v.con_vector then array_agg((random() * 2 - 1)::real)::vector
           else null
         end as embedding
  from generate_series(1, 384)
) as e
on conflict do nothing;

-- 4) CONVERSACION -----------------------------------------------------
insert into conversacion (
  id, usuario_id, titulo, fecha_creacion, fecha_actualizacion
)
values
  (
    '30000000-0000-4000-8000-000000000001',
    '00000000-0000-4000-8000-000000000001',
    'Vacaciones y permisos',
    now() - interval '2 days',
    now() - interval '2 days' + interval '4 minutes'
  ),
  (
    '30000000-0000-4000-8000-000000000002',
    '00000000-0000-4000-8000-000000000001',
    'Matrícula y requisitos',
    now() - interval '5 days',
    now() - interval '5 days' + interval '1 minute'
  )
on conflict do nothing;

-- 5) MENSAJE ----------------------------------------------------------
insert into mensaje (id, conversacion_id, rol, contenido, fecha)
values
  (
    '40000000-0000-4000-8000-000000000001',
    '30000000-0000-4000-8000-000000000001',
    'usuario',
    '¿Cuántos días de vacaciones me corresponden al año?',
    now() - interval '2 days'
  ),
  (
    '40000000-0000-4000-8000-000000000002',
    '30000000-0000-4000-8000-000000000001',
    'asistente',
    'Según la Política de vacaciones (pág. 3), tienes derecho a 15 días hábiles remunerados por cada año de servicio. No se incluyen fines de semana ni festivos.',
    now() - interval '2 days' + interval '20 seconds'
  ),
  (
    '40000000-0000-4000-8000-000000000003',
    '30000000-0000-4000-8000-000000000001',
    'usuario',
    '¿Con cuánta anticipación debo solicitarlas?',
    now() - interval '2 days' + interval '2 minutes'
  ),
  (
    '40000000-0000-4000-8000-000000000004',
    '30000000-0000-4000-8000-000000000001',
    'asistente',
    'La solicitud debe radicarse con al menos 15 días hábiles de anticipación y requiere la aprobación de tu jefe inmediato (Política de vacaciones, pág. 4).',
    now() - interval '2 days' + interval '2 minutes 20 seconds'
  ),
  (
    '40000000-0000-4000-8000-000000000005',
    '30000000-0000-4000-8000-000000000002',
    'usuario',
    '¿Qué documentos necesito para matricularme?',
    now() - interval '5 days'
  ),
  (
    '40000000-0000-4000-8000-000000000006',
    '30000000-0000-4000-8000-000000000002',
    'asistente',
    'Para formalizar la matrícula debes presentar documento de identidad, diploma de bachiller y el recibo de pago de derechos académicos (Reglamento estudiantil, pág. 12).',
    now() - interval '5 days' + interval '30 seconds'
  )
on conflict do nothing;

-- 6) REFERENCIA_FUENTE ------------------------------------------------
-- Cada respuesta del asistente cita los chunks que la respaldan (RF8/RNF7).
insert into referencia_fuente (id, mensaje_id, chunk_id, similitud, orden)
values
  (
    '50000000-0000-4000-8000-000000000001',
    '40000000-0000-4000-8000-000000000002',
    '20000000-0000-4000-8000-000000000004',
    0.94, 1
  ),
  (
    '50000000-0000-4000-8000-000000000002',
    '40000000-0000-4000-8000-000000000002',
    '20000000-0000-4000-8000-000000000005',
    0.87, 2
  ),
  (
    '50000000-0000-4000-8000-000000000003',
    '40000000-0000-4000-8000-000000000004',
    '20000000-0000-4000-8000-000000000005',
    0.91, 1
  ),
  (
    '50000000-0000-4000-8000-000000000004',
    '40000000-0000-4000-8000-000000000006',
    '20000000-0000-4000-8000-000000000001',
    0.89, 1
  )
on conflict do nothing;

commit;

-- =====================================================================
-- Vistas de apoyo para revisar los datos sin mirar los embeddings.
-- =====================================================================

-- Pantalla "Documentos": una fila por documento con el avance de ingesta.
create or replace view v_documento_resumen as
select
  d.id,
  d.nombre,
  d.formato,
  d.categoria,
  d.estado,
  d.progreso,
  d.num_paginas,
  u.nombre as propietario,
  d.fecha_carga,
  d.fecha_actualizacion,
  d.metadata ->> 'error' as motivo_error,
  count(c.id) as chunks,
  count(c.embedding) as chunks_con_vector
from documento d
join usuario u on u.id = d.usuario_id
left join chunk c on c.documento_id = d.id
group by d.id, u.nombre;

-- Pantalla "Historial": conversación → mensajes → fuentes citadas.
create or replace view v_chat_con_fuentes as
select
  m.id as mensaje_id,
  m.conversacion_id,
  cv.titulo as conversacion,
  m.fecha,
  m.rol,
  m.contenido,
  d.nombre as documento_fuente,
  c.pagina,
  r.similitud,
  r.orden
from mensaje m
join conversacion cv on cv.id = m.conversacion_id
left join referencia_fuente r on r.mensaje_id = m.id
left join chunk c on c.id = r.chunk_id
left join documento d on d.id = c.documento_id;
