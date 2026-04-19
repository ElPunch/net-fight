# Fight.net - Plataforma de Eventos de Combate

Proyecto educativo en Django + Django Rest Framework + PostgreSQL. Soporta dos
roles (peleador / promotor), creacion de eventos con cartelera de
enfrentamientos, registro a eventos con QR, check-in y comentarios.

---

## Modelo de datos (principales)

| Tabla              | Descripcion                                                           |
|--------------------|-----------------------------------------------------------------------|
| `auth_user`        | Modelo de usuario de Django.                                          |
| `UserProfile`      | Extiende User con `rol` (fighter/promoter/admin) y datos de peleador. |
| `Event`            | Evento deportivo (titulo, descripcion, fecha, ubicacion, estado).     |
| `EventRegistration`| Registro de usuario a evento + QR + check-in.                         |
| `Comment`          | Comentarios de usuarios sobre eventos.                                |
| `Fight`            | **NUEVO**: Enfrentamiento entre dos peleadores dentro de un evento.   |
| `EventCreationLog` | Auditoria de creacion de eventos.                                     |

### Novedades de este entregable

* **Cartelera de enfrentamientos** - Al crear un evento, el promotor puede
  seleccionar peleadores existentes del sistema y anunciar uno o mas
  enfrentamientos. La cartelera se muestra en el anuncio (detalle) del evento
  y en el listado de eventos disponibles.
* **Django Rest Framework** - Todos los endpoints JSON migrados a DRF
  (serializers, viewsets, routers, permisos). Se restringen los metodos HTTP
  por recurso: por ejemplo `/api/fighters/` solo acepta GET y `/api/logs/` es
  de solo lectura.
* **Contenerizacion con Docker Compose** - Tres servicios: `db` (Postgres),
  `backend` (Django + Gunicorn) y `frontend` (Nginx sirviendo estaticos y
  proxeando al backend).

---

## Endpoints DRF

Base: `/api/`

| Endpoint                              | Metodos permitidos | Descripcion                                       |
|---------------------------------------|--------------------|---------------------------------------------------|
| `/api/events/`                        | GET, POST          | Listar eventos activos / crear evento (promotor)  |
| `/api/events/{id}/`                   | GET, PUT, PATCH, DELETE | Detalle / editar / eliminar (dueno)          |
| `/api/events/{id}/fights/`            | GET, POST          | Lista / agregar enfrentamiento al evento          |
| `/api/fights/{id}/`                   | GET, PUT, PATCH, DELETE | Gestionar enfrentamiento                     |
| `/api/fighters/`                      | **GET unicamente** | Peleadores disponibles (para el modal)            |
| `/api/mis-eventos/`                   | **GET unicamente** | Eventos propios del promotor                      |
| `/api/register-event/`                | **POST unicamente**| Registrar peleador a evento                       |
| `/api/event-attendees/{id}/`          | **GET unicamente** | Asistentes de un evento                           |
| `/api/my-registration/{id}/`          | **GET unicamente** | Mi registro a un evento                           |
| `/api/event-comments/{id}/`           | GET, POST          | Comentarios de un evento                          |
| `/api/check-in/`                      | **POST unicamente**| Validar QR (solo promotor)                        |
| `/api/me/`                            | GET, PUT, PATCH, POST | Datos y edicion del perfil del usuario actual  |
| `/api/logs/` y `/api/logs/{id}/`      | **GET unicamente** | Auditoria (solo lectura)                          |

---

## Correr el proyecto - opcion A: Docker Compose (recomendada)

Requisitos: Docker Desktop / Docker Engine + Docker Compose.

```bash
cp .env.example .env          # editar si se desea
docker compose up --build
```

El servicio `frontend` (Nginx) queda disponible en `http://localhost`, y el
backend Django directamente en `http://localhost:8000`.

La primera vez, el entrypoint corre `migrate` y `collectstatic`.

Para crear un superusuario:

```bash
docker compose exec backend python manage.py createsuperuser
```

### Estructura de contenedores

```
  +-----------+     +-----------+     +-----------+
  |  Nginx    | --> |  Django   | --> | Postgres  |
  | (puerto 80)|    | (DRF, 8000)|    | (5432)    |
  +-----------+     +-----------+     +-----------+
     frontend          backend             db
```

---

## Correr el proyecto - opcion B: Local (sin Docker)

```bash
python -m venv venv
# Linux/Mac:  source venv/bin/activate
# Windows:    venv\Scripts\activate
pip install -r requirements.txt

# Asegurate de tener Postgres corriendo y la base creada.
# Los parametros default son: DB=fightnet_db, USER=postgres, PASS=mfdoom.
# Puedes sobreescribirlos con variables de entorno.

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

App disponible en `http://localhost:8000`.

---

## Flujo rapido para probar la funcionalidad de enfrentamientos

1. Registrar dos o mas usuarios con rol **peleador** (desde `/register/`).
2. Registrar un usuario con rol **promotor** y entrar con esa cuenta.
3. En el panel del promotor, click en **"+ Crear evento"**.
4. Llenar titulo, descripcion, fecha, ubicacion.
5. En la seccion **"Cartelera del evento"**, click en
   **"+ Agregar enfrentamiento"** y seleccionar dos peleadores distintos.
6. (Opcional) Escribir un titulo como "Pelea estelar". Se pueden agregar
   tantos enfrentamientos como se necesiten.
7. Click en **"Crear evento"**.
8. Desde el dashboard del peleador o desde el detalle del evento se vera la
   cartelera completa con los peleadores anunciados.

---

## Punto extra: Despliegue en linea

Para obtener los 3 puntos extra, el mismo `docker-compose.yml` corre tal cual
en cualquier VPS con Docker. Ajustar:

1. En `.env`: `DJANGO_DEBUG=False`, `DJANGO_ALLOWED_HOSTS=<ip-o-dominio>`,
   `DJANGO_CSRF_TRUSTED_ORIGINS=http://<ip>` o `https://<dominio>`.
2. Abrir puerto 80 (y 443 si se configura TLS) en el firewall.
3. `docker compose up -d --build`.
