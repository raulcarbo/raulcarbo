# Integración Carbo Ads ↔ Meta Ads Manager

Guía de conexión del agente al Ads Manager de Carbotecnia. Dos rutas complementarias.

## Ruta A — Conector MCP oficial de Meta (sin app, ~10 min)

Para trabajar en chats de claude.ai y sesiones con conectores.

1. Entrar a claude.ai → Configuración → **Conectores** → *Añadir conector personalizado*.
2. URL del servidor: `https://mcp.facebook.com/ads`
3. Conectar → autenticar con la cuenta de Meta que tiene acceso al Business Manager de Carbotecnia.
4. Habilitar el conector en cada chat/sesión donde trabaje Carbo Ads.
5. Expone ~29 herramientas: reporting, gestión de campañas, catálogo, diagnóstico de señal.

## Ruta B — App propia en Meta for Developers (Marketing API)

Para que el agente opere vía Graph API con token propio, y como base para CAPI/conversiones offline desde el CRM.

### 1. Prerrequisitos (Business Manager)

- Acceso admin a [business.facebook.com](https://business.facebook.com) de Carbotecnia.
- Anotar el **ID de la cuenta publicitaria**: Configuración del negocio → Cuentas → Cuentas publicitarias → formato `act_XXXXXXXXXX`.

### 2. Crear la app

1. Ir a [developers.facebook.com](https://developers.facebook.com) → *Get Started* → registrarse como desarrollador (con el usuario admin del Business).
2. *My Apps* → **Create App**.
3. Caso de uso: **Other** → Tipo de app: **Business**.
4. Nombre: `Carbotecnia Ads Agent` · correo de contacto · vincular al Business Manager de Carbotecnia.
5. En el dashboard de la app: *Add products* → **Marketing API** → Set up.

La app puede quedarse en **modo desarrollo**: acceso completo a las cuentas publicitarias propias del Business. App Review solo se necesita para gestionar cuentas ajenas.

### 3. Token robusto vía usuario del sistema (recomendado)

En Business Manager → Configuración del negocio → Usuarios → **Usuarios del sistema**:

1. Crear usuario del sistema (rol: empleado basta).
2. *Añadir activos*: la cuenta publicitaria con permiso **Administrar campañas**, y la app creada.
3. *Generar token*: seleccionar la app, expiración **nunca**, permisos: `ads_read`, `ads_management`, `business_management`.
4. Guardar el token en un gestor de contraseñas. Se muestra una sola vez.

Alternativa rápida (token de prueba, caduca): Marketing API → Tools → *Get Access Token* con `ads_read` + `ads_management`.

### 4. Entregar credenciales al agente (seguro)

**No pegar el token en el chat.** En code.claude.com → configuración del entorno → variables de entorno:

- `META_ACCESS_TOKEN` = token del usuario del sistema
- `META_AD_ACCOUNT_ID` = `act_XXXXXXXXXX`

### 5. Prueba de conexión

El agente valida con:

```bash
curl -s "https://graph.facebook.com/v23.0/${META_AD_ACCOUNT_ID}/campaigns?fields=name,status,objective,daily_budget&access_token=${META_ACCESS_TOKEN}"
```

Si responde el listado de campañas, la conexión está viva. Primer trabajo: auditoría init definida en `CLAUDE.md`.

### Rotación y revocación

- Token comprometido → Business Settings → Usuarios del sistema → revocar/regenerar.
- Revisar cada 90 días que los permisos del usuario del sistema sigan siendo los mínimos necesarios.

## Estado

- [ ] Ruta A conectada
- [ ] App creada (Ruta B)
- [ ] Token de usuario del sistema generado
- [ ] Variables de entorno configuradas
- [ ] Prueba de conexión exitosa
- [ ] Auditoría init ejecutada y baseline en `APRENDIZAJES.md`
