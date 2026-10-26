# Probar el esquema y los datos en PostgreSQL local (Docker + pgvector)

Guía para levantar una base PostgreSQL de prueba en Docker, aplicar el esquema del proyecto y poblarla con datos de ejemplo, con el fin de **revisar la información que el backend guarda en la base** y ensayar las consultas que usan el chat y el frontend.

> **Alcance.** El backend ya persiste en PostgreSQL: las rutas de usuarios, documentos, conversaciones y mensajes usan repositorios sobre las tablas de `App/migrations/001_schema.sql`. Esta guía levanta una base local con la misma estructura que Supabase, carga datos de ejemplo y muestra cómo verificarlos; la configuración para apuntar el backend a esa base (local o producción) está en la sección 8.

---

## 1. Requisitos

| Herramienta | Para qué | Notas |
|---|---|---|
| Docker Engine o Docker Desktop | Correr PostgreSQL sin instalarlo en el sistema | Verificar con `docker version` |
| Imagen `pgvector/pgvector:pg17` | PostgreSQL 17 + extensión `vector` | Se descarga sola (~400 MB) |
| `psql` | Ejecutar el schema y las consultas | **No hace falta instalarlo**: viene dentro del contenedor |
| DBeaver o Adminer | Ver tablas y filas con interfaz gráfica | Opcional (paso 5) |

La imagen oficial `postgres:17` **no sirve**: el esquema hace `create extension vector` y crea un índice HNSW. Por eso se usa `pgvector/pgvector:pg17`.

### Permisos de Docker en Linux

Si `docker ps` responde `permission denied while trying to connect to the Docker daemon socket`, el usuario no está en el grupo `docker`:

```bash
sudo usermod -aG docker $USER
```

Cerrar sesión y volver a entrar (o reiniciar) para que el cambio aplique. Mientras tanto, se puede anteponer `sudo` a los comandos `docker` de esta guía.

Verificación:

```bash
docker version
```

---

## 2. Levantar la base local

Desde la raíz del repositorio:

```bash
docker run -d --name raguaco-db \
  -e POSTGRES_USER=raguaco \
  -e POSTGRES_PASSWORD=raguaco \
  -e POSTGRES_DB=raguaco \
  -p 5433:5432 \
  -v raguaco_pgdata:/var/lib/postgresql/data \
  pgvector/pgvector:pg17
```

Qué hace cada opción:

| Opción | Motivo |
|---|---|
| `--name raguaco-db` | Nombre fijo para el resto de comandos |
| `POSTGRES_*` | Usuario, clave y base descartables, solo para desarrollo local |
| `-p 5433:5432` | Expone la base en el puerto **5433** para no chocar con un PostgreSQL del sistema ni con Supabase CLI |
| `-v raguaco_pgdata` | Volumen nombrado: los datos sobreviven a `docker stop` / `docker start` |
| `pgvector/pgvector:pg17` | PostgreSQL 17 con `vector` ya disponible |

Esperar a que acepte conexiones:

```bash
docker exec raguaco-db pg_isready -U raguaco -d raguaco
```

Debe imprimir `.../5432 - accepting connections`. Si no responde en unos segundos, revisar `docker logs raguaco-db`.

Si el contenedor ya existe de una sesión anterior, no volver a ejecutar `docker run` (fallaría por nombre duplicado); basta con:

```bash
docker start raguaco-db
```

### Verificar que pgvector está disponible

```bash
docker exec -i raguaco-db psql -U raguaco -d raguaco \
  -c "select extname, extversion from pg_extension where extname = 'vector';"
```

Todavía no devuelve filas: la extensión se crea en el paso siguiente.

---

## 3. Aplicar el esquema

El schema vive en `App/migrations/001_schema.sql` y se aplica tal cual (el mismo archivo que se pega en el SQL Editor de Supabase).

```bash
docker cp App/migrations/001_schema.sql raguaco-db:/tmp/001_schema.sql
docker exec -i raguaco-db psql -U raguaco -d raguaco \
  -v ON_ERROR_STOP=1 -f /tmp/001_schema.sql
```

`-v ON_ERROR_STOP=1` hace que psql se detenga en el primer error en lugar de continuar y dejar el schema a medias.

> En Windows, `docker cp` y `docker exec` funcionan igual desde PowerShell o CMD. Evita redirigir el archivo con `<`, que PowerShell no soporta.

Verificar que se crearon las seis tablas:

```bash
docker exec raguaco-db psql -U raguaco -d raguaco -c '\dt'
```

