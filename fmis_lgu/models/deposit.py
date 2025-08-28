# -*- coding: utf-8 -*-
import json
# from lxml import etree
import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.api import depends
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


class CollectionDeposit(models.Model):
    _name = "fmis.collection.deposit"
    _description = "Deposit"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'analytic.mixin']
    _order = 'id desc'

    name = fields.Char('Name')
    bank_id = fields.Many2one('res.partner.bank', string="Bank")
    officer_id = fields.Many2one('res.users', 'Collection Officer', default=lambda self: self.env.user)
    date = fields.Date('Transaction Date', default=lambda self: fields.Date.today())
    state = fields.Selection(selection=[('draft', 'Draft'),
                                        ('confirm', 'Confirmed'),
                                        ('cancel', 'Cancelled'),
                                        ], string='Status', tracking=True, default="draft")
    deposit_ids = fields.One2many('fmis.collection.deposit.det', 'deposit_id', string="Details")
    amount = fields.Float('Total Amount', compute="_get_total", stored=True)

    @api.depends('deposit_ids')
    @api.onchange('deposit_ids')
    def _get_total(self):
        for rec in self:
            rec.amount = sum(rec.deposit_ids.mapped('amount'))

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('fmis.collection.deposit')

        res = super(CollectionDeposit, self).create(vals)

        return res


    def confirm(self):
        self.state = 'confirm'

    def set_to_draft(self):

        self.state = 'draft'


class ChequeClearingDetails(models.Model):
    _name = "fmis.collection.deposit.det"
    _description = "Collection Deposit Details"

    deposit_id = fields.Many2one('fmis.collection.deposit')
    collection_id = fields.Many2one('fmis.collection')
    payor = fields.Char(related="collection_id.payor")
    amount = fields.Float(related="collection_id.amount", string='Amount')
    cheque_bank = fields.Char(related="collection_id.cheque_bank", string='Cheque Bank')
    cheque_number = fields.Char(related="collection_id.cheque_number", string='Cheque Number')
    cheque_date = fields.Char(related="collection_id.cheque_date", string='Cheque Date')
