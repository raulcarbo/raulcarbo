import logging
import requests
import hashlib
import base64
import secrets
from datetime import datetime, timedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

ML_API = 'https://api.mercadolibre.com'
ML_AUTH = 'https://auth.mercadolibre.com.mx/authorization'
ML_TOKEN = 'https://api.mercadolibre.com/oauth/token'
TIMEOUT = 30


class MlAccount(models.Model):
    _name = 'ml.account'
    _description = 'Cuenta de MercadoLibre'

    name = fields.Char(string='Nombre', required=True, default='MercadoLibre Carbotecnia')
    active = fields.Boolean(default=True)

    # --- Credenciales de la aplicación ML ---
    client_id = fields.Char(string='App ID (Client ID)', required=True)
    client_secret = fields.Char(string='Secret Key', required=True)
    redirect_uri = fields.Char(
        string='Redirect URI',
        compute='_compute_redirect_uri',
        help='Configura esta URL en tu aplicación de MercadoLibre Developers.',
    )

    # --- Tokens OAuth ---
    seller_id = fields.Char(string='Seller ID (User ID de ML)', readonly=True)
    access_token = fields.Char(string='Access Token', readonly=True, groups='base.group_system')
    refresh_token = fields.Char(string='Refresh Token', readonly=True, groups='base.group_system')
    token_expiration = fields.Datetime(string='Expira el', readonly=True)
    connected = fields.Boolean(string='Conectado', compute='_compute_connected')
    pkce_code_verifier = fields.Char(
        string='PKCE code_verifier', readonly=True, groups='base.group_system',
        help='Temporal: se genera al conectar y se usa una sola vez en el callback.',
    )

    # --- Configuración de sincronización ---
    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Almacén MercadoLibre', required=True,
        help='Almacén desde donde se surten los pedidos de ML.',
    )
    team_id = fields.Many2one('crm.team', string='Equipo de ventas')
    salesperson_id = fields.Many2one(
        'res.users', string='Vendedor a notificar',
        help='Usuario que recibe la notificación cuando entra un pedido de ML.',
    )
    pricelist_id = fields.Many2one('product.pricelist', string='Tarifa')
    fiscal_position_id = fields.Many2one(
        'account.fiscal.position', string='Posición fiscal',
        help='Ej. la posición fiscal de Público en General / ML.',
    )
    default_partner_id = fields.Many2one(
        'res.partner', string='Cliente genérico ML',
        help='Cliente usado en los pedidos de ML hasta que el comprador se autofactura.',
    )
    auto_confirm = fields.Boolean(
        string='Confirmar pedido automáticamente', default=True,
        help='Si está activo, el pedido de ML se confirma (sale order) al crearse.',
    )
    send_ml_message = fields.Boolean(
        string='Enviar mensaje de autofacturación en ML', default=True,
    )
    ml_message_template = fields.Text(
        string='Plantilla de mensaje ML',
        default=(
            'Hola, gracias por tu compra. Para generar tu factura CFDI ingresa a '
            'https://carbotecnia.odoo.com/autofactura e ingresa tu número de pedido '
            'de MercadoLibre: {ml_order_number}. Tendrás disponible tu factura una vez '
            'enviado tu producto. Cualquier duda: ventas@carbotecnia.com.mx'
        ),
    )

    _sql_constraints = [
        ('unique_active', 'unique(active)', 'Solo puede haber una cuenta ML activa.'),
    ]

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    def _compute_redirect_uri(self):
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for rec in self:
            rec.redirect_uri = f'{base}/mercadolibre/oauth/callback'

    def _compute_connected(self):
        for rec in self:
            rec.connected = bool(rec.refresh_token)

    # ------------------------------------------------------------------
    # OAuth
    # ------------------------------------------------------------------
    @staticmethod
    def _generate_pkce_pair():
        """Genera (code_verifier, code_challenge) para PKCE con método S256."""
        verifier = secrets.token_urlsafe(64)  # 43-128 chars, URL-safe
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode('ascii')).digest()
        ).decode('ascii').rstrip('=')  # base64url sin padding
        return verifier, challenge

    def action_connect(self):
        """Redirige al usuario a la pantalla de autorización de ML (con PKCE)."""
        self.ensure_one()
        verifier, challenge = self._generate_pkce_pair()
        # Guardamos el verifier para usarlo en el callback
        self.sudo().write({'pkce_code_verifier': verifier})
        auth_url = (
            f'{ML_AUTH}?response_type=code'
            f'&client_id={self.client_id}'
            f'&redirect_uri={self.redirect_uri}'
            f'&state={self.id}'
            f'&code_challenge={challenge}'
            f'&code_challenge_method=S256'
        )
        return {
            'type': 'ir.actions.act_url',
            'url': auth_url,
            'target': 'self',
        }

    def _token_request(self, data):
        """POST al endpoint de token de ML. Devuelve el JSON o lanza un
        UserError con el mensaje exacto de MercadoLibre si falla."""
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        resp = requests.post(ML_TOKEN, data=data, headers=headers, timeout=TIMEOUT)
        if resp.status_code >= 400:
            # ML devuelve {"error": "...", "message": "...", "error_description": "..."}
            try:
                body = resp.json()
                detalle = body.get('message') or body.get('error_description') \
                    or body.get('error') or resp.text
            except Exception:
                detalle = resp.text
            _logger.error('ML token error %s: %s', resp.status_code, resp.text)
            raise UserError(_(
                'MercadoLibre rechazó la conexión (HTTP %(code)s):\n%(detalle)s'
            ) % {'code': resp.status_code, 'detalle': detalle})
        return resp.json()

    def _exchange_code_for_token(self, code):
        """Intercambia el authorization code por tokens (llamado desde el callback)."""
        self.ensure_one()
        data = {
            'grant_type': 'authorization_code',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'redirect_uri': self.redirect_uri,
        }
        # PKCE: incluir el code_verifier generado al conectar
        if self.pkce_code_verifier:
            data['code_verifier'] = self.pkce_code_verifier
        payload = self._token_request(data)
        self.sudo().write({
            'access_token': payload['access_token'],
            'refresh_token': payload['refresh_token'],
            'seller_id': str(payload['user_id']),
            'token_expiration': datetime.now() + timedelta(seconds=payload['expires_in'] - 120),
            'pkce_code_verifier': False,  # usado una sola vez
        })
        _logger.info('ML: tokens obtenidos para seller %s', payload['user_id'])

    def _refresh_access_token(self):
        """Refresca el access token usando el refresh token."""
        self.ensure_one()
        if not self.refresh_token:
            raise UserError(_('La cuenta ML no está conectada.'))
        payload = self._token_request({
            'grant_type': 'refresh_token',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': self.refresh_token,
        })
        self.sudo().write({
            'access_token': payload['access_token'],
            'refresh_token': payload['refresh_token'],
            'token_expiration': datetime.now() + timedelta(seconds=payload['expires_in'] - 120),
        })
        _logger.info('ML: access token refrescado para seller %s', self.seller_id)

    def _get_valid_token(self):
        """Devuelve un access token válido, refrescando si expiró."""
        self.ensure_one()
        if not self.token_expiration or self.token_expiration <= datetime.now():
            self._refresh_access_token()
        return self.access_token

    @api.model
    def _cron_refresh_tokens(self):
        """Cron cada 5 horas: refresca tokens antes de que expiren (ML expira a las 6h)."""
        for account in self.search([('refresh_token', '!=', False)]):
            try:
                account._refresh_access_token()
            except Exception as e:
                _logger.error('ML: fallo al refrescar token de %s: %s', account.name, str(e))

    # ------------------------------------------------------------------
    # Cliente API
    # ------------------------------------------------------------------
    def _api_get(self, path, params=None):
        self.ensure_one()
        token = self._get_valid_token()
        headers = {'Authorization': f'Bearer {token}'}
        resp = requests.get(f'{ML_API}{path}', headers=headers, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json()

    def _api_post(self, path, json_body):
        self.ensure_one()
        token = self._get_valid_token()
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }
        resp = requests.post(f'{ML_API}{path}', headers=headers, json=json_body, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json() if resp.content else {}

    # ------------------------------------------------------------------
    # Sincronización de pedidos
    # ------------------------------------------------------------------
    def sync_order(self, ml_order_id):
        """Trae un pedido de ML y lo crea/actualiza en Odoo."""
        self.ensure_one()
        SaleOrder = self.env['sale.order'].sudo()

        # ¿Ya existe?
        existing = SaleOrder.search(
            [('x_studio_nmero_de_venta_ml', '=', str(ml_order_id))], limit=1)
        if existing:
            _logger.info('ML: pedido %s ya existe en Odoo (%s)', ml_order_id, existing.name)
            return existing

        ml_order = self._api_get(f'/orders/{ml_order_id}')
        order = self._create_sale_order(ml_order)
        return order

    def _find_or_create_partner(self, ml_order):
        """Usa el cliente genérico ML (el comprador captura sus datos al autofacturar)."""
        self.ensure_one()
        if self.default_partner_id:
            return self.default_partner_id
        # Fallback: crear/buscar un partner "MercadoLibre"
        partner = self.env['res.partner'].sudo().search(
            [('name', '=', 'Cliente MercadoLibre')], limit=1)
        if not partner:
            partner = self.env['res.partner'].sudo().create({
                'name': 'Cliente MercadoLibre',
                'company_type': 'person',
            })
        return partner

    def _match_product(self, sku, title):
        """Match por Referencia interna (default_code). Devuelve product.product o False."""
        if not sku:
            return False
        product = self.env['product.product'].sudo().search(
            [('default_code', '=', sku)], limit=1)
        return product or False

    def _create_sale_order(self, ml_order):
        """Crea el sale.order en Odoo a partir del JSON de la orden de ML."""
        self.ensure_one()
        SaleOrder = self.env['sale.order'].sudo()

        ml_order_id = str(ml_order['id'])
        partner = self._find_or_create_partner(ml_order)

        order_lines = []
        unmatched = []
        for item in ml_order.get('order_items', []):
            item_data = item.get('item', {})
            sku = item_data.get('seller_sku') or item_data.get('seller_custom_field')
            title = item_data.get('title', '')
            qty = item.get('quantity', 1)
            price = item.get('unit_price', 0.0)

            product = self._match_product(sku, title)
            if not product:
                unmatched.append(f'{title} (SKU: {sku or "sin SKU"})')
                continue

            order_lines.append((0, 0, {
                'product_id': product.id,
                'product_uom_qty': qty,
                'price_unit': price,
                'name': title or product.name,
            }))

        vals = {
            'partner_id': partner.id,
            'warehouse_id': self.warehouse_id.id,
            'x_studio_nmero_de_venta_ml': ml_order_id,
            'ml_account_id': self.id,
            'origin': f'MercadoLibre {ml_order_id}',
            'order_line': order_lines,
        }
        if self.team_id:
            vals['team_id'] = self.team_id.id
        if self.salesperson_id:
            vals['user_id'] = self.salesperson_id.id
        if self.pricelist_id:
            vals['pricelist_id'] = self.pricelist_id.id
        if self.fiscal_position_id:
            vals['fiscal_position_id'] = self.fiscal_position_id.id

        order = SaleOrder.create(vals)

        # Guardar datos del comprador ML para referencia del vendedor
        buyer = ml_order.get('buyer', {})
        buyer_note = _(
            'Pedido MercadoLibre #%(ml)s\n'
            'Comprador ML: %(nick)s\n'
            'Total ML: %(total)s %(cur)s'
        ) % {
            'ml': ml_order_id,
            'nick': buyer.get('nickname', 'N/D'),
            'total': ml_order.get('total_amount', 0),
            'cur': ml_order.get('currency_id', 'MXN'),
        }
        order.message_post(body=buyer_note.replace('\n', '<br/>'))

        # Alertar productos no encontrados
        if unmatched:
            order.message_post(body=_(
                '<b>⚠️ Productos sin match por SKU (no agregados):</b><br/>%s'
            ) % '<br/>'.join(unmatched))

        # Confirmar automáticamente
        if self.auto_confirm and order.order_line:
            try:
                order.action_confirm()
            except Exception as e:
                _logger.error('ML: no se pudo confirmar pedido %s: %s', order.name, str(e))
                order.message_post(body=_('No se pudo confirmar automáticamente: %s') % str(e))

        # Notificar al vendedor
        self._notify_salesperson(order, unmatched)

        _logger.info('ML: pedido %s creado en Odoo como %s', ml_order_id, order.name)
        return order

    def _notify_salesperson(self, order, unmatched):
        """Crea una actividad para el vendedor."""
        user = self.salesperson_id or order.user_id
        if not user:
            return
        summary = _('Nuevo pedido MercadoLibre %s') % order.x_studio_nmero_de_venta_ml
        note = _('Se creó el pedido %s desde MercadoLibre.') % order.name
        if unmatched:
            summary = _('⚠️ Pedido ML %s requiere revisión') % order.x_studio_nmero_de_venta_ml
            note += _(' Hay productos sin match por SKU — revisa antes de surtir.')
        order.activity_schedule(
            'mail.mail_activity_data_todo',
            user_id=user.id,
            summary=summary,
            note=note,
        )

    # ------------------------------------------------------------------
    # Mensajería ML — instrucciones de autofacturación
    # ------------------------------------------------------------------
    def send_autofactura_message(self, order):
        """Envía mensaje al comprador en ML con las instrucciones de autofacturación."""
        self.ensure_one()
        if not self.send_ml_message:
            return
        if not order.ml_pack_id and not order.x_studio_nmero_de_venta_ml:
            return
        try:
            text = self.ml_message_template.format(
                ml_order_number=order.x_studio_nmero_de_venta_ml or '',
            )
            pack_id = order.ml_pack_id or order.x_studio_nmero_de_venta_ml
            body = {
                'from': {'user_id': self.seller_id},
                'to': {'user_id': order.ml_buyer_id or ''},
                'text': text,
            }
            self._api_post(
                f'/messages/packs/{pack_id}/sellers/{self.seller_id}', body)
            order.ml_message_sent = True
            order.message_post(body=_('✅ Mensaje de autofacturación enviado al comprador en ML.'))
            _logger.info('ML: mensaje autofactura enviado para pedido %s', order.x_studio_nmero_de_venta_ml)
        except Exception as e:
            _logger.error('ML: fallo al enviar mensaje pedido %s: %s',
                          order.x_studio_nmero_de_venta_ml, str(e))
            order.message_post(body=_('⚠️ No se pudo enviar el mensaje de ML: %s') % str(e))
