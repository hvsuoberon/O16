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


class Collection(models.Model):
    _name = "fmis.collection"
    _description = "Collections"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'analytic.mixin']
    _order = 'id desc'

    name = fields.Char('Transaction #')
    date = fields.Date('Transaction Date', default=lambda self: fields.Date.today())

    payor = fields.Char(string="Payor")
    officer_id = fields.Many2one('res.users', 'Collection Officer',  default=lambda self: self.env.user)
    type = fields.Many2one('fmis.accounting.form.type', string='Form Type')
    leaf_id = fields.Many2one('fmis.accounting.form.stub.leaves', 'Document #')
    amount = fields.Float('Amount')
    cheque_bank = fields.Char('Cheque Bank')
    cheque_number = fields.Char('Cheque Number')
    cheque_date = fields.Char('Cheque Date')

    state = fields.Selection(selection=[('draft', 'Draft'),
                                        ('posted', 'Posted'),
                                        ('cancel', 'Cancelled'),
                                        ], string='Status', tracking=True, default="draft")
    payment_type = fields.Selection(selection=[('cash', 'Cash'),
                                        ('cheque', 'Cheque'),
                                        ], string='Payment Type', default="cash")

    def confirm(self):

        self.leaf_id.write({'state': 'used'})
        self.state = 'posted'

    def cancel(self):
        self.leaf_id.write({'state': 'void'})
        self.state = 'cancel'

    def set_to_draft(self):
        self.leaf_id.write({'state': 'available'})
        self.state = 'draft'


class Burial(models.Model):
    _name = "fmis.collection.burial"
    _inherits = {'fmis.collection': 'collection_id'}
    _inherit = ['mail.thread', 'mail.activity.mixin', 'analytic.mixin']
    _order = 'id desc'
    _rec_name = 'leaf_id'

    collection_id = fields.Many2one('fmis.collection', 'Collection', auto_join=True, index=True,
                                      ondelete="cascade", required=True)

    #burial  permit
    agency = fields.Char('Agency')
    permission_type = fields.Selection(selection=[('inter','Interment'),
                                        ('disinter','Disinterment'),
                                        ('remove', 'Remove'),
                                        ], string='Permission Type')
    remains_of = fields.Char('Remains of')
    nationality = fields.Char('Nationality')
    age = fields.Integer('Age')
    sex = fields.Selection(selection=[('male','Male'),
                                        ('female','female'),
                                        ], string='Sex')
    date_death = fields.Date('Date of Death')
    cemetery = fields.Char('Name of Cemetery')
    disinterment = fields.Char('In case of disinterment')
    type_of_disease = fields.Selection(selection=[('inf','Infectious'),
                                        ('non','Non-Infectious'),
                                          ('na', 'Not Applicable'),
                                        ], string='Type of Disease')
    embalmed = fields.Boolean('Embalmed?')
    disposition = fields.Char('Disposition of Remains')


    def confirm(self):
        self.collection_id.confirm()

    def cancel(self):
        self.collection_id.cancel()

    def set_to_draft(self):
        self.collection_id.set_to_draft()

class Marriage(models.Model):
    _name = "fmis.collection.marriage"
    _inherits = {'fmis.collection': 'collection_id'}
    _inherit = ['mail.thread', 'mail.activity.mixin', 'analytic.mixin']
    _order = 'id desc'
    _rec_name = 'leaf_id'

    collection_id = fields.Many2one('fmis.collection', 'Collection', auto_join=True, index=True,
                                      ondelete="cascade", required=True)

    #marriage liense
    marriage_1 = fields.Char('Name')
    birthdate_1 = fields.Date('Birthday')
    address_1 = fields.Char('Address')

    marriage_2 = fields.Char('Name')
    birthdate_2 = fields.Date('Birthday')
    address_2 = fields.Char('Address')

    documents = fields.Char('Documents')

    def confirm(self):
        self.collection_id.confirm()

    def cancel(self):
        self.collection_id.cancel()

    def set_to_draft(self):
        self.collection_id.set_to_draft()

class RealProperty(models.Model):
    _name = "fmis.collection.property"
    _inherits = {'fmis.collection': 'collection_id'}
    _inherit = ['mail.thread', 'mail.activity.mixin', 'analytic.mixin']
    _order = 'id desc'
    _rec_name = 'leaf_id'

    collection_id = fields.Many2one('fmis.collection', 'Collection', auto_join=True, index=True,
                                      ondelete="cascade", required=True)

    #Real Property Tax
    basic_tax = fields.Boolean('Basic Tax')
    sef = fields.Boolean('Special Education Fund')
    line_ids = fields.One2many('fmis.collection.property.line', 'property_id')


    def confirm(self):
        self.collection_id.confirm()

    def cancel(self):
        self.collection_id.cancel()

    def set_to_draft(self):
        self.collection_id.set_to_draft()

