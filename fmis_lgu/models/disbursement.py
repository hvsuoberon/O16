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


class AccountableForms(models.Model):
    _name = "fmis.disbursement"
    _description = "Disbursement"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'analytic.mixin']

    name = fields.Char('Name')
    payee = fields.Many2one('res.partner')
    obr_id = fields.Many2one('obr.here')
    date = fields.Date('Transaction Date')
    particulars = fields.Text('Particualrs')
    amount = fields.Float('Amount')
    tax_3 = fields.Float('Tax 3%')
    tax_1 = fields.Float('Tax 1%')
    amount_due = fields.Float('Amount Due', compute="_get_amount_due")
    certified_a = fields.Char('Certified (1)')
    certified_b = fields.Char('Certified (2)')
    certified_c = fields.Char('Certified (3)')
    approved = fields.Char('Approved By')
    prepared_by = fields.Char('Prepare By')
    certified_by = fields.Char('Certified Correct')
    cheque_date = fields.Date('Cheque Date')
    cheque_number = fields.Many2one('fmis.accounting.form.stub.leaves', string="Cheque Number")
    bank_name = fields.Char('Bank')
    state = fields.Selection(selection=[('draft', 'Available'),
                                        ('check_print', 'For Cheque Printing'),
                                        ('bir_forms', 'For Printing of BIR Forms'),
                                        ('cheque_release', 'For Releasing'),
                                        ('released', 'Cheque Released'),
                                        ], string='Status', tracking=True)


