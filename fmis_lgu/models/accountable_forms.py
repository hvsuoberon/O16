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
    padding = fields.Integer('Padding')
    limit = fields.Integer('Limit Per Person')


class AccountableFormsEntry(models.Model):
    _name = "fmis.accounting.form.entry"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'analytic.mixin']
    _description = "Accountable Forms Entry"

    name = fields.Char('Transaction #')
    form_id = fields.Many2one('fmis.accounting.form.type','Form')
    form_name = fields.Char(related='form_id.name')
    bank_id = fields.Many2one('res.partner.bank', string="Bank")
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
            if len(set(rec.stub_ids.mapped('state'))) == 1 and tuple(set(rec.stub_ids.mapped('state')))[0] == 'available':
                rec.stub_ids.unlink()
            else:
                raise UserError('Cannot populate. Some of the stubs were already assigned or used.')

            s_from = rec.series_from
            for cntr in range(rec.no_of_stubs):
                s_from_lf = str(s_from)
                if rec.form_id.padding != 0:
                    s_from_lf = s_from_lf.zfill(rec.form_id.padding)
                s_to = s_from + rec.no_of_leaves - 1
                s_to_lf = str(s_to)
                if rec.form_id.padding != 0:
                    s_to_lf = s_to_lf.zfill(rec.form_id.padding)
                leaves = []
                for leaf in range(s_from, s_to + 1):
                    lf = str(leaf)
                    if rec.form_id.padding != 0:
                        lf = lf.zfill(rec.form_id.padding)
                    leaves.append((0, 0, {
                        'series': f'{rec.form_id.code} {lf}',
                        'state': 'available',
                    }))

                vals = {
                    'fe_id': rec.id,
                    'name' : f'{rec.form_id.code} {s_from_lf} - {s_to_lf}',
                    'series_from' : s_from_lf,
                    'series_to': s_to_lf,
                    'state': 'available',
                    'leaves_ids' : leaves
                }
                s_from = s_to + 1
                rec.stub_ids.create(vals)

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
    leaves_ids = fields.One2many('fmis.accounting.form.stub.leaves', 'stub_id', 'Leaves')
    assigned_to = fields.Many2one('res.users', 'Collection Officer')

    def unlink(self):
        for record in self:
            if record.fe_id.state == 'confirm':
                raise UserError("You cannot delete a confirmed entry. Please cancel it first.")
        return super(AccountableFormsStub, self).unlink()

class AccountableFormsLeaves(models.Model):
    _name = "fmis.accounting.form.stub.leaves"
    _description = "Accountable Forms Stub Leaves"
    _rec_name = "series"

    stub_id = fields.Many2one('fmis.accounting.form.stub', 'Stub #')
    stub_form_id = fields.Many2one(related="stub_id.fe_id.form_id")
    form_name = fields.Char(related='stub_form_id.name')
    series = fields.Char('Series')
    state = fields.Selection(selection=[('available', 'Available'),
                                        ('used', 'Used'),
                                        ('void', 'Voided'),
                                        ], string='Status', readonly=True)

class AccountableFormsAssignment(models.Model):
    _name = "fmis.accounting.form.stub.assignment"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'analytic.mixin']
    _description = "Accountable Forms Stub Assignment"

    name = fields.Char('Transaction #')
    officer_id = fields.Many2one('res.users', 'Collection Officer',  default=lambda self: self.env.user)
    date = fields.Date('Date of Request')
    state = fields.Selection(selection=[('draft', 'Draft'),
                                        ('request', 'Requested'),
                                        ('approve', 'Approved'),
                                        ('reject', 'Rejected'),
                                        ('cancel', 'Cancelled'),
                                        ], string='Status', default='draft')
    assigned_stub_ids = fields.One2many('fmis.accounting.form.stub.assignment.detail', 'assignment_id', string="Assigned Stubs")

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('stub.assignment')

        res = super(AccountableFormsAssignment, self).create(vals)

        return res

    def request(self):
        self.state = 'request'

    def approve(self):
        self.state = 'approve'

    def reject(self):
        self.state = 'reject'

    def cancel(self):
        self.state = 'cancel'

    def set_to_draft(self):
        self.state = 'draft'


class AccountableFormsAssignmentDetails(models.Model):
    _name = "fmis.accounting.form.stub.assignment.detail"
    _description = "Accountable Forms Stub Assignment Details"

    assignment_id = fields.Many2one('fmis.accounting.form.stub.assignment')
    form_id = fields.Many2one('fmis.accounting.form.type', 'Form')
    no_stubs = fields.Integer('# of Stubs')
    unused_count = fields.Integer('Unused Stubs', compute='get_assigned_count', stored=True)
    unused_leaves = fields.Integer('Unused Leaves', compute='get_assigned_count', stored=True)
    # stub_id = fields.Many2one('fmis.accounting.form.stub')
    # series_from = fields.Integer(related="stub_id.series_from")
    # series_to = fields.Integer(related="stub_id.series_to")

    @api.depends('form_id')
    @api.onchange('form_id')
    def get_assigned_count(self):
        for rec in self:
            get_stubs = self.env['fmis.accounting.form.stub'].search([('assigned_to','=',rec.assignment_id.officer_id.id),('state','=','assign')])
            rec.unused_count = len(get_stubs)
            leaves = 0
            for stub in get_stubs:
                leaves += len(stub.leaves_ids.filtered(lambda x: x.state == 'available').mapped('id'))
            rec.unused_leaves = leaves


