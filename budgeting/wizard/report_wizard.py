
import json
from lxml import etree
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.tools import float_is_zero, float_compare
from odoo.tools.misc import formatLang

from odoo.exceptions import UserError, RedirectWarning, ValidationError

#from common_methods import _check_balance, _check_balance_pr

import odoo.addons.decimal_precision as dp
import logging

class AppStmtWizard(models.TransientModel):
    _name = "budgeting.app.stmt.wizard"
    _description = "Appropriation Statement Report"
   
    datefrom = fields.Date(string='Date From')
    dateto = fields.Date(string='Date To',required=True)
    partner_id = fields.Many2one('res.partner', string='Party', change_default=True, 
        required=True)    
    period_id = fields.Many2one('budgeting.period', string='Budget Specification',
        required=True, states={'draft': [('readonly', False)]})
    account_id = fields.Many2one('account.account', string='Account',
        required=True, 
        domain=[('deprecated', '=', False)], help="The account used for this transaction.")
    rep_ids = fields.One2many('budgeting.app.stmt.wizard.det', 'rep_id')
    
    def get_report(self):
        """Call when button 'Get Report' clicked.
        """
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'datefrom': self.datefrom,
                'dateto': self.dateto,
                'partner_id': self.partner_id.id,
                'period_id': self.period_id.id,
                'account_id': self.account_id.id,
            },
        }

        return self.env.ref('budgeting.appstmt_report').report_action(self, data=data)


class AppStmtWizardDet(models.TransientModel):
    _name = "budgeting.app.stmt.wizard.det"
    _description = "Appropriation Statement Report Details"

    rep_id = fields.Many2one('budgeting.app.stmt.wizard', string="Report", copy=False)
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
    
