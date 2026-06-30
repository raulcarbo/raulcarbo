# Agentes Especializados — Carbotecnia

Colección de agentes especializados importados y adaptados de [agency-agents](https://github.com/msitarzewski/agency-agents) (MIT License). Seleccionados por relevancia directa para las prioridades de Carbotecnia: ventas B2B industrial, margen, marketing técnico y finanzas.

## Directorio

### `/sales` — Ventas B2B

| Agente | Para qué sirve en Carbotecnia |
|--------|-------------------------------|
| `sales-outbound-strategist.md` | Prospección basada en señales: quién abrir, cuándo y con qué mensaje. Aplica para reactivar cuentas industriales y abrir distribuidores. |
| `sales-discovery-coach.md` | Mejorar la calidad de discovery: hacer las preguntas correctas para identificar dolor real, presupuesto y urgencia antes de cotizar. |
| `sales-deal-strategist.md` | Calificación MEDDPICC para cotizaciones complejas. Identifica qué deals tienen tracción real vs. cuáles son ruido. |
| `sales-pipeline-analyst.md` | Diagnóstico de pipeline: velocidad, cobertura, deals estancados, forecast con confianza real (no stage-weighted). |
| `sales-proposal-strategist.md` | Construir cotizaciones técnicas como propuestas con narrativa ganadora, no solo listas de precios. |
| `sales-account-strategist.md` | Expansión en cuentas existentes: QBRs, upsell por señales de uso, multi-threading para no depender de un solo contacto. |
| `sales-coach.md` | Coaching de vendedores: pipeline reviews, call coaching, forecast discipline. |
| `sales-offer-lead-gen-strategist.md` | Rediseñar la oferta y los lead magnets (calculadoras, guías técnicas) para calificar leads antes de que lleguen al equipo. |

### `/marketing` — Marketing B2B Industrial

| Agente | Para qué sirve en Carbotecnia |
|--------|-------------------------------|
| `marketing-seo-specialist.md` | Recuperar posicionamiento técnico: clusters por aplicación, audit de canibalización, Core Web Vitals. |
| `marketing-email-strategist.md` | Secuencias automatizadas de nurture para leads industriales: segmentación por industria/aplicación, reactivación de leads fríos. |
| `marketing-content-creator.md` | Crear contenido técnico que genera demanda calificada: casos de uso, comparativas, fichas técnicas, guías por aplicación. |
| `marketing-growth-hacker.md` | Experimentación en canales: qué canal dominar primero, cómo medir CAC real, cómo escalar lo que funciona. |

### `/finance` — Finanzas y Planeación

| Agente | Para qué sirve en Carbotecnia |
|--------|-------------------------------|
| `finance-fpa-analyst.md` | Planeación operativa anual, forecast rolling, análisis de varianza, unit economics por línea de producto. |
| `finance-financial-analyst.md` | Modelos financieros para decisiones de inversión, pricing, expansión de línea. Escenarios base/upside/downside. |

### `/strategy` — Orquestación

| Agente | Para qué sirve en Carbotecnia |
|--------|-------------------------------|
| `strategy/nexus-strategy.md` | Framework para coordinar múltiples agentes en proyectos complejos (lanzamiento de producto, nuevo segmento, sistema de cotización). |

---

## Cómo usar estos agentes

Cada archivo `.md` es un prompt de sistema listo para usar en Claude. Para activar un agente:

1. Abre una conversación nueva con Claude
2. Pega el contenido del archivo como contexto inicial o usa el campo "system prompt"
3. Empieza con tu caso específico: un deal, un análisis, una cotización, un diagnóstico de pipeline

### Ejemplo de activación rápida

**Para analizar un deal específico con Deal Strategist:**
> "Actúa como el Deal Strategist de este repo. Tenemos una cotización para [cliente], llevan 3 semanas sin responder. Aquí está el contexto: [...]"

**Para diagnosticar el pipeline con Pipeline Analyst:**
> "Actúa como el Pipeline Analyst. Tenemos X cotizaciones abiertas por $Y en total. Aquí están los deals activos: [...]"

---

## Prioridades sugeridas para Carbotecnia

**Alta prioridad — impacto inmediato:**
1. `sales-discovery-coach` → mejorar calidad de las primeras llamadas
2. `sales-deal-strategist` → calificar mejor antes de invertir tiempo en cotización
3. `sales-pipeline-analyst` → diagnóstico del pipeline actual
4. `marketing-seo-specialist` → recuperar posicionamiento orgánico

**Media prioridad — siguiente 90 días:**
5. `sales-outbound-strategist` → reactivación de cuentas y apertura de distribuidores
6. `sales-account-strategist` → expansión en cuentas industriales existentes
7. `finance-fpa-analyst` → forecast y unit economics por línea

**Infraestructura — cuando el equipo esté listo:**
8. `marketing-email-strategist` → nurture automatizado
9. `sales-offer-lead-gen-strategist` → rediseño de calculadoras y lead magnets
10. `strategy/nexus-strategy` → proyectos multi-agente

---

*Fuente: [msitarzewski/agency-agents](https://github.com/msitarzewski/agency-agents) — MIT License*
