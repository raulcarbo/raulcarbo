import logging
from odoo import models

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        """Al validar la entrega de un pedido de ML, dispara el mensaje de autofacturación."""
        res = super().button_validate()
        for picking in self:
            # Solo entregas salientes completadas
            if picking.picking_type_code != 'outgoing' or picking.state != 'done':
                continue
            order = picking.sale_id
            if not order or not order.x_studio_nmero_de_venta_ml or not order.ml_account_id:
                continue
            if order.ml_message_sent:
                continue
            # ¿Todas las entregas del pedido están hechas?
            pendientes = order.picking_ids.filtered(
                lambda p: p.picking_type_code == 'outgoing' and p.state not in ('done', 'cancel')
            )
            if pendientes:
                continue
            try:
                order.ml_account_id.send_autofactura_message(order)
            except Exception as e:
                _logger.error('ML: error al notificar autofactura en %s: %s',
                              order.name, str(e))
        return res
