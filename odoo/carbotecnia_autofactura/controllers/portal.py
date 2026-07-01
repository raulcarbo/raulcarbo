import logging
from odoo import http, _
from odoo.http import request
from odoo.exceptions import AccessError, ValidationError
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager

_logger = logging.getLogger(__name__)

# Catálogos SAT para CFDI 4.0
USOS_CFDI = [
    ('G01', 'G01 - Adquisición de mercancias'),
    ('G02', 'G02 - Devoluciones, descuentos o bonificaciones'),
    ('G03', 'G03 - Gastos en general'),
    ('I01', 'I01 - Construcciones'),
    ('I02', 'I02 - Mobilario y equipo de oficina por inversiones'),
    ('I03', 'I03 - Equipo de transporte'),
    ('I04', 'I04 - Equipo de computo y accesorios'),
    ('I05', 'I05 - Dados, troqueles, moldes, matrices y herramental'),
    ('I06', 'I06 - Comunicaciones telefónicas'),
    ('I07', 'I07 - Comunicaciones satelitales'),
    ('I08', 'I08 - Otra maquinaria y equipo'),
    ('D01', 'D01 - Honorarios médicos, dentales y gastos hospitalarios'),
    ('D02', 'D02 - Gastos médicos por incapacidad o discapacidad'),
    ('D03', 'D03 - Gastos funerales'),
    ('D04', 'D04 - Donativos'),
    ('D05', 'D05 - Intereses reales efectivamente pagados por créditos hipotecarios (casa habitación)'),
    ('D06', 'D06 - Aportaciones voluntarias al SAR'),
    ('D07', 'D07 - Primas por seguros de gastos médicos'),
    ('D08', 'D08 - Gastos de transportación escolar obligatoria'),
    ('D09', 'D09 - Depósitos en cuentas para el ahorro, primas que tengan como base planes de pensiones'),
    ('D10', 'D10 - Pagos por servicios educativos (colegiaturas)'),
    ('S01', 'S01 - Sin efectos fiscales'),
    ('CP01', 'CP01 - Pagos'),
    ('CN01', 'CN01 - Nómina'),
]

REGIMENES_FISCALES = [
    ('601', '601 - General de Ley Personas Morales'),
    ('603', '603 - Personas Morales con Fines no Lucrativos'),
    ('605', '605 - Sueldos y Salarios e Ingresos Asimilados a Salarios'),
    ('606', '606 - Arrendamiento'),
    ('607', '607 - Régimen de Enajenación o Adquisición de Bienes'),
    ('608', '608 - Demás ingresos'),
    ('609', '609 - Consolidación'),
    ('610', '610 - Residentes en el Extranjero sin Establecimiento Permanente en México'),
    ('611', '611 - Ingresos por Dividendos (socios y accionistas)'),
    ('612', '612 - Personas Físicas con Actividades Empresariales y Profesionales'),
    ('614', '614 - Ingresos por intereses'),
    ('615', '615 - Régimen de los ingresos por obtención de premios'),
    ('616', '616 - Sin obligaciones fiscales'),
    ('620', '620 - Sociedades Cooperativas de Producción que optan por diferir sus ingresos'),
    ('621', '621 - Incorporación Fiscal'),
    ('622', '622 - Actividades Agrícolas, Ganaderas, Silvícolas y Pesqueras'),
    ('623', '623 - Opcional para Grupos de Sociedades'),
    ('624', '624 - Coordinados'),
    ('625', '625 - Régimen de las Actividades Empresariales con ingresos a través de Plataformas Tecnológicas'),
    ('626', '626 - Régimen Simplificado de Confianza - RESICO'),
]

FORMAS_PAGO = [
    ('01', '01 - Efectivo'),
    ('02', '02 - Cheque nominativo'),
    ('03', '03 - Transferencia electrónica de fondos'),
    ('04', '04 - Tarjeta de crédito'),
    ('05', '05 - Monedero electrónico'),
    ('06', '06 - Dinero electrónico'),
    ('08', '08 - Vales de despensa'),
    ('12', '12 - Dación en pago'),
    ('13', '13 - Pago por subrogación'),
    ('14', '14 - Pago por consignación'),
    ('15', '15 - Condonación'),
    ('17', '17 - Compensación'),
    ('23', '23 - Novación'),
    ('24', '24 - Confusión'),
    ('25', '25 - Remisión de deuda'),
    ('26', '26 - Prescripción o caducidad'),
    ('27', '27 - A satisfacción del acreedor'),
    ('28', '28 - Tarjeta de débito'),
    ('29', '29 - Tarjeta de servicios'),
    ('30', '30 - Aplicación de anticipos'),
    ('31', '31 - Intermediario pagos'),
    ('99', '99 - Por definir'),
]