class AppStmtReport(models.AbstractModel):
    """Abstract Model for report template.
    for `_name` model, please use `report.` as prefix then add `module_name.report_name`.
    """

    _name = "report.budgeting.appstmt_report_view"

    # @api.model
    # def render_html(self, docids, data=None):
    #     self.model = self.env.context.get('active_model')
    #     self.get_report_values(self.env.context.get('active_id'),data)
    #     docs = self.env['budgeting.app.stmt.wizard'].browse(self.env.context.get('active_id'))
    #     docargs = {
    #         'doc_ids': self.ids,
    #         'doc_model': self.model,
    #         'docs': docs,
    #     }
    #     return self.env['report'].render('budgeting.appstmt_report_view', docargs)

    @api.model
    def _get_report_values(self, docids, data=None):
        #datefrom = datetime.strptime(data['form']['datefrom'], '%m%-d-%Y')
        
        dateto = datetime.strptime(data['form']['dateto'],'%Y-%m-%d').date()
        p_id = data['form']['partner_id']
        period_id = data['form']['period_id']
        acc_id = data['form']['account_id']
        
        docs = []
        query = """
                    SELECT 'APP' source, budgeting_appropriationdet.amount, 
                                budgeting_appropriation.date, budgeting_appropriation.name,
                                budgeting_appropriation.date_approved, concat(initcap(budgettype),' Budget') purpose,
                                budgeting_appropriationdet.amount allotment, 0.00 incurred, 1 srtorder     
                        FROM budgeting_appropriation 
                            inner join budgeting_appropriationdet on budgeting_appropriation.id = budgeting_appropriationdet.app_id  
                        WHERE budgeting_appropriation.state = 'approved' and budgeting_appropriation.partner_id = %s 
                        AND budgeting_appropriationdet.account_id = %s and budgeting_appropriation.period_id = %s
                        and date_approved <= %s
                    union
                    SELECT 'PR' source, budgeting_prdet.amount, 
                                budgeting_pr.date, budgeting_pr.name,
                                budgeting_pr.date_approved, case when budgeting_obr.name is not Null then
                                        concat('***',budgeting_pr.purpose) 
                                    else budgeting_pr.purpose end as purpose,
                                0.00 allotment, budgeting_prdet.amount incurred, 3 srtorder    
                        FROM budgeting_pr 
                            inner join budgeting_prdet on budgeting_pr.id = budgeting_prdet.pr_id  
                            left outer join budgeting_obr on budgeting_pr.id = budgeting_obr.pr_id  
                        WHERE budgeting_pr.state in ('approved','obr') and budgeting_pr.partner_id = %s 
                        AND budgeting_prdet.account_id = %s and budgeting_pr.period_id = %s
                        and budgeting_pr.date_approved <= %s    
                    union  
                    SELECT 'OBR' source, budgeting_obrdet.amount, 
                                budgeting_obr.date, budgeting_obr.name,
                                budgeting_obr.date_approved,  
                                    case when budgeting_pr.name is not Null then
                                        concat('*From ',budgeting_pr.name,' - ',budgeting_obr.purpose) 
                                    else concat('From ',' - ',budgeting_obr.purpose) end as purpose,
                                0.00 allotment, budgeting_obrdet.amount incurred, 4 srtorder
                        FROM budgeting_obr 
                            inner join budgeting_obrdet on budgeting_obr.id = budgeting_obrdet.obr_id
                            left outer join budgeting_pr on budgeting_pr.id = budgeting_obr.pr_id
                        WHERE budgeting_obr.state = 'approved' and budgeting_obr.partner_id = %s 
                        AND budgeting_obrdet.account_id = %s and budgeting_obr.period_id = %s
                        and budgeting_obr.date_approved <= %s    
                    union    
                    SELECT 'AUF' source, budgeting_augmentationdetfrom.amount amount, 
                                budgeting_augmentation.date, budgeting_augmentation.name,
                                budgeting_augmentation.date_approved, budgeting_augmentation.purpose, 
                                0.00 allotment, budgeting_augmentationdetfrom.amount incurred, 5 srtorder 
                        FROM budgeting_augmentation 
                            inner join budgeting_augmentationdetfrom on budgeting_augmentation.id = budgeting_augmentationdetfrom.aug_id  
                        WHERE budgeting_augmentation.state = 'approved' and budgeting_augmentation.partner_id = %s 
                        AND budgeting_augmentationdetfrom.account_id = %s and budgeting_augmentation.period_id = %s
                        and date_approved <= %s
                    union
                    SELECT 'AUT' source, budgeting_augmentationdetto.amount, 
                                budgeting_augmentation.date, budgeting_augmentation.name,
                                budgeting_augmentation.date_approved, budgeting_augmentation.purpose,
                                budgeting_augmentationdetto.amount allotment, 0.00 incurred, 2 srtorder 
                        FROM budgeting_augmentation 
                            inner join budgeting_augmentationdetto on budgeting_augmentation.id = budgeting_augmentationdetto.aug_id  
                        WHERE budgeting_augmentation.state = 'approved' and budgeting_augmentation.partner_id = %s 
                        AND budgeting_augmentationdetto.account_id = %s and budgeting_augmentation.period_id = %s
                        and budgeting_augmentation.date_approved <= %s
                    order by date_approved, srtorder, name 
                        ;
                """
        self.env.cr.execute(query, (p_id, acc_id, period_id,dateto,p_id, acc_id, period_id,dateto,p_id, acc_id, period_id,dateto,p_id, acc_id, period_id,dateto,p_id, acc_id, period_id,dateto))
        query_results = self.env.cr.dictfetchall()

        self.env["budgeting.app.stmt.wizard.det"].search([('rep_id','=',self.env.context.get('active_id'))]).unlink()
        
        
        temp_balance = 0.00 
        act_balance = 0.00
               
        rep_obj = self.env['budgeting.app.stmt.wizard.det']
        for res in query_results:
            temp_reserves = 0.00
            act_amount = 0.00
            
            if res['source'] == 'APP':
                act_balance +=  res['amount']
                temp_balance +=  res['amount']
            if res['source'] == 'PR':
                if res['purpose'] and res['purpose'][:3] == '***':
                    temp_reserves = 0
                else:
                    temp_reserves = -res['amount']
                    temp_balance -= res['amount']
            if res['source'] == 'OBR':
                if not res['purpose'] or res['purpose'][:8] != '*From PR':
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
                temp_balance +=  res['amount']
                
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
            'amount': res['amount']})

            rep_obj.create(dtadet_dict)

        model = self.env.context.get('active_model')
        docs = self.env['budgeting.app.stmt.wizard'].browse(self.env.context.get('active_id'))
        docargs = {
            'doc_ids': self.ids,
            'doc_model': model,
            'docs': docs,
        }

        return docargs
