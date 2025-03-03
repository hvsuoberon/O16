# -*- coding: utf-8 -*-

import json
from lxml import etree
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.tools import float_is_zero, float_compare
from odoo.tools.misc import formatLang

from odoo.exceptions import UserError, RedirectWarning, ValidationError

# from common_methods import _check_balance, _check_balance_pr
from . import common_methods as cm

import odoo.addons.decimal_precision as dp
import logging

_logger = logging.getLogger(__name__)


class BudgetPeriod(models.Model):
    _name = 'budgeting.period'

    @api.depends('code', 'description')
    def _get_name(self):
        for rec in self:
            cde = ''
            desc = ''
            if rec.code:
                cde = rec.code
            if rec.descript:
                desc = rec.descript
            rec.name = cde + ' - ' + desc 

    name = fields.Char(string='Budget Specification', readonly=True, compute='_get_name')
    code = fields.Char(string="AIP Code", required=True)
    descript = fields.Char(string="Description", required=True)
    start_date = fields.Date(required=True, index=True)
    end_date = fields.Date(required=True, index=True) 
    description = fields.Text(string="Notes")
    dyear = fields.Char(string='Year',store=True, readonly=True, compute='_getyear')
    active = fields.Boolean('Active',default=True)
    

    @api.depends('start_date')
    @api.onchange('start_date')
    def _getyear(self):
        for rec in self:
            if rec.start_date:
                rec.dyear = rec.start_date.year

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        filter_period = self.env.context.get('filter_period')
        if filter_period:
            source_id = self.env.context.get('source_id') or 0
            partner_id = self.env.context.get('partner_id') or 0

            query = """
                        SELECT period_id
                            FROM budgeting_appropriation
                            WHERE budgeting_appropriation.state = 'approved'
                            and partner_id = %s
                            and source_id = %s
                            ;
                    """ % (partner_id, source_id)
            self.env.cr.execute(query)
            query_results = self.env.cr.dictfetchall()
            filt = []
            for result in query_results:
                filt.append(result['period_id'])

            tfilt = tuple(filt)
            args.append(['id', 'in', tfilt])

        res = super(BudgetPeriod, self)._search(args, offset=offset, limit=limit, order=order,
                                            count=count, access_rights_uid=access_rights_uid)

        return res

class BudgetSource(models.Model):
    _name = 'budgeting.source'

    name = fields.Char(string="Budget Source", required=True)
    description = fields.Text(string="Notes")
    active = fields.Boolean('Active', default=True)

class BudgetAppropriation(models.Model):
    _inherit = ['mail.thread']
    _name = 'budgeting.appropriation'
    _order = 'name desc'

    @api.depends('appdet_ids.amount')
    def _compute_amount(self):
        self.amount_total = sum(line.amount for line in self.appdet_ids)

    @api.model
    def create(self, vals):
        if vals['dyear'] == '2019':
            cde = 'budgeting.appropriation'
        else:
            cde = 'budgeting.appropriation' + vals['dyear']

        vals['name'] = self.env['ir.sequence'].next_by_code(cde)
        if not vals['name']:
            raise ValidationError(_('Sequence not set. Please contact the programmer.'))

        res = super(BudgetAppropriation, self).create(vals)

        return res

    def post(self):
        return self.write({'state': 'posted'})

    def draft(self):
        return self.write({'state': 'draft'})

    def approve(self):
        if self.date_approved:
            dte = self.date_approved
        else:
            dte = fields.Date.context_today(self)

        return self.write({'state': 'approved', 'date_approved':dte})

    def cancel(self):
        return self.write({'state': 'cancel'})

    def update_year(self):
        for rec in self:
            rec.dyear = rec.period_id.start_date[:4]

    name = fields.Char(string="Transaction Number", readonly=True)
    date = fields.Date(required=True, index=True, default=fields.Date.context_today)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Confirmed'),
        ('approved', 'Approved'),
        ('cancel', 'Cancelled')
        ], 'Status', readonly=True, track_visibility='onchange', copy=False, default='draft',
        )
    budgettype = fields.Selection([
        ('annual', 'Annual Budget'),
        ('supplemental', 'Supplemental Budget'),
        ('reappropriation', 'Reappropriation Budget')
        ], 'Budget Type', readonly=True,
        )
    partner_id = fields.Many2one('res.partner', string='Party', change_default=True,
        required=True, readonly=True, states={'draft': [('readonly', False)]},
        track_visibility='always')
    appdet_ids = fields.One2many('budgeting.appropriationdet', 'app_id', copy=False, ondelete='restrict')
    period_id = fields.Many2one('budgeting.period', string='Budget Specification', required=True, states={'draft': [('readonly', False)]})
    source_id = fields.Many2one('budgeting.source', string='Budget Source', required=True, states={'draft': [('readonly', False)]})
    amount_total = fields.Float(string='Total', store=True, readonly=True, compute='_compute_amount')
    date_approved = fields.Date(string='Date of Approval')
    dyear = fields.Char(string='Year', required=True, default=fields.Date.today().strftime('%Y'))
    company_id = fields.Many2one('res.company', required=True, readonly=True, default=lambda self: self.env.company)


