from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    autofactura_autorizada = fields.Boolean(
        string='Puede autofacturar',
        default=True,
        help='Desactiva para bloquear la autofacturación de este cliente en el portal.',
    )
