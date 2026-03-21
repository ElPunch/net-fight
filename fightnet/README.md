# Fight.net – Plataforma de Eventos de Combate
## Guía de instalación y ejecución paso a paso

---

## Estructura del proyecto

```
fightnet/
├── fightnet/               ← Configuración del proyecto Django
│   ├── settings.py         ← Base de datos, apps instaladas, rutas de media
│   ├── urls.py             ← URLs raíz
│   └── wsgi.py
├── events/                 ← Única app del proyecto
│   ├── models.py           ← 5 tablas de la base de datos
│   ├── views.py            ← Lógica (FBV) + endpoints JSON
│   ├── urls.py             ← Rutas de la app
│   ├── admin.py            ← Panel administrativo
│   └── templates/events/   ← HTML + JavaScript
│       ├── base.html
│       ├── login.html
│       ├── register.html
│       ├── index.html
│       ├── event_detail.html
│       └── my_qr.html
├── media/
│   └── qrcodes/            ← Imágenes QR generadas
├── manage.py
└── requirements.txt
```

---

## Modelo de base de datos

| Tabla             | Descripción                                              |
|-------------------|----------------------------------------------------------|
| `auth_user`       | Modelo de usuario de Django (integrado)                  |
| `UserProfile`     | Extiende User con campo `rol` (fighter/promoter/admin)   |
| `Event`           | Evento deportivo (título, fecha, ubicación, estado)       |
| `EventRegistration` | Registro de usuario a evento + QR + check-in           |
| `Comment`         | Comentarios de usuarios sobre eventos                    |
| `EventCreationLog`| Auditoría de creación de eventos (aprobado/rechazado)    |

### ¿Por qué usamos `auth.User` en lugar de un modelo propio?
Django ya incluye un sistema de usuarios robusto con autenticación, sesiones
y panel admin. Crear una tabla `Users` propia duplicaría trabajo innecesariamente.
`UserProfile` (OneToOne con User) añade solo el campo `rol` que necesitamos.

---

## Requisitos previos

- Python 3.10 o superior
- PostgreSQL instalado y corriendo
- Git

---

## Pasos de instalación

### 1. Clonar el repositorio

```bash
git clone <URL_DEL_REPO>
cd fightnet
```

### 2. Crear y activar entorno virtual

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Crear la base de datos en PostgreSQL

Abre tu cliente de PostgreSQL (psql, pgAdmin, etc.) y ejecuta:

```sql
CREATE DATABASE fightnet_db;
```

### 5. Configurar credenciales en settings.py

Abre `fightnet/settings.py` y edita la sección `DATABASES`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'fightnet_db',
        'USER': 'TU_USUARIO',       # ← cambia esto
        'PASSWORD': 'TU_PASSWORD',  # ← cambia esto
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### 6. Aplicar migraciones

```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. Crear superusuario (admin)

```bash
python manage.py createsuperuser
```
Sigue las instrucciones: nombre, email y contraseña.

### 8. Correr el servidor

```bash
# Local (solo tu máquina)
python manage.py runserver

# Red local (para que compañeros de clase accedan desde su equipo)
python manage.py runserver 0.0.0.0:8000
```

### 9. Acceder al sistema

| URL                                  | Descripción              |
|--------------------------------------|--------------------------|
| http://localhost:8000/               | Página principal         |
| http://localhost:8000/login/         | Iniciar sesión           |
| http://localhost:8000/register/      | Registrarse              |
| http://localhost:8000/admin/         | Panel de administración  |

---

## Endpoints de la API JSON

| Método | URL                            | Descripción                         |
|--------|--------------------------------|-------------------------------------|
| GET    | `/api/events/`                 | Lista todos los eventos activos     |
| POST   | `/api/events/`                 | Crea un nuevo evento                |
| GET    | `/api/events/<id>/`            | Detalle de un evento                |
| DELETE | `/api/events/<id>/`            | Elimina un evento                   |
| POST   | `/api/register-event/`         | Registrar usuario a evento          |
| GET    | `/api/event-attendees/<id>/`   | Lista de asistentes de un evento    |
| GET    | `/api/event-comments/<id>/`    | Lista de comentarios de un evento   |
| POST   | `/api/event-comments/<id>/`    | Agregar comentario a un evento      |
| POST   | `/api/check-in/`               | Validar QR y hacer check-in         |
| GET    | `/api/me/`                     | Datos del usuario autenticado       |

---

## Funcionalidades implementadas

✅ Registro e inicio de sesión de usuarios  
✅ Roles: fighter (peleador) y promoter (promotor)  
✅ Crear eventos desde la interfaz  
✅ Listar eventos con estado (activo/cancelado/finalizado)  
✅ Registrarse a un evento  
✅ Ver lista de asistentes por evento  
✅ Generación automática de código QR al registrarse  
✅ Check-in por código QR  
✅ Comentarios por evento  
✅ Panel de administración Django (con filtros y búsqueda)  
✅ API JSON con FBV (sin Django REST Framework)  

---

## Tecnologías utilizadas

| Capa       | Tecnología                        |
|------------|-----------------------------------|
| Backend    | Django 4.2 (Python)               |
| Base de datos | PostgreSQL                     |
| Frontend   | HTML + CSS + JavaScript Vanilla   |
| Comunicación | `fetch()` (sin frameworks)      |
| QR         | librería `qrcode` + `Pillow`      |
| Admin      | Django Admin                      |

---

## Decisiones de diseño (para el reporte)

1. **Un solo proyecto Django con una app** (`events`): Más simple que multi-app.
   El profesor puede ver toda la lógica en un solo lugar.

2. **`auth.User` en lugar de modelo User propio**: Django ya maneja autenticación,
   sesiones y seguridad. Evitamos reinventar la rueda.

3. **Sin Django REST Framework**: Los endpoints usan `JsonResponse` directamente,
   que es suficiente para el proyecto y más simple de entender.

4. **QR en `EventRegistration`**: El PDF propone una tabla separada `EventCheckIn`,
   pero para este proyecto académico es innecesario. El QR vive en el registro.

5. **FBV (Function-Based Views)**: Más claras para un proyecto académico que las
   Class-Based Views.

6. **Frontend en templates de Django**: Más sencillo que separar completamente
   frontend y backend, pero usando `fetch()` como pide el profesor.

---

## Créditos

Proyecto académico – Fight.net  
Tecnologías: Django 4.2 · PostgreSQL · JavaScript Vanilla · qrcode