class BudgetAppropriationDet(models.Model):
    _name = 'budgeting.appropriationdet'

    app_id = fields.Many2one('budgeting.appropriation', string="Appriation Details", copy=False)
    account_id = fields.Many2one('account.account', string='Account',
        required=True,
        domain=[('deprecated', '=', False)], help="The account used for this transaction.")
    amount = fields.Float(string='Amount', digits=0)

class BudgetPR(models.Model):
    _name = 'budgeting.pr'
    _inherit = ['mail.thread']
    _description = "Purchase Request"
    _order = 'name desc'

    @api.depends('prdet_ids.amount')
    def _compute_amount(self):
        self.amount_total = sum(line.amount for line in self.prdet_ids)

    @api.model
    def create(self, vals):
        if vals['dyear'] == '2019':
            cde = 'budgeting.pr'
        else:
            cde = 'budgeting.pr' + vals['dyear']

        vals['name'] = self.env['ir.sequence'].next_by_code(cde)
        if not vals['name']:
            raise ValidationError(_('Sequence not set. Please contact the programmer.'))

        res = super(BudgetPR, self).create(vals)

        return res

    def post(self):
        self.recalc()
        for rec in self:
            for recdet in rec.prdet_ids:
                if rec.date_approved:
                    dte = rec.date_approved
                else:
                    dte = fields.Date.context_today(self)
                xcurbal = cm._check_balance_pr(self, rec.partner_id.id, recdet.account_id.id, rec.period_id.id, dte, rec.source_id.id)

                xbal = xcurbal - recdet.amount

                if xbal < 0.0:
                    self.amount = 0.00
                    raise ValidationError(_("""Not enough budget for %s.
                                            Remaining budget is %s""") % (recdet.account_id.name, xcurbal))

        return self.write({'state': 'posted'})

    def recalc(self):
        for rec in self:
            for recdet in rec.prdet_ids:
                if rec.date_approved:
                    dte = rec.date_approved
                else:
                    dte = fields.Date.context_today(self)
                xcurbal = cm._check_balance_pr(self, rec.partner_id.id, recdet.account_id.id, rec.period_id.id, dte, rec.source_id.id)
                xbal = xcurbal - recdet.amount
                recdet.write({'currentbal':xcurbal, 'newbal':xbal})

        return

    def approve(self):
        if self.date_approved:
            dte = self.date_approved
        else:
            dte = fields.Date.context_today(self)

        self.recalc()
        return self.write({'state': 'approved', 'date_approved':dte})

    def cancel(self):
        return self.write({'state': 'cancel'})

    def draft(self):
        if self.state == 'obr':
            obr = self.env['budgeting.obr'].search([('pr_id', '=', self.id)])
            if obr and obr.state not in ('draft'):
                raise ValidationError(_("""%s should be in draft state.""") % (obr.name))

        self.recalc()
        return self.write({'state': 'draft'})


    def forobr(self):
        obr_obj = self.env['budgeting.obr']
        obr_objdet = self.env['budgeting.obrdet']
        dta_dict = {}
        for rec in self:
            dta_dict.update({
                'state': 'draft',
                'modeofentry': 'pr',
                'partner_id': rec.partner_id.id,
                'pr_id': rec.id,
                'purpose' : rec.purpose,
                'source_id' : rec.source_id.id,
                'dyear' : rec.dyear,
                'period_id': rec.period_id.id})

            chkr = obr_obj.search([('pr_id', '=', rec.id)])
            if not chkr:
                obr_id = obr_obj.create(dta_dict).id
            else:
                obr_id = chkr[0].id
                dets = obr_objdet.search([('obr_id', '=', obr_id)])
                for det in dets:
                    det.unlink()

            for recdet in rec.prdet_ids:
                dtadet_dict = {}
                dtadet_dict.update({
                'obr_id': obr_id,
                'account_id': recdet.account_id.id,
                'amount': recdet.amount})

                obr_objdet.create(dtadet_dict)

        return self.write({'state': 'obr'})

