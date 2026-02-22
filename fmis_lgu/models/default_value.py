# -*- coding: utf-8 -*-
import json
# from lxml import etree
import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, SUPERUSER_ID, _


class AccountableForms(models.Model):
    _name = "fmis.accounting.default.value"
    _description = "Default Values"
    _order = "id desc"

    #accountant's advice
    municipal_accountant = fields.Char('Municipal Accountant', tracking=True)
    officer_in_charge = fields.Char('Officer in Charge', tracking=True)
    prepared_by = fields.Char('Prepared By', tracking=True)
    prepared_by_pos = fields.Char('Prepared By Position', tracking=True)
    delivered_by = fields.Char('Delivered By', tracking=True)
    delivered_by_pos = fields.Char('Delivered By Position', tracking=True)




