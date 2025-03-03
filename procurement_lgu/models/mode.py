# -*- coding: utf-8 -*-
import json
# from lxml import etree
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.tools import float_is_zero, float_compare
from odoo.tools.misc import formatLang

from odoo.exceptions import UserError, RedirectWarning, ValidationError

import logging

_logger = logging.getLogger(__name__)

class ProcurementMode(models.Model):
    _name = 'procurement.mode'

    name = fields.Char(string='Mode of Procurement')
    long_name = fields.Char(string='Shot Name')

  
class ProcurementSignatory(models.Model):
    _name = 'procurement.signatory'

    conforme_by = fields.Char("RCC II/GSO Designated")
    bac_chairman = fields.Char('BAC Chairman')
    bac_vicechairman = fields.Char('BAC Vice Chairman')
    bac_member1 = fields.Char('BAC Member 1')
    bac_member2 = fields.Char('BAC Member 2')
    bac_member3 = fields.Char('BAC Member 3')
    mayor = fields.Char('Municipal Mayor')
    active = fields.Boolean('Active',default=True)

