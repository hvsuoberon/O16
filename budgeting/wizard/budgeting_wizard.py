# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime
# from gdata.contentforshopping.data import Condition

class BudgetingReport(models.TransientModel):
    _name = "budgeting.report"
    _description = "Budgeting Report"

    source_ids = fields.Many2many('budgeting.source', string='Budget Source', default=lambda self: self.env['budgeting.source'].search([]))
    party_ids = fields.Many2many('res.partner', string='Partners', default=lambda self: self.env['res.partner'].search([]))
    period_ids = fields.Many2many('budgeting.period', string='Budget Specifications', default=lambda self: self.env['budgeting.period'].search([]))
    account_ids = fields.Many2many('account.account', string='Account Titles', default=lambda self: self.env['account.account'].search([]))
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
    dyear = fields.Char(string='Year')
    rep_ids = fields.One2many('budgeting.app.stmt.wizard.detnew', 'rep_id')
    acc_fill = fields.Boolean('Fill Accounts', default=True)
    period_fill = fields.Boolean('Fill Budget Specs', default=True)
    source_fill = fields.Boolean('Fill Budget Source', default=True)
    party_fill = fields.Boolean('Fill Party', default=True)
    
    def _build_contexts(self, data):
        result = {}
        result['source_ids'] = 'source_ids' in data['form'] and data['form']['source_ids'] or False
        result['party_ids'] = 'party_ids' in data['form'] and data['form']['party_ids'] or False
        result['period_ids'] = 'period_ids' in data['form'] and data['form']['period_ids'] or False
        result['account_ids'] = 'account_ids' in data['form'] and data['form']['account_ids'] or False
        result['date_to'] = data['form']['date_to'] or False
        result['date_from'] = data['form']['date_from'] or False
        result['dyear'] = data['form']['dyear'] or False
        return result

    @api.onchange('dyear')
    def onchange_dyear(self):
        for rec in self:
            if rec.dyear:
                self.period_ids = self.env['budgeting.period'].search([('dyear', '=', rec.dyear)])
            else:
                self.period_ids = self.env['budgeting.period'].search([])

    @api.onchange('acc_fill')
    def onchange_acc_fill(self):
        for rec in self:
            if rec.acc_fill:
                rec.account_ids = self.env['account.account'].search([])
            else:
                rec.account_ids = self.env['account.account'].search([('id', '=', 0)])

    @api.onchange('period_fill')
    def onchange_period_fill(self):
        for rec in self:
            if rec.period_fill:
                if rec.dyear:
                    self.period_ids = self.env['budgeting.period'].search([('dyear', '=', rec.dyear)])
                else:
                    self.period_ids = self.env['budgeting.period'].search([])
            else:
                self.period_ids = self.env['budgeting.period'].search([('id', '=', 0)])

    @api.onchange('source_fill')
    def onchange_source_fill(self):
        for rec in self:
            if rec.source_fill:
                self.source_ids = self.env['budgeting.source'].search([])
            else:
                self.source_ids = self.env['budgeting.source'].search([('id', '=', 0)])
                
    @api.onchange('party_fill')
    def onchange_party_fill(self):
        for rec in self:
            if rec.party_fill:
                self.party_ids = self.env['res.partner'].search([])
            else:
                self.party_ids = self.env['res.partner'].search([('id', '=', 0)])                
                
    def _print_report(self, data):
        # data = self.pre_print_report(data)
        # data['form'].update(self.read(['initial_balance', 'sortby'])[0])
        # if data['form'].get('initial_balance') and not data['form'].get('date_from'):
        #    raise UserError(_("You must define a Start Date"))
        # records = self.env[data['model']].browse(data.get('ids', []))
        # return self.env['report'].with_context(landscape=True).get_action(records, 'budgeting.appstmt_report_viewnew', data=data)

        return self.env.ref('budgeting.appstmt_reportnew').report_action(self, data=data)

    def check_report(self):
        self.ensure_one()
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(['source_ids', 'period_ids', 'party_ids', 'account_ids', 'date_to', 'date_from', 'dyear'])[0]
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context, lang=self.env.context.get('lang') or 'en_US')
        return self._print_report(data)

    def group_source(self):
        res = []
        sql = """ 
            SELECT distinct source_id 
            FROM budgeting_app_stmt_wizard_detnew det
            where rep_id = %s  
              """ % (self.env.context.get('active_id'))
              
        self.env.cr.execute(sql)
        query_results = self.env.cr.dictfetchall()
        for rec in query_results:
            res.append(rec['source_id'])
        res = self.env['budgeting.source'].browse(res)
        return res 

    def group_partner(self, source_id):
        res = []
        sql = """ 
            SELECT distinct partner_id 
            FROM budgeting_app_stmt_wizard_detnew det
            where rep_id = %s  
            and source_id = %s 
              """ % (self.env.context.get('active_id'), source_id)
              
        self.env.cr.execute(sql)
        query_results = self.env.cr.dictfetchall()
        for rec in query_results:
            res.append(rec['partner_id'])
        res = self.env['res.partner'].browse(res)
        return res 
    
    def group_specs(self, source_id, partner_id):
        res = []
        sql = """ 
            SELECT distinct period_id 
            FROM budgeting_app_stmt_wizard_detnew det
            where rep_id = %s  
            and source_id = %s 
            and partner_id = %s
              """ % (self.env.context.get('active_id'), source_id, partner_id)
              
        self.env.cr.execute(sql)
        query_results = self.env.cr.dictfetchall()
        for rec in query_results:
            res.append(rec['period_id'])
        res = self.env['budgeting.period'].browse(res)
        return res 

    def group_account(self, source_id, partner_id, period_id):
        res = []
        sql = """ 
            SELECT distinct account_id 
            FROM budgeting_app_stmt_wizard_detnew det
            where rep_id = %s  
            and source_id = %s 
            and partner_id = %s
            and period_id = %s
              """ % (self.env.context.get('active_id'), source_id, partner_id, period_id)
              
        self.env.cr.execute(sql)
        query_results = self.env.cr.dictfetchall()
        for rec in query_results:
            res.append(rec['account_id'])
        res = self.env['account.account'].browse(res)
        return res

    def get_begbal(self, source_id, partner_id, period_id, account_id):
        srch_begbal = self.env['budgeting.app.stmt.wizard.detnew'].search([('rep_id', '=', self.env.context.get('active_id')),
                                                                           ('source_id', '=', source_id), 
                                                                           ('partner_id', '=', partner_id), 
                                                                           ('period_id', '=', period_id), 
                                                                           ('account_id', '=', account_id),
                                                                           ('date_approved','<',self.date_from)], order='id desc', limit=1)
        
        res = self.env['budgeting.app.stmt.wizard.detnew'].browse(srch_begbal.ids)
        return res

    def get_detail(self, source_id, partner_id, period_id, account_id):
        srch_det = self.env['budgeting.app.stmt.wizard.detnew'].search([('rep_id', '=', self.env.context.get('active_id')),
                                                                           ('source_id', '=', source_id), 
                                                                           ('partner_id', '=', partner_id), 
                                                                           ('period_id', '=', period_id), 
                                                                           ('account_id', '=', account_id),
                                                                           ('date_approved','>=',self.date_from)], order='id')

        res = self.env['budgeting.app.stmt.wizard.detnew'].browse(srch_det.ids)
        return res



