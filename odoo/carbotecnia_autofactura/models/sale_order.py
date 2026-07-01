from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    autofactura_habilitada = fields.Boolean(
        string='Autofacturación habilitada',
        default=True,
        help='Si está activo, el cliente puede generar su factura desde el portal.',
    )
    autofactura_url = fields.Char(
        string='URL de autofacturación',
        compute='_compute_autofactura_url',
        store=False,
    )

    @api.depends('access_token', 'id')
    def _compute_autofactura_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for order in self:
            if order.access_token:
                order.autofactura_url = (
                    f'{base_url}/autofactura/{order.id}/{order.access_token}'
                )
            else:
                order.autofactura_url = ''

    def action_copy_autofactura_url(self):
        """Botón en el pedido para copiar la URL."""
        self.ensure_one()
        if not self.access_token:
            self._portal_ensure_token()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'URL de autofacturación',
                'message': self.autofactura_url,
                'type': 'success',
                'sticky': True,
            },
        }

    def action_send_autofactura_email(self):
        """Envía por correo la URL de autofacturación al cliente."""
        self.ensure_one()
        if not self.access_token:
            self._portal_ensure_token()

        template = self.env.ref(
            'carbotecnia_autofactura.mail_template_autofactura',
            raise_if_not_found=False,
        )
        if template:
            template.send_mail(self.id, force_send=True)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Correo enviado',
                    'message': f'URL de autofacturación enviada a {self.partner_id.email}',
                    'type': 'success',
                },
            }