class RealPropertyDetails(models.Model):
    _name = "fmis.collection.property.line"

    property_id = fields.Many2one('fmis.collection.property')
    name = fields.Char('Name of Declared Owner')
    location = fields.Char('Location Number and Street or Barangay')
    lot = fields.Char('Lot and Block Number')
    td_no = fields.Char('Tax Declaration Number')
    av_land = fields.Float('Land', help="Assessed Value of Land")
    av_improvements = fields.Float('Improvements', help="Assessed Value of Improvements")
    av_total = fields.Float('Total', compute="get_av_total")
    tax_due = fields.Float('Tax Due')
    inst_no = fields.Integer('Installment #')
    inst_payment = fields.Float('Installment Payment')
    full_payment = fields.Float('Full Payment')
    penalty = fields.Float('Penalty Percent')
    total = fields.Float('Total', compute="get_line_total")

    @api.depends('inst_payment', 'full_payment', 'penalty')
    @api.onchange('inst_payment', 'full_payment', 'penalty')
    def get_line_total(self):
        for rec in self:
            rec.total = rec.tax_due + rec.inst_payment + rec.full_payment + rec.penalty

    @api.depends('av_land','av_improvements')
    @api.onchange('av_land', 'av_improvements')
    def get_av_total(self):
        for rec in self:
            rec.av_total = rec.av_improvements + rec.av_land

class OfficialReceipt(models.Model):
    _name = "fmis.collection.or"
    _inherits = {'fmis.collection': 'collection_id'}
    _inherit = ['mail.thread', 'mail.activity.mixin', 'analytic.mixin']
    _order = 'id desc'
    _rec_name = 'leaf_id'

    collection_id = fields.Many2one('fmis.collection', 'Collection', auto_join=True, index=True,
                                      ondelete="cascade", required=True)

    agency = fields.Char('Agency')
    line_ids = fields.One2many('fmis.collection.or.line', 'or_id')

    def confirm(self):
        self.collection_id.confirm()

    def cancel(self):
        self.collection_id.cancel()

    def set_to_draft(self):
        self.collection_id.set_to_draft()

class OfficialReceiptDetails(models.Model):
    _name = "fmis.collection.or.line"

    or_id = fields.Many2one('fmis.collection.or')
    nature_of_collection = fields.Char('Nature of Collection')
    account_id = fields.Many2one('account.account', string="Account Code")
    amount = fields.Float('Amount')


class Ownership(models.Model):
    _name = "fmis.collection.ownership"
    _inherits = {'fmis.collection': 'collection_id'}
    _inherit = ['mail.thread', 'mail.activity.mixin', 'analytic.mixin']
    _order = 'id desc'
    _rec_name = 'leaf_id'

    collection_id = fields.Many2one('fmis.collection', 'Collection', auto_join=True, index=True,
                                      ondelete="cascade", required=True)

    address = fields.Char('Address')
    particulars = fields.Char('Particulars (Animal)')
    sex = fields.Selection(selection=[('male', 'Male'),
                                      ('female', 'female'),
                                      ], string='Sex')
    age = fields.Integer('Age')
    brand_municipality = fields.Char('Brand of MUnicipality')
    brand_owner = fields.Char('Brand of Owner')


    def confirm(self):
        self.collection_id.confirm()

    def cancel(self):
        self.collection_id.cancel()

    def set_to_draft(self):
        self.collection_id.set_to_draft()


class OwnershipTransfer(models.Model):
    _name = "fmis.collection.ownership.transfer"
    _inherits = {'fmis.collection': 'collection_id'}
    _inherit = ['mail.thread', 'mail.activity.mixin', 'analytic.mixin']
    _order = 'id desc'
    _rec_name = 'leaf_id'

    collection_id = fields.Many2one('fmis.collection', 'Collection', auto_join=True, index=True,
                                      ondelete="cascade", required=True)

    address = fields.Char('Address')
    previous_owner = fields.Char('Previous Owner')
    previous_address = fields.Char('Previous Owner Address')
    particulars = fields.Char('Particulars (Animal)')
    sold_amount = fields.Float('Sold in amount of')
    sex = fields.Selection(selection=[('male', 'Male'),
                                      ('female', 'female'),
                                      ], string='Sex')
    age = fields.Integer('Age')
    prev_coo = fields.Char('Previous Cert of Ownership #')
    brand_municipality = fields.Char('Brand of MUnicipality')
    brand_owner = fields.Char('Brand of Owner')


    def confirm(self):
        self.collection_id.confirm()

    def cancel(self):
        self.collection_id.cancel()

    def set_to_draft(self):
        self.collection_id.set_to_draft()