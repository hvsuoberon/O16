# -*- coding: utf-8 -*-
import json
# from lxml import etree
import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.tools import float_is_zero, float_compare, float_round
from odoo.tools.misc import formatLang
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError, RedirectWarning, ValidationError
# from odoo.tools import amount_to_text_en
import math

# from common_methods import _check_balance, _check_balance_pr

# import odoo.addons.decimal_precision as dp
import logging

_logger = logging.getLogger(__name__)


class Disbursement(models.Model):
    _name = "fmis.disbursement"
    _description = "Disbursement"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'analytic.mixin']
    _order = 'id desc'

    name = fields.Char('Name')
    bank_id = fields.Many2one('res.partner.bank', string="Bank")
    payee = fields.Char('Payee')
    obr_id = fields.Many2one('budgeting.obr', string="Obligation Request")
    date = fields.Date('Transaction Date', default=lambda self: fields.Date.today())
    particulars = fields.Text('Particulars')
    amount = fields.Float('Amount')
    tax_3 = fields.Float('Tax 3%', compute="_get_amount_due", store=True)
    tax_1 = fields.Float('Tax 1%', compute="_get_amount_due", store=True)
    amount_due = fields.Float('Amount Due', compute="_get_amount_due", store=True)
    certified_a = fields.Char('Certified (1)')
    certified_b = fields.Char('Certified (2)')
    certified_c = fields.Char('Certified (3)')
    approved = fields.Char('Approved By')
    prepared_by = fields.Char('Prepared By')
    certified_by = fields.Char('Certified Correct')
    cheque_date = fields.Date('Cheque Date', required=True)
    cheque_number = fields.Many2one('fmis.accounting.form.stub.leaves', string="Cheque Number", domain=[('state','=','available'),('form_name','=','Cheque')], required=True)
    bank_name = fields.Char('Bank')
    state = fields.Selection(selection=[('draft', 'Draft'),
                                        ('check_print', 'For Cheque Printing'),
                                        ('bir_forms', 'For Printing of BIR Forms'),
                                        ('cheque_release', 'For Releasing'),
                                        ('released', 'Cheque Released'),
                                        ], string='Status', tracking=True, default="draft")
    advice_id = fields.Many2one('fmis.disbursement.advice', string="Advice on Local Cheque Disbursement")

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('fmis.disbursement')

        res = super(Disbursement, self).create(vals)

        return res

    @api.depends('obr_id')
    @api.onchange('obr_id')
    def onchange_obr_id(self):
        if self.obr_id:
            self.payee = self.obr_id.payee
            self.particulars = self.obr_id.purpose
            self.amount = self.obr_id.amount_total
        else:
            self.payee = None
            self.particulars = None
            self.amount = None

    @api.depends('amount')
    @api.onchange('amount')
    def _get_amount_due(self):
        for rec in self:
            rec.tax_1 = rec.amount * 0.01
            rec.tax_3 = rec.amount * 0.03
            rec.amount_due = rec.amount - rec.tax_1 - rec.tax_3

    def confirm(self):
        if self.cheque_number.state != 'available':
            raise UserError(_('Cheque is not available'))
        self.cheque_number.write({'state': 'used'})
        self.state = 'check_print'

    def bir_forms(self):
        self.state = 'bir_forms'

    def cheque_release(self):

        self.state = 'cheque_release'

    def released(self):

        self.state = 'released'

    def add_to_aa(self):
        grps = set(self.mapped('bank_id'))

        for grp in grps:
            vals = {
                'bank_id': grp.id,
                'date': fields.Date.today(),
            }
            rec_id = self.env['fmis.disbursement.advice'].create(vals)

            for rec in self.filtered(lambda rec: rec.bank_id.id == grp.id):
                rec.write({'advice_id': rec_id.id})


class DisbursementAdvice(models.Model):
    _name = "fmis.disbursement.advice"
    _description = "Advice on Local Cheque Disbursement"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'analytic.mixin']
    _order = 'id desc'

    name = fields.Char('Name')
    bank_id = fields.Many2one('res.partner.bank', string="Bank")
    date = fields.Date('Date')
    disbursement_ids = fields.One2many('fmis.disbursement', 'advice_id')
    state = fields.Selection(selection=[('draft', 'Draft'),
                                        ('confirm', 'Confirmed'),
                                        ], string='Status', tracking=True, default="draft")
    total = fields.Float('Total', compute='_compute_total')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    municipal_accountant = fields.Char('Municipal Accountant', tracking=True, default=lambda self: self._get_default_values1())
    officer_in_charge = fields.Char('Officer in Charge', tracking=True, default=lambda self: self._get_default_values2())
    prepared_by = fields.Char('Prepared By', tracking=True, default=lambda self: self._get_default_values3())
    prepared_by_pos = fields.Char('Prepared By Position', tracking=True, default=lambda self: self._get_default_values4())
    delivered_by = fields.Char('Delivered By', tracking=True, default=lambda self: self._get_default_values5())
    delivered_by_pos = fields.Char('Delivered By Position', tracking=True, default=lambda self: self._get_default_values6())

    def _get_default_values1(self):
        def_val = self.env['fmis.accounting.default.value'].search([('municipal_accountant','!=',False)], limit=1)
        if def_val:
            return def_val.municipal_accountant
        else:
            return False

    def _get_default_values2(self):
        def_val = self.env['fmis.accounting.default.value'].search([('municipal_accountant','!=',False)], limit=1)
        if def_val:
            return def_val.officer_in_charge
        else:
            return False

    def _get_default_values3(self):
        def_val = self.env['fmis.accounting.default.value'].search([('municipal_accountant','!=',False)], limit=1)
        if def_val:
            return def_val.prepared_by
        else:
            return False

    def _get_default_values4(self):
        def_val = self.env['fmis.accounting.default.value'].search([('municipal_accountant','!=',False)], limit=1)
        if def_val:
            return def_val.prepared_by_pos
        else:
            return False

    def _get_default_values5(self):
        def_val = self.env['fmis.accounting.default.value'].search([('municipal_accountant','!=',False)], limit=1)
        if def_val:
            return def_val.delivered_by
        else:
            return False

    def _get_default_values6(self):
        def_val = self.env['fmis.accounting.default.value'].search([('municipal_accountant','!=',False)], limit=1)
        if def_val:
            return def_val.delivered_by_pos
        else:
            return False


    def _compute_total(self):
        for rec in self:
            rec.total = sum(rec.disbursement_ids.mapped('amount_due'))

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('fmis.disbursement.advice')

        res = super(DisbursementAdvice, self).create(vals)

        return res

    def confirm(self):

        self.state = 'confirm'