Salida esperada:

```text
              List of relations
 Schema |       Name        | Type  | Owner
--------+-------------------+-------+---------
 public | chunk             | table | raguaco
 public | conversacion      | table | raguaco
 public | documento         | table | raguaco
 public | mensaje           | table | raguaco
 public | referencia_fuente | table | raguaco
 public | usuario           | table | raguaco
(6 rows)
```

Verificar la columna vectorial y el índice HNSW:

```bash
docker exec raguaco-db psql -U raguaco -d raguaco -c '\d chunk'
```

Debe aparecer `embedding | vector(384)` y el índice `chunk_embedding_idx` de tipo `hnsw`.

---

## 4. Cargar los datos de prueba

El archivo `App/migrations/seed_dev.sql` crea datos de ejemplo (cargarlo es **opcional**: el backend también puede crear usuarios, documentos y conversaciones por la API):

- 1 usuario demo.
- 3 documentos con los estados que muestra el frontend: `listo` (48 págs., 100 %), `procesando` (62 %) y `error` (con el motivo en `metadata`).
- 6 chunks con página, sección y un vector aleatorio de 384 dimensiones (uno queda sin vector para representar una ingesta a medias).
- 2 conversaciones y 6 mensajes (`usuario` / `asistente`).
- 4 referencias de fuente con su similitud y orden.

```bash
docker cp App/migrations/seed_dev.sql raguaco-db:/tmp/seed_dev.sql
docker exec -i raguaco-db psql -U raguaco -d raguaco \
  -v ON_ERROR_STOP=1 -f /tmp/seed_dev.sql
```

> Los embeddings son **aleatorios**: permiten comprobar que el tipo `vector` y el operador de distancia funcionan, pero la similitud no tiene significado semántico. Los vectores reales los calculará `multilingual-e5-small` (384 dimensiones) durante la ingesta.

Comprobar los conteos:

```bash
docker exec raguaco-db psql -U raguaco -d raguaco -c "
select 'usuario' as tabla, count(*) from usuario
union all select 'documento', count(*) from documento
union all select 'chunk', count(*) from chunk
union all select 'conversacion', count(*) from conversacion
union all select 'mensaje', count(*) from mensaje
union all select 'referencia_fuente', count(*) from referencia_fuente
order by tabla;"
```

Resultado esperado:

| tabla | count |
|---|---:|
| chunk | 6 |
| conversacion | 2 |
| documento | 3 |
| mensaje | 6 |
| referencia_fuente | 4 |
| usuario | 1 |

El seed es idempotente (`on conflict do nothing` y UUID fijos): se puede volver a ejecutar sin duplicar filas. Para dejarlo como nuevo:

```sql
truncate table referencia_fuente, mensaje, conversacion,
               chunk, documento, usuario cascade;
```

---

## 5. Visualizar la información

### Opción A — `psql` dentro del contenedor (sin instalar nada)

Abrir una sesión interactiva:

```bash
docker exec -it raguaco-db psql -U raguaco -d raguaco
```

Comandos útiles dentro de `psql`:

| Comando | Qué hace |
|---|---|
| `\dt` | Lista las tablas |
| `\d+ documento` | Columnas, tipos, índices y llaves |
| `\x auto` | Cambia a salida vertical cuando la fila es ancha (útil con textos largos) |
| `\dv` | Lista las vistas |
| `\q` | Salir |

### Opción B — DBeaver (GUI recomendada)

1. Descargar DBeaver Community desde <https://dbeaver.io/download/> (instalador `.deb`, Flatpak o AppImage).
2. Crear una conexión **PostgreSQL** con estos datos:

   | Campo | Valor |
   |---|---|
   | Host | `localhost` |
   | Port | `5433` |
   | Database | `raguaco` |
   | Username | `raguaco` |
   | Password | `raguaco` |

3. Probar la conexión y explorar `public` → `Tables` / `Views`.
4. Para no ver la columna `embedding` (un vector de 384 números), usar las vistas `v_documento_resumen` y `v_chat_con_fuentes`.

**1. Pantalla de documentos (con avance de ingesta y conteo de chunks):**

```sql
select nombre, formato, categoria, estado, progreso, num_paginas,
       chunks, chunks_con_vector, propietario, fecha_carga, motivo_error
from v_documento_resumen
order by fecha_carga desc;
```

Debe mostrar el documento `procesando` con 62 %, el `error` con su motivo y el `listo` con 100 %. El documento en proceso ya tiene 2 chunks vectorizados (ingesta parcial); el que falló tiene 1 chunk sin vector (`chunks_con_vector` en 0) y el listo, 3.

