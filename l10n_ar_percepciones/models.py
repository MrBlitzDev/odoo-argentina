# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, _, fields, api, tools
from odoo.exceptions import UserError,ValidationError
from odoo.tools.safe_eval import safe_eval
import datetime
from datetime import date

class AccountMove(models.Model):
    _inherit = 'account.move'

    dt_percepciones = fields.Datetime('Fecha/Hora Percepciones')

    def action_post(self):
        for rec in self:
            if rec.move_type in ['out_refund','out_invoice'] and rec.dt_percepciones:
                for inv_line in rec.invoice_line_ids:
                    date1 = str(inv_line.write_date)[:19]
                    date2 = str(rec.dt_percepciones)
                    if date1 > date2:
                        raise ValidationError('No se puede confirmar porque antes debe calcular percepciones %s %s'%(date1,date2))
        return super(AccountMove, self).action_post()

    def btn_add_percepciones(self):
        self.ensure_one()
        if self.state not in ['draft','sent']:
            raise ValidationError('Solo se pueden agregar/modificar impuestos en movimientos en borrador')
        if self.move_type not in ['out_invoice','out_refund']:
            raise ValidationError('El tipo de documento debe ser factura de cliente o nota de crédito')
        vals = {
            'move_id': self.id,
            }
        wizard_id = self.env['percepciones.wizard'].create(vals)
        for line in self.line_ids.filtered(lambda x: x.tax_line_id):
            vals_line = {
                    'invoice_tax_id': wizard_id.id,
                    'tax_id': line.tax_line_id.id,
                    'amount': line.amount_currency,
                    'new_tax': False,
                    }
            if line.tax_line_id.tax_group_id and line.tax_line_id.tax_group_id.tax_type == 'withholdings':
                continue
            line_id = self.env['percepciones.line.wizard'].create(vals_line)
        for perception in self.partner_id.perception_ids:
            if self.move_type == 'out_invoice':
                sign = 1
            else:
                sign = -1
            amount = self.amount_untaxed * perception.percent / 100 
            vals_line = {
                    'invoice_tax_id': wizard_id.id,
                    'tax_id': perception.tax_id.id,
                    'amount': amount * sign,
                    'new_tax': True,
                    }
            line_id = self.env['percepciones.line.wizard'].search([('invoice_tax_id','=',wizard_id.id),('tax_id','=',perception.tax_id.id)])
            if not line_id:
                line_id = self.env['percepciones.line.wizard'].create(vals_line)
        if self.partner_shipping_id:
            for perception in self.partner_shipping_id.perception_ids:
                if self.move_type == 'out_invoice':
                    sign = 1
                else:
                    sign = -1
                amount = self.amount_untaxed * perception.percent / 100 
                vals_line = {
                    'invoice_tax_id': wizard_id.id,
                    'tax_id': perception.tax_id.id,
                    'amount': amount * sign,
                    'new_tax': True,
                    }
                line_id = self.env['percepciones.line.wizard'].search([('invoice_tax_id','=',wizard_id.id),('tax_id','=',perception.tax_id.id)])
                if not line_id:
                    line_id = self.env['percepciones.line.wizard'].create(vals_line)
        res = {
            'name': _('Percepciones Wizard'),
            'res_model': 'percepciones.wizard',
            'view_mode': 'form',
            'res_id': wizard_id.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }
        return res

class AccountPadron(models.Model):
	_name = 'account.padron'
	_description = 'account.padron'

	date_from = fields.Date('Fecha Desde')
	date_to = fields.Date('Fecha Hasta')
	cuit = fields.Char('CUIT',index=True)
	tax = fields.Char('Impuesto')
	percent = fields.Float('Porcentaje')

class ResPartnerPerception(models.Model):
	_name = "res.partner.perception"
	_description = "Perception Defined in Partner"

	tax_id = fields.Many2one('account.tax',string='Impuesto',required=True)
	percent = fields.Float('Percent', required=True)
	date_from = fields.Date('Fecha Desde')
	partner_id = fields.Many2one('res.partner', 'Cliente')

class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def update_percepciones(self):
        partners = self.env['res.partner'].search([])
        for partner in partners:
            for perception in partner.perception_ids:
                perception.unlink()
            padron_ids = self.env['account.padron'].search([('cuit','=',partner.vat)])
            for padron in padron_ids:
                tax_id = self.env['account.tax'].search([('padron_prefix','=',padron.tax)])
                if not tax_id:
                    raise ValidationError('Impuesto no determinado %s'%(padron.tax))
                perception_ids = self.env['res.partner.perception'].search([('partner_id','=',partner.id),('tax_id','=',tax_id.id)],order='date_from desc')
                if not perception_ids:
                    vals = {'partner_id': partner.id,'percent': padron.percent,'tax_id': tax_id.id,'date_from': padron.date_from}
                    perception_id = self.env['res.partner.perception'].create(vals)

    def partner_update_percepciones(self):
        self.ensure_one()
        for partner in self:
            for perception in partner.perception_ids:
                perception.unlink()
            padron_ids = self.env['account.padron'].search([('cuit','=',partner.vat)],order='date_from desc')
            for padron in padron_ids:
                tax_id = self.env['account.tax'].search([('padron_prefix','=',padron.tax)])
                if not tax_id:
                    raise ValidationError('Impuesto no determinado %s'%(padron.tax))
                perception_ids = self.env['res.partner.perception'].search([('partner_id','=',partner.id),('tax_id','=',tax_id.id)])
                if not perception_ids:
                    vals = {'partner_id': partner.id,'percent': padron.percent,'tax_id': tax_id.id,'date_from': padron.date_from}
                    perception_id = self.env['res.partner.perception'].create(vals)

    perception_ids = fields.One2many('res.partner.perception', 'partner_id', 'Percepciones Definidas')

