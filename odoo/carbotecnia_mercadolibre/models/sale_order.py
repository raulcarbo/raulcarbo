from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    ml_order_number = fields.Char(
        string='N° pedido MercadoLibre',
        index=True, copy=False,
        help='Número de pedido que MercadoLibre da al cliente. '
             'Es el identificador que usa el cliente para autofacturar.',
    )
    ml_pack_id = fields.Char(string='ML Pack ID', copy=False)
    ml_buyer_id = fields.Char(string='ML Buyer ID', copy=False)
    ml_account_id = fields.Many2one('ml.account', string='Cuenta ML', copy=False)
    ml_message_sent = fields.Boolean(string='Mensaje ML enviado', copy=False, default=False)

    _sql_constraints = [
        ('ml_order_number_uniq', 'unique(ml_order_number)',
         'Ya existe un pedido con este número de MercadoLibre.'),
    ]
