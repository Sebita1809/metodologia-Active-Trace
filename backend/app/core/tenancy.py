"""
core/tenancy.py — RESERVADO para C-02.

Este módulo implementará:
  - Resolución del tenant_id del request actual (desde JWT verificado)
  - Aislamiento row-level: todos los queries deben filtrar por tenant_id
  - Helpers para validar que el contexto tiene tenant antes de acceder a datos

Regla dura: NUNCA tomar tenant_id de URL, body o headers —
            siempre desde la sesión JWT verificada.
NO contiene lógica hasta que C-02 sea implementado.
"""
# Implementar en C-02 (core-models-y-tenancy).