#     @api.depends('period_id')
#     @api.onchange('period_id')
#     def _getyear(self):
#         for rec in self:
#             if rec.period_id and rec.period_id.start_date:
#                 rec.dyear = rec.period_id.start_date[:4]


    def action_view_obr(self):
        self.ensure_one()
        action = self.env.ref('budgeting.budgetingobr_form_view')
        pr_id = self.id
        return {
            'name': action.name,
            'type': action.type,
            # 'view_type': action.view_type,
            # 'view_mode': action.view_mode,
            # 'target': action.target,
            'context': "{'default_pr_id': " + str(pr_id) + "}",
            'res_model': action.model,
            'domain': [('pr_id', '=', self.id)],
        }

    name = fields.Char(string="Transaction Number", readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Confirmed'),
        ('approved', 'Approved'),
        ('obr', 'Obligation Request'),
        ('cancel', 'Cancelled')
        ], 'Status', readonly=True, track_visibility='onchange', copy=False, default='draft',
        )
    date = fields.Date(required=True, index=True, default=fields.Date.context_today)
    partner_id = fields.Many2one('res.partner', string='Party', change_default=True,
        required=True, readonly=True, states={'draft': [('readonly', False)]},
        track_visibility='always')
    period_id = fields.Many2one('budgeting.period', string='Budget Specification',
        required=True, states={'draft': [('readonly', False)]})
    source_id = fields.Many2one('budgeting.source', string='Budget Source',
        required=True, states={'draft': [('readonly', False)]})
    prdet_ids = fields.One2many('budgeting.prdet', 'pr_id', copy=False, ondelete='restrict')
    amount_total = fields.Float(string='Total',
        store=True, readonly=True, compute='_compute_amount')
    purpose = fields.Text('Purpose')
    date_approved = fields.Date(string='Date of Approval')
    dyear = fields.Char(string='Year',required=True, default=fields.Date.today().strftime('%Y'))

    def update_year(self):
        for rec in self:
            rec.dyear = rec.period_id.start_date[:4]


class BudgetPRDet(models.Model):
    _name = 'budgeting.prdet'

    @api.onchange('amount', 'currentbal', 'newbal', 'account_id')
    def _onchange_action_amount(self):
        if self.pr_id.date_approved:
            dte = self.pr_id.date_approved
        else:
            dte = fields.Date.context_today(self)
        xcurbal = cm._check_balance_pr(self, self.pr_id.partner_id.id, self.account_id.id, self.pr_id.period_id.id, dte, self.pr_id.source_id.id)
        self.currentbal = xcurbal
        xbal = xcurbal - self.amount
        self.newbal = xbal

        return

#    @api.onchange('account_id')
#    def _onchange_account(self):

#        p_id = self.env.context.get('xpart')
#        period_id = self.env.context.get('xspec')
#        source_id = self.env.context.get('xsource')
#        dom = {}
#        if p_id and period_id and source_id:
#            query = """
#                        SELECT account_id
#                            FROM budgeting_appropriation
#                                inner join budgeting_appropriationdet on budgeting_appropriation.id = budgeting_appropriationdet.app_id
#                            WHERE budgeting_appropriation.state = 'approved'
#                            and budgeting_appropriation.partner_id = %s
#                            and budgeting_appropriation.period_id = %s
#                            and budgeting_appropriation.source_id <= %s
#                            ;
#                    """
#            self.env.cr.execute(query, (p_id, period_id, source_id))
#            print 'pass2'
#            query_results = self.env.cr.dictfetchall()
#            print query_results
#            filt = []
#            for result in query_results:
#                filt.append(result['account_id'])
#            print 'yyyy'
#            print tuple(filt)
#            acc_ids = self.env['account.account'].search([('id','in',filt)])
#            print filt
#            print 'acc', acc_ids
#            x = tuple(filt)
#            dom = {'domain': {'account_id':['id','in',x]}}

