from odoo import models, fields

# El número de pedido de MercadoLibre ya existe como campo de Studio:
#   x_studio_nmero_de_venta_ml  (sale.order)
# El módulo lo lee/escribe directamente, no define uno propio.


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    ml_pack_id = fields.Char(string='ML Pack ID', copy=False)
    ml_buyer_id = fields.Char(string='ML Buyer ID', copy=False)
    ml_account_id = fields.Many2one('ml.account', string='Cuenta ML', copy=False)
    ml_message_sent = fields.Boolean(string='Mensaje ML enviado', copy=False, default=False)
