# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime
#from gdata.contentforshopping.data import Condition

class BudgetingSummary(models.TransientModel):
    _name = "budgeting.summary"
    _description = "Budgeting Summary"

    source_ids = fields.Many2many('budgeting.source', string='Budget Source', default=lambda self: self.env['budgeting.source'].search([]))
    period_ids = fields.Many2many('budgeting.period', string='Budget Specifications', default=lambda self: self.env['budgeting.period'].search([]))
    date_to = fields.Date(string='As Of')
    dyear = fields.Char(string='Year')
    rep_ids = fields.One2many('budgeting.app.stmt.wizard.summary', 'rep_id')
    period_fill = fields.Boolean('Fill Budget Specs', default=True)
    source_fill = fields.Boolean('Fill Source', default=True)
    
    def _build_contexts(self, data):
        result = {}
        result['source_ids'] = 'source_ids' in data['form'] and data['form']['source_ids'] or False
        result['period_ids'] = 'period_ids' in data['form'] and data['form']['period_ids'] or False
        result['date_to'] = data['form']['date_to'] or False
        result['dyear'] = data['form']['dyear'] or False
        return result

    @api.onchange('source_fill')
    def onchange_source_fill(self):
        for rec in self:
            if rec.source_fill:
                rec.source_ids = self.env['budgeting.source'].search([])
            else:
                rec.source_ids = self.env['budgeting.source'].search([('id', '=', 0)])

    @api.onchange('period_fill','source_ids')
    def onchange_period_fill(self):
        for rec in self:
            if rec.period_fill:
                if rec.dyear:
                    srch = [('dyear', '=', rec.dyear)]
                    if self.source_ids:
                        prd_ids = self.env['budgeting.appropriation'].search([('source_id', 'in', rec.source_ids._ids)])
                        if prd_ids:
                            srch += [('id', 'in', prd_ids.mapped('period_id')._ids)]
                    self.period_ids = self.env['budgeting.period'].search(srch)
                    
                else:
                    self.period_ids = self.env['budgeting.period'].search([])
            else:
                self.period_ids = self.env['budgeting.period'].search([('id', '=', 0)])

    @api.onchange('dyear')
    def onchange_dyear(self):
        for rec in self:
            if rec.dyear:
                self.period_ids = self.env['budgeting.period'].search([('dyear','=',rec.dyear)])
            else:
                self.period_ids = self.env['budgeting.period'].search([])

    def _print_report(self, data):
        #data = self.pre_print_report(data)
        #data['form'].update(self.read(['initial_balance', 'sortby'])[0])
        #if data['form'].get('initial_balance') and not data['form'].get('date_from'):
        #    raise UserError(_("You must define a Start Date"))
        #records = self.env[data['model']].browse(data.get('ids', []))
        #return self.env['report'].with_context(landscape=True).get_action(records, 'budgeting.appstmt_report_viewnew', data=data)
        # return self.env['report'].get_action(self, 'budgeting.appstmt_report_summary', data=data)

        return self.env.ref('budgeting.appstmt_summary').report_action(self, data=data)
        
    def check_report(self):
        self.ensure_one()
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(['source_ids', 'period_ids', 'date_to','dyear'])[0]
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context, lang=self.env.context.get('lang') or 'en_US')
        return self._print_report(data)

    def group_source(self):
        res = []
        sql = """ 
            SELECT distinct source_id 
            FROM budgeting_app_stmt_wizard_summary det
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
            FROM budgeting_app_stmt_wizard_summary det
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
            FROM budgeting_app_stmt_wizard_summary det
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
            FROM budgeting_app_stmt_wizard_summary det
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

class AppStmtWizardSummary(models.TransientModel):
    _name = "budgeting.app.stmt.wizard.summary"
    _description = "Appropriation Summary"

    rep_id = fields.Many2one('budgeting.summary', string="Report", copy=False)
    allotment = fields.Float(string='Allotment', digits=0)
    incurred = fields.Float(string='Incurred', digits=0)
    actbal = fields.Float(string='Actual Balance', digits=0)
    period_id = fields.Many2one('budgeting.period', string='Budget Specification',
        required=True)
    source_id = fields.Many2one('budgeting.source', string='Budget Source',
        required=True)

    
class AppStmtReportSummary(models.AbstractModel):
    """Abstract Model for report template.
    for `_name` model, please use `report.` as prefix then add `module_name.report_name`.
    """

    _name = "report.budgeting.appstmt_report_summary"

    @api.model
    def render_html(self, docids, data=None):
        self.model = self.env.context.get('active_model')
        self.get_report_values(self.env.context.get('active_id'),data)
        docs = self.env['budgeting.summary'].browse(self.env.context.get('active_id'))
        docargs = {
            'doc_ids': self.ids,
            'doc_model': self.model,
            'docs': docs,
        }

        # return self.env['report'].render('budgeting.appstmt_report_summary', docargs)

        return self.env.ref('budgeting.appstmt_summary').report_action(self, data=data)

    @api.model
    def _get_report_values(self, docids, data=None):
        #dateto = datetime.strptime(data['form']['date_to'],'%Y-%m-%d').date()
        dateto = data['form']['date_to']
        period_id = data['form']['period_ids']
        source_id = data['form']['source_ids']

        cond = ''
        if period_id:
            if len(period_id) == 1:
                cond += ' and period_id = %s' % str(period_id[0])
            else:    
                cond += ' and period_id in %s' % str(tuple(period_id)) 
        if source_id:
            if len(source_id) == 1:
                cond += ' and source_id = %s' % str(source_id[0])
            else:
                cond += ' and source_id in %s' % str(tuple(source_id)) 
        cond += " and date_approved <= '" + dateto + "'::date "
        cond2 = ''
        if period_id:
            if len(period_id) == 1:
                cond2 += ' and budgeting_obr.period_id = %s' % str(period_id[0])
            else:    
                cond2 += ' and budgeting_obr.period_id in %s' % str(tuple(period_id)) 
        if source_id:
            if len(source_id) == 1:
                cond2 += ' and budgeting_obr.source_id = %s' % str(source_id[0])
            else:
                cond2 += ' and budgeting_obr.source_id in %s' % str(tuple(source_id))
        cond2 += " and budgeting_obr.date_approved <= '" + dateto + "'::date "
                
        docs = []
        query = ("""
                select source_id, period_id, sum(allotment) as allotment, sum(incurred) as incurred,
                    sum(allotment-incurred) as balance
                from 
                    (SELECT 'APP' source, budgeting_appropriationdet.amount, 
                                budgeting_appropriationdet.amount allotment, 0.00 incurred, 
                                budgeting_appropriation.source_id,
                                budgeting_appropriation.period_id, budgeting_appropriation.name, budgeting_appropriation.id, budgeting_appropriationdet.id as id2
                        FROM budgeting_appropriation 
                            inner join budgeting_appropriationdet on budgeting_appropriation.id = budgeting_appropriationdet.app_id  
                        WHERE budgeting_appropriation.state = 'approved'
                """ + cond + """ 
                    union  
                    SELECT 'OBR' source, budgeting_obrdet.amount, 
                                0.00 allotment, budgeting_obrdet.amount incurred, 
                                budgeting_obr.source_id,
                                budgeting_obr.period_id, budgeting_obr.name, budgeting_obr.id, budgeting_obrdet.id as id2
                        FROM budgeting_obr 
                            inner join budgeting_obrdet on budgeting_obr.id = budgeting_obrdet.obr_id
                            left outer join budgeting_pr on budgeting_pr.id = budgeting_obr.pr_id
                        WHERE budgeting_obr.state = 'approved'
                    """ + cond2 +
                    """ 
                    union    
                    SELECT 'AUF' source, budgeting_augmentationdetfrom.amount amount, 
                                -budgeting_augmentationdetfrom.amount allotment, 0.00 incurred, 
                                budgeting_augmentation.source_id,
                                budgeting_augmentation.period_id, budgeting_augmentation.name, budgeting_augmentation.id, budgeting_augmentationdetfrom.id as id2 
                        FROM budgeting_augmentation 
                            inner join budgeting_augmentationdetfrom on budgeting_augmentation.id = budgeting_augmentationdetfrom.aug_id  
                        WHERE budgeting_augmentation.state = 'approved'
                    """ + cond +
                    """ 
                    union
                    SELECT 'AUT' source, budgeting_augmentationdetto.amount, 
                                budgeting_augmentationdetto.amount allotment, 0.00 incurred, 
                                budgeting_augmentation.source_id,
                                budgeting_augmentation.period_id, budgeting_augmentation.name, budgeting_augmentation.id, budgeting_augmentationdetto.id as id2 
                        FROM budgeting_augmentation 
                            inner join budgeting_augmentationdetto on budgeting_augmentation.id = budgeting_augmentationdetto.aug_id  
                        WHERE budgeting_augmentation.state = 'approved'
                    """ + cond +
                    """ 
                    order by source_id, period_id) as src
                    group by source_id, period_id 
                        ;
                """)

        #self.env.cr.execute(query, (cond,dateto,cond,dateto,cond,dateto,cond,dateto,cond,dateto))
        self.env.cr.execute(query, (cond,cond,cond,cond,cond))
        query_results = self.env.cr.dictfetchall()
        self.env["budgeting.app.stmt.wizard.summary"].search([('rep_id','=',self.env.context.get('active_id'))]).unlink()
        
        rep_obj = self.env['budgeting.app.stmt.wizard.summary']
        for res in query_results:
            
            dtadet_dict = {}
            dtadet_dict.update({
            'rep_id': self.env.context.get('active_id'),
            'allotment': res['allotment'],
            'incurred': res['incurred'],
            'actbal': res['balance'],
            'source_id': res['source_id'],
            'period_id': res['period_id']})

            rep_obj.create(dtadet_dict)
    
        model = self.env.context.get('active_model')
        docs = self.env['budgeting.summary'].browse(self.env.context.get('active_id'))
        docargs = {
            'doc_ids': self.ids,
            'doc_model': model,
            'docs': docs,
        }

        return docargs