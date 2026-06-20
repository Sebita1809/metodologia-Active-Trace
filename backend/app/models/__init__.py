# app/models/__init__.py
# Import all models here so Alembic autogenerate can discover them via Base.metadata.
# Add new models as they are created in successive changes.

from app.models.tenant import Tenant  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.rol import Rol  # noqa: F401
from app.models.permiso import Permiso  # noqa: F401
from app.models.rol_permiso import RolPermiso  # noqa: F401
from app.models.usuario_rol import UsuarioRol  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.carrera import Carrera  # noqa: F401
from app.models.cohorte import Cohorte  # noqa: F401
from app.models.materia import Materia  # noqa: F401
from app.models.usuario import Usuario  # noqa: F401
from app.models.asignacion import Asignacion  # noqa: F401
from app.models.version_padron import VersionPadron  # noqa: F401
from app.models.entrada_padron import EntradaPadron  # noqa: F401
from app.models.umbral_materia import UmbralMateria  # noqa: F401
from app.models.calificacion import Calificacion  # noqa: F401
from app.models.slot_encuentro import SlotEncuentro  # noqa: F401
from app.models.instancia_encuentro import InstanciaEncuentro  # noqa: F401
from app.models.guardia import Guardia  # noqa: F401
from app.models.aviso import Aviso  # noqa: F401
from app.models.acknowledgment_aviso import AcknowledgmentAviso  # noqa: F401
from app.models.tarea import Tarea  # noqa: F401
from app.models.comentario_tarea import ComentarioTarea  # noqa: F401
from app.models.programa_materia import ProgramaMateria  # noqa: F401
from app.models.fecha_academica import FechaAcademica  # noqa: F401
from app.models.salario_base import SalarioBase  # noqa: F401
from app.models.salario_plus import SalarioPlus  # noqa: F401
from app.models.liquidacion import Liquidacion  # noqa: F401
from app.models.factura import Factura  # noqa: F401
from app.models.mensaje import Mensaje  # noqa: F401