**2. Conversación completa con las fuentes citadas (RF8):**

```sql
select fecha, rol, contenido, documento_fuente, pagina, similitud, orden
from v_chat_con_fuentes
where conversacion = 'Vacaciones y permisos'
order by fecha, orden;
```

Las respuestas del asistente aparecen con `documento_fuente`, `pagina`, `similitud` (0.94, 0.87, 0.91) y `orden` (1, 2). Las preguntas del usuario quedan con esas columnas en `NULL`, porque no citan fuentes.

**3. Búsqueda por similitud con pgvector:**

```sql
with consulta as (
  select embedding from chunk
  where id = '20000000-0000-4000-8000-000000000004'
)
select c.contenido,
       1 - (c.embedding <=> consulta.embedding) as similitud
from chunk c, consulta
order by c.embedding <=> consulta.embedding
limit 5;
```

El primer resultado debe ser el mismo chunk usado como consulta, con similitud `1`. Esto valida el operador coseno `<=>`. El índice HNSW se comprobó en el paso 3; con solo 6 filas el planner probablemente resuelva la consulta con un *sequential scan*, lo cual es normal a esta escala.

**4. Trazabilidad de una respuesta (join manual, sin vista):**

```sql
select m.rol, m.contenido, d.nombre, c.pagina, c.metadata ->> 'seccion' as seccion,
       r.similitud, r.orden
from mensaje m
join referencia_fuente r on r.mensaje_id = m.id
join chunk c on c.id = r.chunk_id
join documento d on d.id = c.documento_id
where m.conversacion_id = '30000000-0000-4000-8000-000000000001'
order by m.fecha, r.orden;
```

**5. Metadatos y errores de ingesta:**

```sql
select nombre, estado, metadata ->> 'error' as motivo
from documento
where metadata ? 'error';
```

**6. Confirmar que RLS está activo (como lo define el schema):**

```sql
select relname, relrowsecurity
from pg_class
where relname in ('usuario', 'documento', 'chunk',
                  'conversacion', 'mensaje', 'referencia_fuente')
order by relname;
```

Las seis filas deben tener `relrowsecurity = true`. La conexión local usa el usuario dueño (`raguaco`), que no queda bloqueado por RLS; un rol limitado o la *anon key* de Supabase sí verían las tablas vacías hasta definir políticas.

---

## 6. Apagar, reiniciar y borrar

```bash
# Detener sin perder datos
docker stop raguaco-db

# Volver a levantar
docker start raguaco-db

# Eliminar contenedor y GUI (los datos del volumen siguen ahí)
docker rm -f raguaco-db raguaco-admin

# Borrar también los datos (empezar de cero)
docker volume rm raguaco_pgdata
```

Si se borra el volumen, repetir los pasos 2 a 4.

---

## 7. Posibles problemas y solución

| Síntoma | Causa | Solución |
|---|---|---|
| `permission denied ... docker.sock` | Usuario fuera del grupo `docker` | `sudo usermod -aG docker $USER` y reiniciar sesión, o usar `sudo` |
| `port is already allocated` en 5433 | Otro servicio usa el puerto | Cambiar a `-p 5434:5432` y ajustar host/puerto en el cliente |
| `type "vector" does not exist` | Se usó la imagen `postgres:17` | Usar `pgvector/pgvector:pg17` |
| `relation "usuario" already exists` | El schema ya se aplicó | Omitir el paso 3 o recrear el volumen |
| `duplicate key value violates unique constraint` al cargar el seed | Quedaron filas de una prueba anterior con otros UUID | Ejecutar el `truncate ... cascade` del paso 4 y repetir |
| La GUI muestra las tablas vacías | Se conectó con un rol sujeto a RLS | Conectarse como `raguaco` (dueño) en local |
| `docker: command not found` | Docker no está instalado o no está en el `PATH` | Instalar Docker Engine / Docker Desktop |
| `PoolTimeout` o `connection refused` al arrancar uvicorn | La base no está levantada o `DATABASE_URL` apunta a otro puerto | `docker start raguaco-db` y revisar `DATABASE_URL` |
| `password authentication failed` | Credenciales incorrectas en `DATABASE_URL` | Usar `raguaco:raguaco` en local o la cadena real de Supabase |
| `ModuleNotFoundError: psycopg` | Faltan las dependencias nuevas | `pip install -r requirements.txt` |
| `relation "usuario" does not exist` | El schema no se aplicó a esa base | Ejecutar el paso 3 sobre la base correcta |

