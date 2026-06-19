"""CSV export service for teaching teams."""
import csv
import io

from app.repositories.usuarios.asignacion_repository import AsignacionRepository


class ExportService:
    def __init__(self, repo: AsignacionRepository):
        self.repo = repo

    async def generar_csv_equipo(self, asignaciones: list) -> io.StringIO:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Docente", "Rol", "Carrera", "Cohorte", "Comisiones", "Desde", "Hasta", "Estado"])
        for a in asignaciones:
            writer.writerow([
                str(a.usuario_id),
                a.rol,
                str(a.carrera_id or ""),
                str(a.cohorte_id or ""),
                ", ".join(a.comisiones) if a.comisiones else "",
                a.desde.isoformat(),
                a.hasta.isoformat() if a.hasta else "",
                a.estado_vigencia,
            ])
        output.seek(0)
        return output