#        return True
    @api.model
    def create(self, vals):

        pr = self.env['budgeting.pr'].browse(vals['pr_id'])
        if pr.date_approved:
            dte = pr.date_approved
        else:
            dte = fields.Date.context_today(self)
        xcurbal = cm._check_balance_pr(self, pr.partner_id.id, vals['account_id'], pr.period_id.id, dte, pr.source_id.id)
        vals['currentbal'] = xcurbal
        vals['newbal'] = xcurbal - vals['amount']

        res = super(BudgetPRDet, self).create(vals)

        return res

    @api.model
    def write(self, vals):
        if self.pr_id.date_approved:
            dte = self.pr_id.date_approved
        else:
            dte = fields.Date.context_today(self)
        xcurbal = cm._check_balance_pr(self, self.pr_id.partner_id.id, self.account_id.id, self.pr_id.period_id.id, dte, self.pr_id.source_id.id)
        vals['currentbal'] = xcurbal

        amt = 0
        if 'amount' not in vals:
            amt = self.amount
        else:
            amt = vals['amount']

        vals['newbal'] = xcurbal - amt

        super(BudgetPRDet, self).write(vals)

        return True

    pr_id = fields.Many2one('budgeting.pr', string="Purchase Request", copy=False)
    account_id = fields.Many2one('account.account', string='Account',
        required=True,
        # domain=lambda self:self._get_account_list(),
        domain=[('deprecated', '=', False)],
        help="The account used for this transaction.")
    amount = fields.Float(string='Amount', digits=0)
    currentbal = fields.Float(string='Current Balance', digits=0, readonly=True)
    newbal = fields.Float(string='New Balance', digits=0, readonly=True)