class AppStmtWizardDet(models.TransientModel):
    _name = "budgeting.app.stmt.wizard.detnew"
    _description = "Appropriation Statement Report Details"

    rep_id = fields.Many2one('budgeting.report', string="Report", copy=False)
    amount = fields.Float(string='Amount', digits=0)   
    date = fields.Date(string='Transaction Date')
    date_approved = fields.Date(string='Date of Approval')
    reference = fields.Char(string='Reference')
    particulars = fields.Char(string='Particulars')
    allotment = fields.Float(string='Allotment', digits=0)
    incurred = fields.Float(string='Incurred', digits=0)
    tempres = fields.Float(string='Reserves', digits=0)
    tempbal = fields.Float(string='Temp Balance', digits=0)
    actamount = fields.Float(string='Actual Amount', digits=0)
    actbal = fields.Float(string='Actual Balance', digits=0)
    partner_id = fields.Many2one('res.partner', string='Party', change_default=True,
        required=True)    
    period_id = fields.Many2one('budgeting.period', string='Budget Specification',
        required=True)
    account_id = fields.Many2one('account.account', string='Account',
        required=True,
        domain=[('deprecated', '=', False)], help="The account used for this transaction.")
    source_id = fields.Many2one('budgeting.source', string='Budget Source',
        required=True)

    
