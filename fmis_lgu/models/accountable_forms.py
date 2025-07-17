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
    _name = "fmis.accounting.form.type"
    _description = "Accountable Forms"

    name = fields.Char('Name')
    code = fields.Char('Code')
    limit = fields.Integer('Limit Per Person')


class AccountableFormsEntry(models.Model):
    _name = "fmis.accounting.form.entry"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'analytic.mixin']
    _description = "Accountable Forms Entry"

    name = fields.Char('Transaction #')
    form_id = fields.Many2one('fmis.accounting.form.type','Form')
    date = fields.Date('Printing Date')
    no_of_leaves = fields.Integer('No. of Leaves per Stub')
    no_of_stubs = fields.Integer('No. of Stubs')
    series_from = fields.Integer('Series From')
    state = fields.Selection(selection=[('draft','Draft'),
                                        ('confirm','Confirmed'),
                                        ('cancel', 'Cancelled'),
                                        ], default="draft", string='Status')
    stub_ids = fields.One2many('fmis.accounting.form.stub', 'fe_id', string="Stubs")
    bank = fields.Char('Bank')

    @api.model
    def create(self, vals):
        cde = 'accountable.forms'

        vals['name'] = self.env['ir.sequence'].next_by_code(cde)
        if not vals['name']:
            raise ValidationError(_('Sequence not set. Please contact the programmer.'))

        res = super(AccountableFormsEntry, self).create(vals)

        return res

    def populate(self):
        for rec in self:
            s_from = rec.series_from
            for cntr in range(rec.no_of_stubs):
                vals = {
                    'fe_id': rec.id,
                    'name' : '',
                }

    def confirm(self):
        self.state = 'confirm'

    def cancel(self):
        self.state = 'cancel'

    def draft(self):
        self.state = 'draft'

class AccountableFormsStub(models.Model):
    _name = "fmis.accounting.form.stub"
    _description = "Accountable Forms Stub"

    fe_id = fields.Many2one('fmis.accounting.form.entry', 'Entry ID')
    name = fields.Char('Name')
    series_from = fields.Integer('Series From')
    series_to = fields.Integer('Series To')
    state = fields.Selection(selection=[('available', 'Available'),
                                        ('assign', 'Assigned'),
                                        ('used', 'Used'),
                                        ], string='Status', tracking=True)


class AccountableFormsLeaves(models.Model):
    _name = "fmis.accounting.form.stub.leaves"
    _description = "Accountable Forms Stub Leaves"

    stub_id = fields.Many2one('fmis.accounting.form.stub', 'Stub #')
    series = fields.Char('Series')
    state = fields.Selection(selection=[('available', 'Available'),
                                        ('used', 'Used'),
                                        ('void', 'Voided'),
                                        ], string='Status')


class AccountableFormsAssignment(models.Model):
    _name = "fmis.accounting.form.stub.assignment"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'analytic.mixin']
    _description = "Accountable Forms Stub Assignment"

    name = fields.Char('Transaction #')
    officer_id = fields.Many2one('res.users', 'Collection Officer')
    date = fields.Date('Date of Request')
    state = fields.Selection(selection=[('draft', 'Draft'),
                                        ('confirm', 'Confirmed'),
                                        ('cancel', 'Cancelled'),
                                        ], string='Status')
    assigned_stub_ids = fields.One2many('fmis.accounting.form.stub.assignment.detail', 'assignment_id', string="Assigned Stubs")

class AccountableFormsAssignmentDetails(models.Model):
    _name = "fmis.accounting.form.stub.assignment.detail"
    _description = "Accountable Forms Stub Assignment Details"

    assignment_id = fields.Many2one('fmis.accounting.form.stub.assignment')
    form_id = fields.Many2one('fmis.accounting.form.type', 'Form')
    stub_id = fields.Many2one('fmis.accounting.form.stub')
    series_from = fields.Integer(related="stub_id.series_from")
    series_to = fields.Integer(related="stub_id.series_to")


