# activia-trace

Plataforma de gestión académica y trazabilidad multi-tenant para instituciones educativas. Actúa como capa de orquestación sobre Moodle: consolida calificaciones, detecta atrasos, gestiona comunicación saliente con aprobación, equipos docentes, encuentros, coloquios, liquidaciones de honorarios y auditoría completa.

## Stack

| Componente | Tecnología |
|------------|-----------|
| **Backend** | Python 3.13 + FastAPI (async) |
| **ORM** | SQLAlchemy 2.0 (async) |
| **Base de datos** | PostgreSQL 16 |
| **Migraciones** | Alembic |
| **Frontend** | React 19 + TypeScript 6 + Vite |
| **Estilos** | Tailwind CSS v4 |
| **Server state** | TanStack Query |
| **Forms** | React Hook Form + Zod |
| **HTTP Client** | Axios (JWT refresh interceptor) |
| **Auth** | JWT (access 15min + refresh rotation) + Argon2id + 2FA TOTP |
| **Contenedores** | Docker + docker-compose |

> Stack completo en [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md). Dominio documentado en [`knowledge-base/`](knowledge-base/).

## Requisitos

- **Docker** + docker-compose (para el stack completo)
- **Python 3.13+** (para desarrollo local del backend)
- **pnpm** (para desarrollo local del frontend)
- **PostgreSQL 16** (para desarrollo local sin Docker)

## Setup rápido (Docker)

```bash
# 1. Clonar el repo
git clone https://github.com/Sebita1809/metodologia-Active-Trace.git
cd metodologia-Active-Trace

# 2. Configurar variables de entorno del backend
cp backend/.env.example backend/.env
# Editar backend/.env con valores reales

# 3. Configurar variables de entorno del frontend
cp frontend/.env.example frontend/.env

# 4. Levantar todo con Docker
docker compose up -d

# 5. Correr migraciones
docker compose exec api alembic upgrade head

# 6. Sembrar datos de desarrollo (opcional)
docker compose exec api python seed_dev.py
```

La API estará en `http://localhost:8000` y el frontend en `http://localhost:5173`.

## Setup desarrollo local

### Backend

```bash
cd backend

# Crear entorno virtual
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Instalar dependencias
pip install -e ".[dev]"

# Configurar variables de entorno
cp .env.example .env
# Editar DATABASE_URL en .env para apuntar a tu PostgreSQL local

# Correr migraciones
alembic upgrade head

# Iniciar servidor de desarrollo
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend

# Instalar dependencias (usar pnpm, no npm)
pnpm install

# Configurar variables de entorno
cp .env.example .env

# Iniciar servidor de desarrollo
pnpm dev
```

## Variables de entorno

### Backend (`backend/.env`)

| Variable | Descripción | Default |
|----------|-------------|---------|
| `DATABASE_URL` | URL de conexión a PostgreSQL | `postgresql+asyncpg://...` |
| `SECRET_KEY` | Clave secreta para JWT (mín 32 caracteres) | — |
| `ENCRYPTION_KEY` | Clave AES-256 para cifrado de PII (exactamente 32 caracteres) | — |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Expiración del access token en minutos | `15` |
| `TEST_DATABASE_URL` | URL de la base de datos de tests | — |
| `APP_ENV` | Entorno (`development`, `staging`, `production`) | `development` |
| `LOG_LEVEL` | Nivel de log (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `INFO` |
| `OTEL_ENABLED` | Habilitar OpenTelemetry | `false` |

### Frontend (`frontend/.env`)

| Variable | Descripción | Default |
|----------|-------------|---------|
| `VITE_API_BASE_URL` | URL base de la API backend | `http://localhost:8000` |

## Scripts útiles

### Backend

| Comando | Descripción |
|---------|-------------|
| `alembic upgrade head` | Aplicar migraciones pendientes |
| `alembic revision --autogenerate -m "descripcion"` | Crear nueva migración |
| `pytest` | Ejecutar tests |
| `pytest --cov=app --cov-report=term-missing` | Tests con cobertura |
| `python seed_dev.py` | Sembrar datos de desarrollo |

### Frontend

| Comando | Descripción |
|---------|-------------|
| `pnpm dev` | Iniciar servidor de desarrollo con HMR |
| `pnpm build` | Type-check + build de producción |
| `pnpm test:run` | Ejecutar tests una vez |
| `pnpm coverage` | Tests con reporte de cobertura |

## Estructura del proyecto

```
├── backend/               # API REST FastAPI
│   ├── app/
│   │   ├── api/           # Routers
│   │   ├── core/          # Configuración, seguridad, dependencias
│   │   ├── features/      # Lógica de negocio por módulo
│   │   ├── integrations/  # Integraciones externas (Moodle WS, N8N)
│   │   ├── models/        # Modelos SQLAlchemy
│   │   ├── repositories/  # Acceso a datos con scope de tenant
│   │   ├── schemas/       # Schemas Pydantic v2
│   │   ├── services/      # Servicios de dominio
│   │   └── workers/       # Workers asíncronos
│   ├── alembic/           # Migraciones de base de datos
│   └── tests/             # Tests (pytest)
├── frontend/              # SPA React + TypeScript
│   └── src/
│       ├── features/      # Módulos feature-based
│       └── shared/        # Componentes compartidos, hooks, servicios
├── docs/                  # Documentación técnica
├── knowledge-base/        # Base de conocimiento del dominio
└── openspec/              # Cambios (OpenSpec)
    └── changes/
        └── archive/       # Cambios archivados
```

## Roadmap de implementación

Todos los **24 changes** (C-01 a C-24) están completados. Ver [`CHANGES.md`](CHANGES.md) para el detalle de cada fase.

Fases:

| Fase | Changes | Estado |
|------|---------|--------|
| **FASE 0** — Cimiento e Infraestructura | C-01 | ✅ Completado |
| **FASE 1** — Seguridad y Modelos Core | C-02 → C-05 | ✅ Completado |
| **FASE 2** — Entidades Raíz Académicas | C-06 | ✅ Completado |
| **FASE 3** — Identidad, Asignaciones y Estructura Documental | C-07, C-17 | ✅ Completado |
| **FASE 4** — Módulos de Dominio | C-08 → C-20 | ✅ Completado |
| **FASE 5** — Frontend | C-21 → C-24 | ✅ Completado |

## Licencia

Proyecto académico — UTN Facultad Regional Buenos Aires.
