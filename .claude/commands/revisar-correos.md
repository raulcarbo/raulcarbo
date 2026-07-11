---
description: Revisa la bandeja de Gmail, lee el contexto completo de cada hilo y deja borradores de respuesta para revisión de Raúl. Nunca envía.
---

Lanza el subagente `revisor-correos` (definido en `.claude/agents/revisor-correos.md`) para revisar la bandeja de entrada de Gmail.

Instrucción adicional de Raúl para esta corrida (puede estar vacía): $ARGUMENTS

Si Raúl no dio instrucción adicional, revisa los correos no leídos de los últimos 3 días (`in:inbox is:unread newer_than:3d`). Si dio un filtro (un remitente, un tema, "hoy", "esta semana"), pásalo al subagente traducido a criterios de búsqueda de Gmail.

Al terminar, muestra a Raúl el reporte del subagente tal cual: hilos revisados, borradores creados (con quién y qué pide cada uno), pendientes marcados con `[CONFIRMAR: …]`, y correos escalados que requieren su decisión.

Recuérdale al final: los borradores están en Gmail → Borradores, listos para revisar, editar y enviar personalmente.