class BudgetOBR(models.Model):
    _name = 'budgeting.obr'
    _inherit = ['mail.thread']
    _description = "Obligation Request"
    _order = 'name desc'

    @api.depends('obrdet_ids.amount')
    def _compute_amount(self):
        self.amount_total = sum(line.amount for line in self.obrdet_ids)

    @api.model
    def create(self, vals):
        if vals['dyear'] == '2019':
            cde = 'budgeting.obr'
        else:
            cde = 'budgeting.obr' + vals['dyear']

        vals['name'] = self.env['ir.sequence'].next_by_code(cde)
        if not vals['name']:
            raise ValidationError(_('Sequence not set. Please contact the programmer.'))

        res = super(BudgetOBR, self).create(vals)

        return res

    def post(self):
        self.recalc()
        for rec in self:
            for recdet in rec.obrdet_ids:
                if rec.date_approved:
                    dte = rec.date_approved
                else:
                    dte = fields.Date.context_today(self)
                xcurbal = cm._check_balance(self, rec.partner_id.id, recdet.account_id.id, rec.period_id.id, dte, rec.source_id.id)

                xbal = xcurbal - recdet.amount

                if xbal < 0.0:
                    self.amount = 0.00
                    raise ValidationError(_("""Not enough budget for %s.
                                            Remaining budget is %s""") % (recdet.account_id.name, xcurbal))


        return self.write({'state': 'posted'})

    def recalc(self):
        for rec in self:
            for recdet in rec.obrdet_ids:
                if rec.date_approved:
                    dte = rec.date_approved
                else:
                    dte = fields.Date.context_today(self)
                xcurbal = cm._check_balance(self, rec.partner_id.id, recdet.account_id.id, rec.period_id.id, dte, rec.source_id.id)
                xbal = xcurbal - recdet.amount

                recdet.write({'currentbal':xcurbal, 'newbal':xbal})

        return


    def approve(self):
        if self.date_approved:
            dte = self.date_approved
        else:
            dte = fields.Date.context_today(self)
        self.recalc()
        return self.write({'state': 'approved', 'date_approved':dte})


    def cancel(self):
        return self.write({'state': 'cancel'})


    def receive(self):
        return self.write({'acctg_received': True})


    def draft(self):
        self.recalc()
        return self.write({'state': 'draft'})

    name = fields.Char(string="Transaction Number", readonly=True)
    modeofentry = fields.Selection([
        ('manual', 'Manual Entry'),
        ('pr', 'From Purchase Request'),
        ], 'Mode of Entry', readonly=True, track_visibility='onchange', copy=False, default='manual',
        )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Confirmed'),
        ('approved', 'Approved'),
        ('cancel', 'Cancelled')
        ], 'Status', readonly=True, track_visibility='onchange', copy=False, default='draft',
        )
    acctg_received = fields.Boolean('Received', default=False, track_visibility='onchange')
    date = fields.Date(required=True, index=True, default=fields.Date.context_today)
    partner_id = fields.Many2one('res.partner', string='Party', change_default=True,
        required=True, readonly=True, states={'draft': [('readonly', False)]},
        track_visibility='always')
    period_id = fields.Many2one('budgeting.period', string='Budget Specification',
        required=True, states={'draft': [('readonly', False)]})
    source_id = fields.Many2one('budgeting.source', string='Budget Source',
        required=True, states={'draft': [('readonly', False)]})
    obrdet_ids = fields.One2many('budgeting.obrdet', 'obr_id', copy=False, ondelete='restrict')
    amount_total = fields.Float(string='Total',
        store=True, readonly=True, compute='_compute_amount')
    pr_id = fields.Many2one('budgeting.pr', string="Purchase Request Ref", copy=False)
    purpose = fields.Text('Purpose')
    date_approved = fields.Date(string='Date of Approval')
    payee = fields.Char(string="Payee")
    dyear = fields.Char(string='Year',required=True, default=fields.Date.today().strftime('%Y'))

    def update_year(self):
            rec.dyear = rec.period_id.start_date[:4]


class BudgetOBRDet(models.Model):
    _name = 'budgeting.obrdet'

    @api.onchange('amount', 'currentbal', 'newbal', 'account_id')
    def _onchange_action_amount(self):
        if self.obr_id.date_approved:
            dte = self.obr_id.date_approved
        else:
            dte = fields.Date.context_today(self)
        xcurbal = cm._check_balance(self, self.obr_id.partner_id.id, self.account_id.id, self.obr_id.period_id.id, dte, self.obr_id.source_id.id)
        self.currentbal = xcurbal
        xbal = xcurbal - self.amount
        self.newbal = xbal

        return

    @api.model
    def create(self, vals):

        pr = self.env['budgeting.obr'].browse(vals['obr_id'])
        if pr.date_approved:
            dte = pr.date_approved
        else:
            dte = fields.Date.context_today(self)
        xcurbal = cm._check_balance(self, pr.partner_id.id, vals['account_id'], pr.period_id.id, dte, pr.source_id.id)
        vals['currentbal'] = xcurbal
        vals['newbal'] = xcurbal - vals['amount']

        res = super(BudgetOBRDet, self).create(vals)

        return res

    @api.model
    def write(self, vals):
        if self.obr_id.date_approved:
            dte = self.obr_id.date_approved
        else:
            dte = fields.Date.context_today(self)
        xcurbal = cm._check_balance(self, self.obr_id.partner_id.id, self.account_id.id, self.obr_id.period_id.id, dte, self.obr_id.source_id.id)
        vals['currentbal'] = xcurbal

        amt = 0
        if 'amount' not in vals:
            amt = self.amount
        else:
            amt = vals['amount']

        vals['newbal'] = xcurbal - amt

        res = super(BudgetOBRDet, self).write(vals)

        return res


    obr_id = fields.Many2one('budgeting.obr', string="Obligation Request", copy=False)
    account_id = fields.Many2one('account.account', string='Account',
        required=True,
        domain=[('deprecated', '=', False)], help="The account used for this transaction.")
    amount = fields.Float(string='Amount', digits=0)
    currentbal = fields.Float(string='Current Balance', digits=0, readonly=True)
    newbal = fields.Float(string='New Balance', digits=0, readonly=True)

