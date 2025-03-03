# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class BankPolicyWizard(models.TransientModel):
    _name = "bank.loan.wizard"
    _description = "Bank Loan Report"

    lender_ids = fields.Many2many('account.journal', string="Lender", domain=[('type', '=', 'bank')])
    include_fully_paid = fields.Boolean('Include Fully Paid Loans', default=True)

    def _build_contexts(self, data):
        result = {}
        result['lender_ids'] = 'lender_ids' in data['form'] and data['form']['lender_ids'] or False
        result['include_fully_paid'] = 'include_fully_paid' in data['form'] and data['form']['include_fully_paid'] or False

        return result

    def action_retrieve(self):
        self.ensure_one()

        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'bank.loan.wizard')
        data['form'] = self.read(['lender_ids','include_fully_paid'])[0]
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context, lang=self.env.context.get('lang') or 'en_US')
        return self._screen_show(data)

    def _screen_show(self, data):
        dta = self.get_report_values_screen(data=data)

        return dta

    @api.model
    def get_report_values_screen(self, data=None):
        if not data.get('form'):
            raise UserError(_("Form content is missing, this report cannot be printed."))
        if not self.env.context.get('active_model'):
            selfmodel = 'bank.loan.wizard'
        else:
            selfmodel = self.env.context.get('active_model')

        docs = self.env[selfmodel].browse(self.env.context.get('active_ids', []))

        lender_ids = data['form'].get('lender_ids', False)
        include_fully_paid = data['form'].get('include_fully_paid', False)
        docus =  self.with_context(data['form'].get('used_context', {}))._get_documents(lender_ids,include_fully_paid)

        bal = 0
        curbal = 0
        cur_policy = 0
        for rec in docus:
            # if cur_policy != rec['bank_policy_id']:
            #     bal = 0
            #     curbal = 0
            # if rec['currency_debit']:
            #     rec['avg_rate_debit'] = rec['debit'] / rec['currency_debit']
            # if rec['currency_credit']:
            #     rec['avg_rate_credit'] = rec['credit'] / rec['currency_credit']
            # bal +=  rec['debit'] - rec['credit']
            # curbal += rec['currency_debit'] - rec['currency_credit']
            # rec['balance'] = bal
            # rec['currency_balance'] = curbal
            #
            # cur_policy = rec['bank_policy_id']

            self.env['bank.loan.report'].create(rec)

        search_view_ref = self.env.ref('bank_loan.view_bank_loan_report_search_view', False)
        form_view_ref = self.env.ref('bank_loan.view_bank_loan_report_form', False)
        tree_view_ref = self.env.ref('bank_loan.view_bank_loan_report_tree', False)

        return {
            'domain': [('wizard_id', '=', self.id)],
            'context': {'search_default_group_type': True,'search_default_group_lender': True,},
            'name': 'Loan Report',
            'res_model': 'bank.loan.report',
            'type': 'ir.actions.act_window',
            'views': [(tree_view_ref.id, 'tree'), (form_view_ref.id, 'form')],
            'search_view_id': search_view_ref and search_view_ref.id,
        }

    def _get_documents(self, lender_ids,include_fully_paid):
        cr = self.env.cr
        where_clause = ''
        if lender_ids:
            plcy = '('
            for plc in lender_ids:
                plcy += str(plc) + ","
            plcy = plcy[0:len(plcy)-1] + ")"
            where_clause += ' lender_id in ' + plcy
        # else:
        #     where_clause += ' lender_id is not null '

        #
        # if not include_unposted:
        #     where_clause += " and parent_state='posted' "

        if where_clause:
            where_clause = " where " + where_clause

        if not where_clause:
            where_clause = " where " + "al.state = 'posted' "
        else:
            where_clause += " and " + "al.state = 'posted' "

        # case when al.type = 'short' then al.due_date else (select max(date)
        # from account_loan_line where
        # loan_id = al.id
        #           and id in (select loan_line_id from account_move where loan_id = al.id)) end as due_date,

    #     case when al.type = 'short' then
    #     case when al.due_date - date(now()) <= 0
    #     then 'مستحقة' else concat((al.due_date - date(now()))::text, ' day(s)') end
    #     else case when(select max(date) from account_loan_line where
    # loan_id = al.id and id in (select loan_line_id from account_move where loan_id = al.id)) - date(now()) <= 0
    # then 'مستحقة' else concat(((select max(date) from account_loan_line where loan_id = al.id
    # and id in (select loan_line_id from account_move where loan_id = al.id)) - date(
    #     now()))::text, ' day(s)') end
    #     end as due_on,

        sql = ("""
            select %s as wizard_id, al.id as loan_id, al.company, al.lender_id, al.start_date, 
                case when al.type = 'short' then concat(al.short_term_due::text, ' days') else concat(al.periods::text, ' year(s)') end as short_term_due,
                ((al.loan_amount + coalesce((select sum(coalesce(interests_amount,0)+coalesce(additional_interest,0)) from account_loan_line where loan_id = al.id and is_active and date <= now()::date),0)) - (select sum(credit - abs(aml.amount_residual))
                    from account_move_line aml
                    inner join account_move am on am.id = aml.move_id
                    where am.id in (select id from account_move where loan_id = al.id)
                    and aml.account_id = al.loan_account_id
                    and am.state = 'posted' and aml.credit != 0)) as remaining_balance,
                al.loan_amount, 
                (select sum(credit - abs(aml.amount_residual))
                    from account_move_line aml
                    inner join account_move am on am.id = aml.move_id
                    where am.id in (select id from account_move where loan_id = al.id)
                    and aml.account_id = al.loan_account_id
                    and am.state = 'posted' and aml.credit != 0) as payment, 
                coalesce((select sum(interests_amount+coalesce(additional_interest,0)) from account_loan_line where loan_id = al.id and is_active),0) as total_interest,
                (al.loan_amount + coalesce((select sum(interests_amount+coalesce(additional_interest,0)) from account_loan_line where loan_id = al.id and is_active and date <= now()::date),0)) as total_due,
                al.type 
            from account_loan al
            %s
            """) % (self.id, where_clause)
        cr.execute(sql)
        res = []
        for row in cr.dictfetchall():
            res.append(row)



        return res