class AutofacturaPortal(CustomerPortal):

    def _get_order_sudo(self, order_id, access_token):
        """Obtiene el pedido validando el token de acceso."""
        order = request.env['sale.order'].sudo().browse(int(order_id))
        if not order.exists():
            return None
        # Validar token
        if not self._verify_order_token(order, access_token):
            return None
        return order

    def _verify_order_token(self, order, access_token):
        """Verifica que el access_token corresponde al pedido."""
        if not access_token:
            return False
        return order.access_token == access_token

    def _get_cfdi_values_from_partner(self, partner):
        """Extrae valores CFDI almacenados en el contacto."""
        return {
            'rfc': partner.vat or '',
            'uso_cfdi': partner.l10n_mx_edi_usage or 'G03',
            'regimen_fiscal': partner.l10n_mx_edi_fiscal_regime or '601',
        }

    # ------------------------------------------------------------------
    # GET — formulario de datos fiscales
    # ------------------------------------------------------------------
    @http.route(
        '/autofactura/<int:order_id>/<string:access_token>',
        type='http', auth='public', website=True, sitemap=False,
    )
    def autofactura_form(self, order_id, access_token, **kwargs):
        order = self._get_order_sudo(order_id, access_token)
        if not order:
            return request.render('carbotecnia_autofactura.error_acceso')

        # Pedido debe estar confirmado
        if order.state not in ('sale', 'done'):
            return request.render('carbotecnia_autofactura.error_estado', {
                'order': order,
            })

        # Ya tiene facturas válidas
        facturas_validas = order.invoice_ids.filtered(
            lambda i: i.state == 'posted' and i.move_type == 'out_invoice'
        )
        if facturas_validas:
            return request.render('carbotecnia_autofactura.ya_facturado', {
                'order': order,
                'facturas': facturas_validas,
            })

        partner = order.partner_invoice_id or order.partner_id
        cfdi_values = self._get_cfdi_values_from_partner(partner)

        return request.render('carbotecnia_autofactura.autofactura_form', {
            'order': order,
            'partner': partner,
            'access_token': access_token,
            'cfdi_values': cfdi_values,
            'usos_cfdi': USOS_CFDI,
            'regimenes_fiscales': REGIMENES_FISCALES,
            'formas_pago': FORMAS_PAGO,
            'error': kwargs.get('error', ''),
        })

    # ------------------------------------------------------------------
    # POST — generar factura CFDI
    # ------------------------------------------------------------------
    @http.route(
        '/autofactura/<int:order_id>/<string:access_token>/generar',
        type='http', auth='public', website=True, sitemap=False, methods=['POST'],
    )
    def autofactura_generar(self, order_id, access_token, **kwargs):
        order = self._get_order_sudo(order_id, access_token)
        if not order:
            return request.render('carbotecnia_autofactura.error_acceso')

        if order.state not in ('sale', 'done'):
            return request.render('carbotecnia_autofactura.error_estado', {'order': order})

        # Guardia: pedidos de MercadoLibre solo se facturan después del surtido
        if getattr(order, 'ml_order_number', False):
            salidas = order.picking_ids.filtered(
                lambda p: p.picking_type_code == 'outgoing')
            entregado = salidas and all(
                p.state in ('done', 'cancel') for p in salidas) and any(
                p.state == 'done' for p in salidas)
            if not entregado:
                return request.render('carbotecnia_autofactura.error_estado', {'order': order})

        # Validar datos fiscales del formulario
        rfc = (kwargs.get('rfc') or '').strip().upper()
        razon_social = (kwargs.get('razon_social') or '').strip().upper()
        uso_cfdi = kwargs.get('uso_cfdi', 'G03')
        regimen_fiscal = kwargs.get('regimen_fiscal', '601')
        forma_pago = kwargs.get('forma_pago', '99')
        cp_receptor = (kwargs.get('cp_receptor') or '').strip()

        # Validaciones básicas
        errors = []
        if not rfc:
            errors.append('El RFC es obligatorio.')
        elif len(rfc) < 12:
            errors.append('El RFC no es válido (mínimo 12 caracteres).')
        if not razon_social:
            errors.append('La razón social es obligatoria.')
        if not cp_receptor or len(cp_receptor) != 5:
            errors.append('El código postal del receptor debe tener 5 dígitos.')
        if not uso_cfdi:
            errors.append('Selecciona el uso de CFDI.')
        if not regimen_fiscal:
            errors.append('Selecciona el régimen fiscal.')

        if errors:
            partner = order.partner_invoice_id or order.partner_id
            cfdi_values = self._get_cfdi_values_from_partner(partner)
            return request.render('carbotecnia_autofactura.autofactura_form', {
                'order': order,
                'partner': partner,
                'access_token': access_token,
                'cfdi_values': {
                    'rfc': rfc,
                    'uso_cfdi': uso_cfdi,
                    'regimen_fiscal': regimen_fiscal,
                },
                'usos_cfdi': USOS_CFDI,
                'regimenes_fiscales': REGIMENES_FISCALES,
                'formas_pago': FORMAS_PAGO,
                'error': ' '.join(errors),
                'form_values': kwargs,
            })

        try:
            # Actualizar datos fiscales del partner
            partner = order.partner_invoice_id or order.partner_id
            partner.sudo().write({
                'vat': rfc,
                'name': razon_social,
                'l10n_mx_edi_usage': uso_cfdi,
                'l10n_mx_edi_fiscal_regime': regimen_fiscal,
                'zip': cp_receptor,
            })

            # Crear la factura desde el pedido
            invoice_wizard = request.env['sale.advance.payment.inv'].sudo().with_context(
                active_ids=[order.id],
                active_model='sale.order',
            ).create({'advance_payment_method': 'delivered'})
            invoice_wizard.create_invoices()

            # Obtener la factura recién creada
            invoice = order.invoice_ids.filtered(
                lambda i: i.state == 'draft' and i.move_type == 'out_invoice'
            )[-1:]

            if not invoice:
                raise ValidationError('No se pudo crear la factura.')

            # Aplicar datos CFDI adicionales en la factura
            invoice.sudo().write({
                'l10n_mx_edi_usage': uso_cfdi,
                'l10n_mx_edi_payment_method_id': request.env['l10n_mx_edi.payment.method'].sudo().search(
                    [('code', '=', forma_pago)], limit=1
                ).id or False,
            })

            # Validar (timbrar) la factura — esto dispara el PAC
            invoice.sudo().action_post()

            _logger.info(
                'Autofactura generada: pedido %s → factura %s por portal',
                order.name, invoice.name,
            )

            # Redirigir al portal de facturas con token
            invoice_token = invoice.sudo().access_token
            if not invoice_token:
                invoice.sudo()._portal_ensure_token()
                invoice_token = invoice.sudo().access_token

            return request.redirect(
                f'/my/invoices/{invoice.id}?access_token={invoice_token}'
            )

        except Exception as e:
            _logger.error('Error en autofacturación pedido %s: %s', order_id, str(e))
            partner = order.partner_invoice_id or order.partner_id
            cfdi_values = self._get_cfdi_values_from_partner(partner)
            return request.render('carbotecnia_autofactura.autofactura_form', {
                'order': order,
                'partner': partner,
                'access_token': access_token,
                'cfdi_values': cfdi_values,
                'usos_cfdi': USOS_CFDI,
                'regimenes_fiscales': REGIMENES_FISCALES,
                'formas_pago': FORMAS_PAGO,
                'error': f'Error al generar la factura: {str(e)}',
                'form_values': kwargs,
            })

    # ------------------------------------------------------------------
    # GET — estado de timbrado (para polling desde el portal)
    # ------------------------------------------------------------------
    @http.route(
        '/autofactura/status/<int:invoice_id>/<string:access_token>',
        type='json', auth='public',
    )
    def autofactura_status(self, invoice_id, access_token, **kwargs):
        invoice = request.env['account.move'].sudo().browse(int(invoice_id))
        if not invoice.exists() or invoice.access_token != access_token:
            return {'error': 'Acceso no válido'}

        return {
            'state': invoice.state,
            'edi_state': invoice.l10n_mx_edi_cfdi_state or 'pending',
            'cfdi_uuid': invoice.l10n_mx_edi_cfdi_uuid or '',
            'name': invoice.name,
        }