class BudgetAugmentation(models.Model):
    _name = 'budgeting.augmentation'
    _inherit = ['mail.thread']
    _description = "Budget Augmentation"
    _order = 'name desc'

    @api.depends('augdetfrom_ids.amount')
    def _compute_amount_from(self):
        self.amount_total_from = sum(line.amount for line in self.augdetfrom_ids)


    @api.depends('augdetto_ids.amount')
    def _compute_amount_to(self):
        self.amount_total_to = sum(line.amount for line in self.augdetto_ids)


    @api.model
    def create(self, vals):
        if vals['dyear'] == '2019':
            cde = 'budgeting.augmentation'
        else:
            cde = 'budgeting.augmentation' + vals['dyear']

        vals['name'] = self.env['ir.sequence'].next_by_code(cde)
        if not vals['name']:
            raise ValidationError(_('Sequence not set. Please contact the programmer.'))

        res = super(BudgetAugmentation, self).create(vals)

        return res


    def post(self):
        for rec in self:
            for recdet in rec.augdetfrom_ids:
                if rec.date_approved:
                    dte = rec.date_approved
                else:
                    dte = fields.Date.context_today(self)
                xcurbal = cm._check_balance(self, rec.partner_id.id, recdet.account_id.id, rec.period_id.id, dte, rec.source_id.id)

                xbal = xcurbal - recdet.amount

                if xbal < 0.0:
                    self.amount = 0.00
                    raise ValidationError(_("""Not enough budget for %s.
                                            Remaining budget is %s""") % (recdet.account_id.name, xcurbal))

        return self.write({'state': 'posted'})


    def recalc(self):
        for rec in self:
            for recdet in rec.augdetfrom_ids:
                if rec.date_approved:
                    dte = rec.date_approved
                else:
                    dte = fields.Date.context_today(self)
                xcurbal = cm._check_balance(self, rec.partner_id.id, recdet.account_id.id, rec.period_id.id, dte, rec.source_id.id)
                xbal = xcurbal - recdet.amount

                recdet.write({'currentbal':xcurbal, 'newbal':xbal})

            for recdet in rec.augdetto_ids:
                if rec.date_approved:
                    dte = rec.date_approved
                else:
                    dte = fields.Date.context_today(self)
                xcurbal = cm._check_balance(self, rec.partner_id.id, recdet.account_id.id, rec.period_id.id, dte, rec.source_id.id)
                xbal = xcurbal - recdet.amount

                recdet.write({'currentbal':xcurbal, 'newbal':xbal})
        return


    def approve(self):
        if self.date_approved:
            dte = self.date_approved
        else:
            dte = fields.Date.context_today(self)
        return self.write({'state': 'approved', 'date_approved':dte})

    def cancel(self):
        return self.write({'state': 'cancel'})

    def draft(self):
        return self.write({'state': 'draft'})


    name = fields.Char(string="Transaction Number", readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Confirmed'),
        ('approved', 'Approved'),
        ('cancel', 'Cancelled')
        ], 'Status', readonly=True, track_visibility='onchange', copy=False, default='draft',
        )
    date = fields.Date(required=True, index=True, default=fields.Date.context_today)
    partner_id = fields.Many2one('res.partner', string='Party', change_default=True,
        required=True, readonly=True, states={'draft': [('readonly', False)]},
        track_visibility='always')
    period_id = fields.Many2one('budgeting.period', string='Budget Specification',
        required=True, states={'draft': [('readonly', False)]})
    source_id = fields.Many2one('budgeting.source', string='Budget Source',
        required=True, states={'draft': [('readonly', False)]})
    augdetfrom_ids = fields.One2many('budgeting.augmentationdetfrom', 'aug_id', copy=False, ondelete='restrict')
    augdetto_ids = fields.One2many('budgeting.augmentationdetto', 'aug_id', copy=False, ondelete='restrict')
    amount_total_from = fields.Float(string='Total',
        store=True, readonly=True, compute='_compute_amount_from')
    amount_total_to = fields.Float(string='Total',
        store=True, readonly=True, compute='_compute_amount_to')
    purpose = fields.Text('Purpose')
    date_approved = fields.Date(string='Date of Approval')