class AppStmtReportNew(models.AbstractModel):
    """Abstract Model for report template.
    for `_name` model, please use `report.` as prefix then add `module_name.report_name`.
    """

    _name = "report.budgeting.appstmt_report_viewnew"

    @api.model
    def render_html(self, docids, data=None):
        self.model = self.env.context.get('active_model')
        self.get_report_values(self.env.context.get('active_id'), data)
        docs = self.env['budgeting.report'].browse(self.env.context.get('active_id'))
        docargs = {
            'doc_ids': self.ids,
            'doc_model': self.model,
            'docs': docs,
        }

        # return self.env['report'].render('budgeting.appstmt_report_viewnew', docargs)

        return self.env.ref('budgeting.appstmt_reportnew').report_action(self, data=data)

    @api.model
    def _get_report_values(self, docids, data=None):
        # dateto = datetime.strptime(data['form']['date_to'],'%Y-%m-%d').date()
        dateto = data['form']['date_to']
        datefrom = data['form']['date_from']
        p_id = data['form']['party_ids']
        period_id = data['form']['period_ids']
        acc_id = data['form']['account_ids']
        source_id = data['form']['source_ids']

        cond = ''
        cond_a = ''
        if p_id:
            if len(p_id) == 1:
                cond += ' and partner_id = %s' % str(p_id[0])
                cond_a += ' and budgeting_pr.partner_id = %s' % str(p_id[0])
            else: 
                cond += ' and partner_id in %s' % str(tuple(p_id))
                cond_a += ' and budgeting_pr.partner_id in %s' % str(tuple(p_id))
        if period_id:
            if len(period_id) == 1:
                cond += ' and period_id = %s' % str(period_id[0])
                cond_a += ' and budgeting_pr.period_id = %s' % str(period_id[0])
            else:    
                cond += ' and period_id in %s' % str(tuple(period_id))
                cond_a += ' and budgeting_pr.period_id in %s' % str(tuple(period_id))
        if acc_id:
            if len(acc_id) == 1:
                cond += ' and account_id = %s' % str(acc_id[0])
                cond_a += ' and account_id = %s' % str(acc_id[0])
            else:
                cond += ' and account_id in %s' % str(tuple(acc_id))
                cond_a += ' and account_id in %s' % str(tuple(acc_id))
        if source_id:
            if len(source_id) == 1:
                cond += ' and source_id = %s' % str(source_id[0])
                cond_a += ' and budgeting_pr.source_id = %s' % str(source_id[0])
            else:
                cond += ' and source_id in %s' % str(tuple(source_id))
                cond_a += ' and budgeting_pr.source_id in %s' % str(tuple(source_id))

        cond += " and date_approved <= '" + dateto + "'::date "
        cond_a += " and budgeting_pr.date_approved <= '" + dateto + "'::date "