---

## 8. Backend conectado a PostgreSQL

El backend persiste en PostgreSQL. El flujo es:

```text
ruta FastAPI → repositorio → pool de psycopg → PostgreSQL
```

### Configuración

`App/core/config.py` lee `DATABASE_URL` del entorno o de un archivo `.env` en la raíz del repositorio (o en `App/.env`). El archivo `.env` no se versiona.

| Entorno | `DATABASE_URL` |
|---|---|
| Docker local | `postgresql://raguaco:raguaco@localhost:5433/raguaco` |
| Supabase (producción) | `postgresql://postgres.<proyecto>:<clave>@<host>:5432/postgres?sslmode=require` |

> Usar el esquema `postgresql://` de libpq, no `postgresql+psycopg://` (ese formato es exclusivo de SQLAlchemy). La cadena de Supabase se copia desde *Project Settings → Database → Connection string*; nunca se escribe en el código ni se sube al repositorio (RNF5).

Crear el archivo y ajustar la cadena:

```bash
cp .env.example .env
# editar .env y definir DATABASE_URL
```

### Arrancar

La base debe estar levantada **antes** de uvicorn: el pool abre conexiones y espera hasta 10 segundos; si no encuentra la base, el arranque falla con un error de conexión.

```bash
# 1) base local (pasos 2 a 4 de esta guía, si aún no está)
docker start raguaco-db

# 2) backend (ya está indicado también en el paso 3 del README inicial)
cd App && uvicorn main:app --reload
```

### Verificar que escribe en la base

> Este apartado es opcional.
> Aplica cuando hay dudas en la existencia de la conexión con la base de datos local.

Con la API en `http://127.0.0.1:8000` (o cual sea el puerto definido), crear datos en orden (un documento o una conversación necesitan un `usuario_id` existente por la llave foránea):

```bash
# 1) usuario; guardar el id devuelto
curl -X POST http://127.0.0.1:8000/v1/models/users/ \
  -H 'Content-Type: application/json' \
  -d '{"nombre": "Ana García", "email": "ana@raguaco.test"}'

# 2) conversación (reemplazar USUARIO_ID)
curl -X POST http://127.0.0.1:8000/v1/models/conversations/ \
  -H 'Content-Type: application/json' \
  -d '{"usuario_id": "USUARIO_ID"}'

# 3) mensaje (reemplazar CONVERSACION_ID)
curl -X POST http://127.0.0.1:8000/v1/models/conversations/CONVERSACION_ID/messages \
  -H 'Content-Type: application/json' \
  -d '{"rol": "usuario", "contenido": "¿Cuántos días de vacaciones me corresponden?"}'
```

También se puede usar la documentación interactiva en el endpoint `.../docs` que integra FastAPI.

Comprobar en la base:

```bash
docker exec raguaco-db psql -U raguaco -d raguaco \
  -c "select id, nombre, email from usuario order by nombre;"
```

> [!WARNING]
> Los datos sobreviven a reinicios de uvicorn y a `docker stop` / `docker start`. Solo se pierden si se borra el volumen (`docker volume rm raguaco_pgdata`).

### Producción (Supabase)

1. Pegar `App/migrations/001_schema.sql` en el SQL Editor (y, si se quieren datos demo, `seed_dev.sql`).
2. Configurar `DATABASE_URL` con la cadena de la base de Supabase, no con la *anon key*: RLS está activo en todas las tablas y la API accede como dueño de la base.
3. No versionar `.env`; en el hosting, definir `DATABASE_URL` como variable de entorno.

> El `seed_dev.sql` es solo para desarrollo: contiene UUID fijos y embeddings aleatorios.

## 9. Extras

### Capas que implementa el backend

| Archivo | Responsabilidad |
|---|---|
| `App/core/config.py` | Lee `DATABASE_URL` del entorno / `.env` |
| `App/infrastructure/db/session.py` | Pool asíncrono de psycopg y apertura/cierre en el ciclo de vida |
| `App/api/deps.py` | `get_db` (una conexión por petición) y proveedores de repositorios |
| `App/infrastructure/db/repositories/` | SQL de usuarios, documentos, conversaciones y mensajes |
| `App/api/routes/` | Validación de la petición, reglas de la API y errores HTTP |

Cada petición toma una conexión del pool; al terminar sin errores se hace `commit` y, si falla, `rollback` (lo hace el context manager de `psycopg_pool`).