#     dyear = fields.Char(string='Year',store=True, readonly=True, compute='_getyear')
    dyear = fields.Char(string='Year',required=True, default=fields.Date.today().strftime('%Y'))


    def update_year(self):
        for rec in self:
#             if not rec.dyear:
            rec.dyear = rec.period_id.start_date[:4]


#     @api.depends('period_id')
#     @api.onchange('period_id')
#     def _getyear(self):
#         for rec in self:
#             if rec.period_id and rec.period_id.start_date:
#                 rec.dyear = rec.period_id.start_date[:4]

class BudgetAugmentationDetFrom(models.Model):
    _name = 'budgeting.augmentationdetfrom'

    @api.onchange('amount', 'currentbal', 'newbal', 'account_id')
    def _onchange_action_amount(self):
        if self.aug_id.date_approved:
            dte = self.aug_id.date_approved
        else:
            dte = fields.Date.context_today(self)
        xcurbal = cm._check_balance(self, self.aug_id.partner_id.id, self.account_id.id, self.aug_id.period_id.id, dte, self.aug_id.source_id.id)
        self.currentbal = xcurbal
        xbal = xcurbal - self.amount
        self.newbal = xbal

        return

    @api.model
    def create(self, vals):

        pr = self.env['budgeting.augmentation'].browse(vals['aug_id'])
        if pr.date_approved:
            dte = pr.date_approved
        else:
            dte = fields.Date.context_today(self)
        xcurbal = cm._check_balance(self, pr.partner_id.id, vals['account_id'], pr.period_id.id, dte, pr.source_id.id)
        vals['currentbal'] = xcurbal
        vals['newbal'] = xcurbal - vals['amount']

        res = super(BudgetAugmentationDetFrom, self).create(vals)

        return res

    @api.model
    def write(self, vals):
        if self.aug_id.date_approved:
            dte = self.aug_id.date_approved
        else:
            dte = fields.Date.context_today(self)
        xcurbal = cm._check_balance(self, self.aug_id.partner_id.id, self.account_id.id, self.aug_id.period_id.id, dte, self.aug_id.source_id.id)
        vals['currentbal'] = xcurbal

        amt = 0
        if 'amount' not in vals:
            amt = self.amount
        else:
            amt = vals['amount']

        vals['newbal'] = xcurbal - amt

        res = super(BudgetAugmentationDetFrom, self).write(vals)

        return res


    aug_id = fields.Many2one('budgeting.augmentation', string="Budget Augmentation", copy=False)
    account_id = fields.Many2one('account.account', string='Account',
        required=True,
        domain=[('deprecated', '=', False)], help="The account used for this transaction.")
    currentbal = fields.Float(string='Current Balance', digits=0, readonly=True)
    amount = fields.Float(string='Amount', digits=0)
    newbal = fields.Float(string='New Balance', digits=0, readonly=True)

class BudgetAugmentationDetTo(models.Model):
    _name = 'budgeting.augmentationdetto'

    @api.onchange('amount', 'currentbal', 'newbal', 'account_id')
    def _onchange_action_amount(self):
        if self.aug_id.date_approved:
            dte = self.aug_id.date_approved
        else:
            dte = fields.Date.context_today(self)
        xcurbal = cm._check_balance(self, self.aug_id.partner_id.id, self.account_id.id, self.aug_id.period_id.id, dte, self.aug_id.source_id.id)
        self.currentbal = xcurbal
        xbal = xcurbal + self.amount
        self.newbal = xbal

        return

    @api.model
    def create(self, vals):

        pr = self.env['budgeting.augmentation'].browse(vals['aug_id'])

        if pr.date_approved:
            dte = pr.date_approved
        else:
            dte = fields.Date.context_today(self)
        xcurbal = cm._check_balance(self, pr.partner_id.id, vals['account_id'], pr.period_id.id, dte, pr.source_id.id)
        vals['currentbal'] = xcurbal

        vals['newbal'] = xcurbal + vals['amount']

        res = super(BudgetAugmentationDetTo, self).create(vals)

        return res

    @api.model
    def write(self, vals):
        if self.aug_id.date_approved:
            dte = self.aug_id.date_approved
        else:
            dte = fields.Date.context_today(self)
        xcurbal = cm._check_balance(self, self.aug_id.partner_id.id, self.account_id.id, self.aug_id.period_id.id, dte, self.aug_id.source_id.id)
        vals['currentbal'] = xcurbal
        amt = 0
        if 'amount' not in vals:
            amt = self.amount
        else:
            amt = vals['amount']

        vals['newbal'] = xcurbal + amt

        res = super(BudgetAugmentationDetTo, self).write(vals)

        return res

    aug_id = fields.Many2one('budgeting.augmentation', string="Budget Augmentation", copy=False)
    account_id = fields.Many2one('account.account', string='Account',
        required=True,
        domain=[('deprecated', '=', False)], help="The account used for this transaction.")
    currentbal = fields.Float(string='Current Balance', digits=0, readonly=True)
    amount = fields.Float(string='Amount', digits=0)
    newbal = fields.Float(string='New Balance', digits=0, readonly=True)