#         cond += " and date_approved >= '" + datefrom + "'::date "        
        cond2 = ''
        if p_id:
            if len(p_id) == 1:
                cond2 += ' and budgeting_obr.partner_id = %s' % str(p_id[0])
            else: 
                cond2 += ' and budgeting_obr.partner_id in %s' % str(tuple(p_id))     
        if period_id:
            if len(period_id) == 1:
                cond2 += ' and budgeting_obr.period_id = %s' % str(period_id[0])
            else:    
                cond2 += ' and budgeting_obr.period_id in %s' % str(tuple(period_id)) 
        if acc_id:
            if len(acc_id) == 1:
                cond2 += ' and budgeting_obrdet.account_id = %s' % str(acc_id[0])
            else:
                cond2 += ' and budgeting_obrdet.account_id in %s' % str(tuple(acc_id)) 
        if source_id:
            if len(source_id) == 1:
                cond2 += ' and budgeting_obr.source_id = %s' % str(source_id[0])
            else:
                cond2 += ' and budgeting_obr.source_id in %s' % str(tuple(source_id))
        cond2 += " and budgeting_obr.date_approved <= '" + dateto + "'::date "
#         cond2 += " and budgeting_obr.date_approved >= '" + datefrom + "'::date "
                
        docs = []
        query = ("""
                    SELECT 'APP' source, budgeting_appropriationdet.amount, 
                                budgeting_appropriation.date, budgeting_appropriation.name,
                                budgeting_appropriation.date_approved, concat(initcap(budgettype),' Budget') purpose,
                                budgeting_appropriationdet.amount allotment, 0.00 incurred, 1 srtorder, 
                                budgeting_appropriation.source_id,
                                budgeting_appropriation.partner_id,
                                budgeting_appropriation.period_id,
                                budgeting_appropriationdet.account_id       
                        FROM budgeting_appropriation 
                            inner join budgeting_appropriationdet on budgeting_appropriation.id = budgeting_appropriationdet.app_id  
                        WHERE budgeting_appropriation.state = 'approved'
                """ + cond + """ 
                    union
                    SELECT 'PR' source, budgeting_prdet.amount, 
                                budgeting_pr.date, budgeting_pr.name,
                                budgeting_pr.date_approved, case when budgeting_obr.name is not Null then
                                        concat('***',budgeting_pr.purpose) 
                                    else budgeting_pr.purpose end as purpose,
                                0.00 allotment, budgeting_prdet.amount incurred, 3 srtorder, 
                                budgeting_pr.source_id,
                                budgeting_pr.partner_id,
                                budgeting_pr.period_id,
                                budgeting_prdet.account_id    
                        FROM budgeting_pr 
                            inner join budgeting_prdet on budgeting_pr.id = budgeting_prdet.pr_id  
                            left outer join budgeting_obr on budgeting_pr.id = budgeting_obr.pr_id  
                        WHERE budgeting_pr.state in ('approved','obr')
                    """ + cond_a +
                    """ 
                    union  
                    SELECT 'OBR' source, budgeting_obrdet.amount, 
                                budgeting_obr.date, budgeting_obr.name,
                                budgeting_obr.date_approved, 
                                    case when budgeting_pr.name is not Null then
                                        concat('*From ',budgeting_pr.name,' - ',budgeting_obr.purpose) 
                                    else concat('From ',' - ',budgeting_obr.purpose) end as purpose,
                                0.00 allotment, budgeting_obrdet.amount incurred, 4 srtorder, 
                                budgeting_obr.source_id,
                                budgeting_obr.partner_id,
                                budgeting_obr.period_id,
                                budgeting_obrdet.account_id
                        FROM budgeting_obr 
                            inner join budgeting_obrdet on budgeting_obr.id = budgeting_obrdet.obr_id
                            left outer join budgeting_pr on budgeting_pr.id = budgeting_obr.pr_id
                        WHERE budgeting_obr.state = 'approved'
                    """ + cond2 + 
                    """ 
                    union    
                    SELECT 'AUF' source, budgeting_augmentationdetfrom.amount amount, 
                                budgeting_augmentation.date, budgeting_augmentation.name,
                                budgeting_augmentation.date_approved, budgeting_augmentation.purpose, 
                                0.00 allotment, budgeting_augmentationdetfrom.amount incurred, 5 srtorder, 
                                budgeting_augmentation.source_id,
                                budgeting_augmentation.partner_id,
                                budgeting_augmentation.period_id,
                                budgeting_augmentationdetfrom.account_id 
                        FROM budgeting_augmentation 
                            inner join budgeting_augmentationdetfrom on budgeting_augmentation.id = budgeting_augmentationdetfrom.aug_id  
                        WHERE budgeting_augmentation.state = 'approved'
                    """ + cond + 
                    """ 
                    union
                    SELECT 'AUT' source, budgeting_augmentationdetto.amount, 
                                budgeting_augmentation.date, budgeting_augmentation.name,
                                budgeting_augmentation.date_approved, budgeting_augmentation.purpose,
                                budgeting_augmentationdetto.amount allotment, 0.00 incurred, 2 srtorder, 
                                budgeting_augmentation.source_id,
                                budgeting_augmentation.partner_id,
                                budgeting_augmentation.period_id,
                                budgeting_augmentationdetto.account_id 
                        FROM budgeting_augmentation 
                            inner join budgeting_augmentationdetto on budgeting_augmentation.id = budgeting_augmentationdetto.aug_id  
                        WHERE budgeting_augmentation.state = 'approved'
                    """ + cond + 
                    """ 
                    order by source_id, partner_id, period_id, account_id, date_approved, srtorder, name 
                        ;
                """)

        # self.env.cr.execute(query, (cond,dateto,cond,dateto,cond,dateto,cond,dateto,cond,dateto))
        self.env.cr.execute(query, (cond, cond, cond, cond, cond))
        query_results = self.env.cr.dictfetchall()

        self.env["budgeting.app.stmt.wizard.detnew"].search([('rep_id', '=', self.env.context.get('active_id'))]).unlink()
        
        temp_balance = 0.00 
        act_balance = 0.00
        run_source = 0
        run_partner = 0
        run_specs = 0
        run_account = 0
               
        rep_obj = self.env['budgeting.app.stmt.wizard.detnew']

        for res in query_results:
            
            temp_reserves = 0.00
            act_amount = 0.00

            if not (run_source == res['source_id'] and run_partner == res['partner_id']
                            and run_specs == res['period_id']
                            and run_account == res['account_id']):
                temp_balance = 0.00 
                act_balance = 0.00
 
            run_source = res['source_id']
            run_partner = res['partner_id']
            run_specs = res['period_id']
            run_account = res['account_id']
            
            if res['source'] == 'APP':
                act_balance += res['amount']
                temp_balance += res['amount']
            if res['source'] == 'PR':
                if res['purpose'] and res['purpose'][:3] == '***':
                    temp_reserves = 0
                else:
                    temp_reserves = -res['amount']
                    temp_balance -= res['amount']
            if res['source'] == 'OBR':
                # if res['purpose'][:8] != '*From PR':
                temp_reserves = -res['amount']
                temp_balance -= res['amount']
                act_amount = -res['amount']
                act_balance -= res['amount']
            if res['source'] == 'AUF':
                temp_reserves = -res['amount']
                temp_balance -= res['amount']
                act_amount = -res['amount']
                act_balance -= res['amount']
            if res['source'] == 'AUT':
                act_balance += res['amount']
                temp_balance += res['amount']
                
            dtadet_dict = {}
            dtadet_dict.update({
            'rep_id': self.env.context.get('active_id'),
            'reference' : res['name'],
            'particulars' : res['purpose'],
            'date': res['date'],
            'date_approved': res['date_approved'],
            'allotment': res['allotment'],
            'incurred': res['incurred'],
            'tempres': temp_reserves,
            'tempbal': temp_balance,
            'actamount': act_amount,
            'actbal': act_balance,
            'source_id': res['source_id'],
            'partner_id': res['partner_id'],
            'period_id': res['period_id'],
            'account_id': res['account_id'],
            'amount': res['amount']})

            rep_obj.create(dtadet_dict)
    
        model = self.env.context.get('active_model')
        docs = self.env['budgeting.report'].browse(self.env.context.get('active_id'))
        docargs = {
            'doc_ids': self.ids,
            'doc_model': model,
            'docs': docs,
        }

        return docargs