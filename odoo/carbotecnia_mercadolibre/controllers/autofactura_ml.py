import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class AutofacturaML(http.Controller):
    """Página pública donde el cliente de MercadoLibre ingresa su número de
    pedido para autofacturar. Reutiliza los templates del módulo
    carbotecnia_autofactura para el formulario fiscal."""

    def _order_entregado(self, order):
        """True si todas las entregas salientes del pedido están completadas."""
        salidas = order.picking_ids.filtered(
            lambda p: p.picking_type_code == 'outgoing')
        if not salidas:
            return False
        return all(p.state in ('done', 'cancel') for p in salidas) and \
            any(p.state == 'done' for p in salidas)

    # ------------------------------------------------------------------
    # GET — página para ingresar el número de pedido ML
    # ------------------------------------------------------------------
    @http.route('/autofactura', type='http', auth='public', website=True, sitemap=True)
    def autofactura_inicio(self, **kwargs):
        return request.render('carbotecnia_mercadolibre.autofactura_buscar', {
            'error': kwargs.get('error', ''),
            'ml_number': kwargs.get('ml_number', ''),
        })

    # ------------------------------------------------------------------
    # POST — buscar el pedido por número ML
    # ------------------------------------------------------------------
    @http.route('/autofactura/buscar', type='http', auth='public',
                website=True, methods=['POST'])
    def autofactura_buscar(self, **kwargs):
        ml_number = (kwargs.get('ml_number') or '').strip()

        if not ml_number:
            return request.render('carbotecnia_mercadolibre.autofactura_buscar', {
                'error': 'Ingresa tu número de pedido de MercadoLibre.',
                'ml_number': ml_number,
            })

        order = request.env['sale.order'].sudo().search(
            [('x_studio_nmero_de_venta_ml', '=', ml_number)], limit=1)

        if not order:
            return request.render('carbotecnia_mercadolibre.autofactura_buscar', {
                'error': 'No encontramos ese número de pedido. Verifica que sea el '
                         'número que te dio MercadoLibre. Si tu compra es muy reciente, '
                         'espera unos minutos e intenta de nuevo.',
                'ml_number': ml_number,
            })

        # ¿Ya facturado?
        facturas = order.invoice_ids.filtered(
            lambda i: i.state == 'posted' and i.move_type == 'out_invoice')
        if facturas:
            return request.render('carbotecnia_autofactura.ya_facturado', {
                'order': order,
                'facturas': facturas,
            })

        # ¿Ya se surtió? (requisito: facturar después del surtido)
        if not self._order_entregado(order):
            return request.render('carbotecnia_mercadolibre.autofactura_no_surtido', {
                'order': order,
            })

        # Renderizar el formulario fiscal del módulo autofactura
        partner = order.partner_invoice_id or order.partner_id
        from odoo.addons.carbotecnia_autofactura.controllers.portal import (
            USOS_CFDI, REGIMENES_FISCALES, FORMAS_PAGO,
        )
        return request.render('carbotecnia_autofactura.autofactura_form', {
            'order': order,
            'partner': partner,
            'access_token': order.access_token,
            'cfdi_values': {
                'rfc': partner.vat or '',
                'uso_cfdi': partner.l10n_mx_edi_usage or 'G03',
                'regimen_fiscal': partner.l10n_mx_edi_fiscal_regime or '601',
            },
            'usos_cfdi': USOS_CFDI,
            'regimenes_fiscales': REGIMENES_FISCALES,
            'formas_pago': FORMAS_PAGO,
            'error': '',
        })
