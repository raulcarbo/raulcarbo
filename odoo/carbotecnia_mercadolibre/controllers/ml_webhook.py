import logging
import json
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class MlWebhook(http.Controller):

    # ------------------------------------------------------------------
    # Callback OAuth — ML redirige aquí con el authorization code
    # ------------------------------------------------------------------
    @http.route('/mercadolibre/oauth/callback', type='http', auth='user', website=False)
    def ml_oauth_callback(self, code=None, state=None, **kwargs):
        if not code:
            return 'Error: no se recibió el código de autorización de MercadoLibre.'
        account = request.env['ml.account'].sudo().browse(int(state)) if state else \
            request.env['ml.account'].sudo().search([], limit=1)
        if not account.exists():
            return 'Error: cuenta ML no encontrada.'
        try:
            account._exchange_code_for_token(code)
        except Exception as e:
            _logger.error('ML OAuth callback error: %s', str(e))
            return f'Error al conectar con MercadoLibre: {str(e)}'
        # Redirigir de vuelta al formulario de la cuenta
        return request.redirect(
            f'/odoo/action-base_setup.action_general_configuration'
            if False else f'/web#id={account.id}&model=ml.account&view_type=form'
        )

    # ------------------------------------------------------------------
    # Webhook de notificaciones de ML
    # ML envía POST con {topic, resource, user_id, ...}
    # ------------------------------------------------------------------
    @http.route('/mercadolibre/notifications', type='http', auth='public',
                csrf=False, methods=['POST'])
    def ml_notifications(self, **kwargs):
        try:
            raw = request.httprequest.get_data()
            data = json.loads(raw) if raw else {}
        except Exception:
            data = {}

        topic = data.get('topic')
        resource = data.get('resource', '')
        _logger.info('ML webhook: topic=%s resource=%s', topic, resource)

        # ML espera respuesta 200 rápida — procesamos y respondemos
        try:
            if topic == 'orders_v2' or topic == 'orders':
                # resource = /orders/{id}
                ml_order_id = resource.rstrip('/').split('/')[-1]
                account = request.env['ml.account'].sudo().search([], limit=1)
                if account and ml_order_id:
                    # Confirmar que la orden está pagada antes de crear
                    request.env.cr.commit()  # aseguramos estado limpio
                    account.sync_order(ml_order_id)
        except Exception as e:
            _logger.error('ML webhook error procesando %s: %s', resource, str(e))
            # Aun así respondemos 200 para que ML no reintente en loop;
            # el error queda en el log para revisión.

        return request.make_response('OK', headers=[('Content-Type', 'text/plain')])