class BankLoanReport(models.TransientModel):
    _name = "bank.loan.report"
    _description = "Bank Loan Report"
    # _order = 'bank_policy_id, date, id'

    loan_id = fields.Many2one('account.loan', string="Loan")
    wizard_id = fields.Many2one('bank.loan.wizard', string="Wizard")
    company = fields.Many2one('res.partner', string="Company")
    lender_id = fields.Many2one('account.journal', string="Lender")
    start_date = fields.Date("Loan Date")
    short_term_due = fields.Char(default=0, string="Due to Pay")
    due_date = fields.Date("Due Date", compute='_compute_due_date')
    due_on = fields.Char('Due On', compute='_compute_due_date')
    ddue_date = fields.Date("Due Date")
    ddue_on = fields.Char('Due On')
    remaining_balance = fields.Float('Remaining Balance')
    loan_amount = fields.Float('Loan Amount')
    payment = fields.Float('Payment')
    total_interest = fields.Float('Total Interest')
    total = fields.Float('Total', compute='_compute_total')
    total_due = fields.Float('Total Due')
    type = fields.Selection([('short', 'Short Term'),
                             ('long', 'Long Term'),
                             ],)

    def _compute_due_date(self):
        for record in self:
            if record.loan_id.type == 'long':
                next_due = record.loan_id.line_ids.filtered(lambda r: r.is_active and (r.date > fields.Datetime.now().date() or r.amount_paid != r.payment_amount))
                if next_due:
                    record.due_date = next_due[0].date
                    record.ddue_date = next_due[0].date
                    if next_due[0].amount_paid == next_due[0].payment_amount:
                        record.due_on = 'مدفوعة'
                        record.ddue_on = 'مدفوعة'
                    else:
                        if next_due[0].date <=  fields.Datetime.now().date():
                            record.due_on = 'مستحقة'
                            record.ddue_on = 'مستحقة'
                        else:
                            record.due_on = str(next_due[0].date - fields.Datetime.now().date()).replace(', 0:00:00','')
                            record.ddue_on = str(next_due[0].date - fields.Datetime.now().date()).replace(', 0:00:00','')
            else:
                record.due_date = max(record.loan_id.line_ids.filtered(lambda r: r.is_active).mapped('date'))
                record.ddue_date = max(record.loan_id.line_ids.filtered(lambda r: r.is_active).mapped('date'))
                recs = record.loan_id.line_ids.filtered(lambda r: r.is_active)
                t_int = 0
                for rec in recs:
                    t_int += rec.interests_amount + rec.additional_interest

                if record.loan_id.total_payment == record.loan_id.loan_amount + t_int:
                    record.due_on = 'مدفوعة'
                    record.ddue_on = 'مدفوعة'
                else:
                    if record.due_date <= fields.Datetime.now().date():
                        record.due_on = 'مستحقة'
                        record.ddue_on = 'مستحقة'
                    else:
                        record.due_on = str(record.due_date - fields.Datetime.now().date()).replace(', 0:00:00','')
                        record.ddue_on = str(record.due_date - fields.Datetime.now().date()).replace(', 0:00:00', '')

    def _compute_total(self):
        for record in self:
            record.total = record.loan_amount + record.total_interest

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        """
            Override read_group to calculate the sum of the non-stored fields that depend on the user context
        """
        if 'avg_rate_debit' in fields:
            fields.remove('avg_rate_debit')
        if 'avg_rate_credit' in fields:
            fields.remove('avg_rate_credit')

        if 'company_id' in groupby and 'bank_policy_id' in groupby:
            if 'debit' in fields:
                fields.remove('debit')
            if 'credit' in fields:
                fields.remove('credit')
            if 'currency_debit' in fields:
                fields.remove('currency_debit')
            if 'currency_credit' in fields:
                fields.remove('currency_credit')
            if 'balance' in fields:
                fields.remove('balance')
            if 'currency_balance' in fields:
                fields.remove('currency_balance')

        res = super(BankLoanReport, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        for line in res:

            if 'balance' in fields and 'debit' in fields and 'credit' in fields:
                line['balance'] = line['debit'] - line['credit']
            if 'currency_balance' in fields and 'currency_debit' in fields and 'currency_credit' in fields:
                line['currency_balance'] = line['currency_debit'] - line['currency_credit']

            return res