# MercadoLibre → Odoo — Carbotecnia

Sincroniza pedidos de MercadoLibre a Odoo 18 y dispara la autofacturación CFDI.

## Flujo

```
Cliente compra en ML
   → ML manda webhook a Odoo (/mercadolibre/notifications)
   → Odoo trae el pedido por API y crea el sale.order
        · match de producto por SKU = Referencia interna (default_code)
        · cantidad y precio de ML
        · almacén "MercadoLibre"
        · número de pedido ML guardado en el pedido
   → Se confirma el pedido (opcional) y se notifica al vendedor (actividad)
   → Almacén surte y valida la entrega (picking → done)
   → Se envía mensaje al comprador en ML con instrucciones de autofacturación
   → Cliente entra a carbotecnia.odoo.com/autofactura, escribe su N° de pedido ML
   → Genera su CFDI (solo disponible después del surtido)
```

## Instalación en Odoo.sh

1. Sube este módulo y `carbotecnia_autofactura` al repo conectado a Odoo.sh.
2. En Odoo: Ajustes → Técnico → Actualizar lista de módulos.
3. Instala **MercadoLibre → Odoo — Carbotecnia** (instala el autofacturador como dependencia).
4. Requisitos previos instalados: `l10n_mx_edi`, `l10n_mx_edi_40`, PAC configurado con CSD activo.

## Configuración de la App en MercadoLibre

1. Entra a https://developers.mercadolibre.com.mx → Crea una aplicación.
2. En **Redirect URI** pon exactamente la que muestra Odoo en la cuenta ML:
   `https://carbotecnia.odoo.com/mercadolibre/oauth/callback`
3. Permisos (scopes): `read`, `write`, `offline_access`.
4. En **Notificaciones (webhooks)**, URL de callback:
   `https://carbotecnia.odoo.com/mercadolibre/notifications`
   Suscríbete al topic **orders_v2**.
5. Copia el **App ID** y **Secret Key**.

## Configuración en Odoo

1. Menú **MercadoLibre → Cuentas → Crear**.
2. Pega App ID y Secret Key.
3. Configura:
   - **Almacén MercadoLibre** (créalo antes en Inventario si no existe).
   - **Cliente genérico ML** (un `res.partner`, ej. "Cliente MercadoLibre").
   - **Vendedor a notificar**, equipo, tarifa y posición fiscal (ML / Público en general).
   - **Confirmar pedido automáticamente** (recomendado ON).
   - **Enviar mensaje de autofacturación en ML** (ON).
4. Botón **Conectar con MercadoLibre** → autoriza → vuelve conectado.

## Notas técnicas

- **Match de producto:** el SKU de la publicación de ML (`seller_sku`) debe coincidir con la
  Referencia interna del producto en Odoo. Si no hay match, el pedido se crea sin esa línea
  y el vendedor recibe una alerta en la actividad y en el chatter.
- **Campo de número de pedido:** este módulo agrega `ml_order_number`. Si ya tenías un campo
  propio para el número de ML, avísame para mapear la sincronización a ese campo en vez de crear uno nuevo.
- **Tokens:** ML expira el access token cada 6 horas; un cron lo refresca cada 5 horas.
- **Mensajería ML:** el endpoint de mensajes post-venta de ML tiene restricciones y plantillas
  según categoría. Si ML rechaza el envío, queda registrado en el chatter del pedido para envío manual.
- **Facturar después del surtido:** el CFDI solo se habilita cuando todas las entregas salientes
  del pedido están validadas (`done`).
