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


class ChequeClearing(models.Model):
    _name = "fmis.cheque.clearing"
    _description = "Cheque Clearing"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'analytic.mixin']
    _order = 'id desc'

    name = fields.Char('Name')
    bank_id = fields.Many2one('res.partner.bank', string="Bank")
    date = fields.Date('Transaction Date', default=lambda self: fields.Date.today())
    state = fields.Selection(selection=[('draft', 'Draft'),
                                        ('confirm', 'Confirmed'),
                                        ('cancel', 'Cancelled'),
                                        ], string='Status', tracking=True, default="draft")
    clearing_ids = fields.One2many('fmis.cheque.clearing.det', 'clearing_id', string="Details")

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('fmis.cheque.clearing')

        res = super(ChequeClearing, self).create(vals)

        return res


    def confirm(self):
        self.state = 'confirm'

    def set_to_draft(self):

        self.state = 'draft'


class ChequeClearingDetails(models.Model):
    _name = "fmis.cheque.clearing.det"
    _description = "Cheque Clearing Details"

    clearing_id = fields.Many2one('fmis.cheque.clearing')
    disbursement_id = fields.Many2one('fmis.disbursement')
    payee = fields.Char(related="disbursement_id.payee")
    amount_due = fields.Float(related="disbursement_id.amount_due", string='Amount Due')
    cheque_date = fields.Date(related="disbursement_id.cheque_date", string='Cheque Date')