class Account(models.Model):
    _inherit = 'account.account'

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):

        p_id = self.env.context.get('xpart')
        period_id = self.env.context.get('xspec')
        source_id = self.env.context.get('xsource')
        if p_id and period_id and source_id:
            query = """
                        SELECT account_id
                            FROM budgeting_appropriation
                                inner join budgeting_appropriationdet on budgeting_appropriation.id = budgeting_appropriationdet.app_id
                            WHERE budgeting_appropriation.state = 'approved'
                            and budgeting_appropriation.partner_id = %s
                            and budgeting_appropriation.period_id = %s
                            and budgeting_appropriation.source_id <= %s
                            ;
                    """
            self.env.cr.execute(query, (p_id, period_id, source_id))
            query_results = self.env.cr.dictfetchall()
            filt = []
            for result in query_results:
                filt.append(result['account_id'])

            tfilt = tuple(filt)
            args.append(['id', 'in', tfilt])

        filter_account = self.env.context.get('filter_account')
        if filter_account:
            query = """
                        SELECT distinct budgeting_appropriationdet.account_id
                            FROM budgeting_appropriation
                                inner join budgeting_appropriationdet on budgeting_appropriation.id = budgeting_appropriationdet.app_id
                            WHERE budgeting_appropriation.state = 'approved'
                            ;
                    """
            self.env.cr.execute(query)
            query_results = self.env.cr.dictfetchall()
            filt = []
            for result in query_results:
                filt.append(result['account_id'])

            tfilt = tuple(filt)
            args.append(['id', 'in', tfilt])

        res = super(Account, self)._search(args, offset=offset, limit=limit, order=order,
                                            count=count, access_rights_uid=access_rights_uid)

        return res

class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        filter_partner = self.env.context.get('filter_partner')
        if filter_partner:
            query = """
                        SELECT partner_id
                            FROM budgeting_appropriation
                                inner join budgeting_appropriationdet on budgeting_appropriation.id = budgeting_appropriationdet.app_id
                            WHERE budgeting_appropriation.state = 'approved'
                            ;
                    """
            self.env.cr.execute(query)
            query_results = self.env.cr.dictfetchall()
            filt = []
            for result in query_results:
                filt.append(result['partner_id'])

            tfilt = tuple(filt)
            args.append(['id', 'in', tfilt])

        filter_partner2 = self.env.context.get('filter_partner2')
        if filter_partner2:
            source_id = self.env.context.get('source_id') or 0
            query = """
                        SELECT partner_id
                            FROM budgeting_appropriation
                                inner join budgeting_appropriationdet on budgeting_appropriation.id = budgeting_appropriationdet.app_id
                            WHERE budgeting_appropriation.state = 'approved'
                            and source_id = %s
                            ;
                    """ % (source_id)
            self.env.cr.execute(query)
            query_results = self.env.cr.dictfetchall()
            filt = []
            for result in query_results:
                filt.append(result['partner_id'])

            tfilt = tuple(filt)
            args.append(['id', 'in', tfilt])

        res = super(ResPartner, self)._search(args, offset=offset, limit=limit, order=order,
                                            count=count, access_rights_uid=access_rights_uid)

        return res

