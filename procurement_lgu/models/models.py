# -*- coding: utf-8 -*-
import json
# from lxml import etree
import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.tools import float_is_zero, float_compare
from odoo.tools.misc import formatLang
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError, RedirectWarning, ValidationError
# from odoo.tools import amount_to_text_en
import math

# from common_methods import _check_balance, _check_balance_pr

# import odoo.addons.decimal_precision as dp
import logging

_logger = logging.getLogger(__name__)

PURCHASE_REQUISITION_STATES = [
    ('in_progress', 'Confirmed'),
    ('prebid', 'Pre Bid Conference'),
    ('philgeps', 'Posted to PhilGEPS'),
    ('postqual', 'Post Qualification'),
    ('open', 'Bid Selection'),
    ('reso', 'Resolution and Sworn Statement'),
    ('po_obr', 'Processed PO and OBR'),
]

# class ProcurementPrograms(models.Model):
#     _name = 'procurement.program'
# 
#     @api.one
#     @api.depends('code', 'description')
#     def _get_name(self):
#         cde = ''
#         desc = ''
#         if self.code:
#             cde = self.code 
#         if self.descript:
#             desc = self.descript
#         self.name = cde + ' - ' + desc 
# 
#     name = fields.Char(string='Program',
#         readonly=True, compute='_get_name')
#     code = fields.Char(string="AIP Code", required=True)
#     descript = fields.Char(string="Description", required=True)
#     start_date = fields.Date(required=True, index=True)
#     end_date = fields.Date(required=True, index=True) 
#     description = fields.Text(string="Notes")
#     dyear = fields.Char(string='Year',store=True, readonly=True, compute='_getyear')
#     active = fields.Boolean('Active',default=True)
#     
# #     dyear = fields.Char(string='Year')
# 
#     @api.depends('start_date')
#     @api.onchange('start_date')
#     def _getyear(self):
#         for rec in self:
#             if rec.start_date:
#                 rec.dyear = rec.start_date[:4]
# 
#     @api.model
#     def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
#         filter_program = self.env.context.get('filter_program')
#         if filter_program:
#             pu_id = self.env.context.get('pu_id') or 0
#             project_id = self.env.context.get('project_id') or 0
#             program_id = self.env.context.get('program_id') or 0
#              
#             query = """
#                         SELECT ppd.program_id 
#                             FROM procurement_plan pp
#                             inner join procurement_plan_det ppd on pp.id = ppd.pp_id
#                             WHERE pp.state = 'approved'
#                             and partner_id = %s
#                             and project_id = %s
#                             ;
#                     """ % (pu_id, project_id)
#             print(query)
#             self.env.cr.execute(query)
#             query_results = self.env.cr.dictfetchall()
#             filt = []
#             for result in query_results:
#                 filt.append(result['program_id'])
#              
#             tfilt = tuple(filt)
#             args.append(['id', 'in', tfilt]) 
#  
#         res = super(ProcurementPrograms, self)._search(args, offset=offset, limit=limit, order=order,
#                                             count=count, access_rights_uid=access_rights_uid)
#              
#         return res
#

class BudgetSource(models.Model):
    _name = 'budgeting.source'

    name = fields.Char(string="Budget Source", required=True)
    description = fields.Text(string="Notes")
    active = fields.Boolean('Active', default=True)
class ProcurementProject(models.Model):
    _name = 'procurement.project'

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

    name = fields.Char(string='Project',
        readonly=True, compute='_get_name')
    code = fields.Char(string="AIP Code", required=True)
    descript = fields.Char(string="Description", required=True)
    start_date = fields.Date(required=True, index=True)
    end_date = fields.Date(required=True, index=True) 
    description = fields.Text(string="Notes")
    dyear = fields.Char(string='Year',store=True, readonly=True, compute='_getyear')
    active = fields.Boolean('Active',default=True)
    
#     dyear = fields.Char(string='Year')

    @api.depends('start_date')
    @api.onchange('start_date')
    def _getyear(self):
        for rec in self:
            if rec.start_date:
                rec.dyear = rec.start_date.strftime('%Y')

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        filter_project = self.env.context.get('filter_project')
        if filter_project:
            pu_id = self.env.context.get('pu_id') or 0
              
            query = """
                        SELECT pp.project_id 
                            FROM procurement_plan pp
                            inner join procurement_plan_det ppd on pp.id = ppd.pp_id
                            WHERE pp.state = 'approved'
                            and partner_id = %s
                            ;
                    """ % (pu_id)

            self.env.cr.execute(query)
            query_results = self.env.cr.dictfetchall()
            filt = []
            for result in query_results:
                filt.append(result['project_id'])
              
            tfilt = tuple(filt)
            args.append(['id', 'in', tfilt]) 
  
        res = super(ProcurementProject, self)._search(args, offset=offset, limit=limit, order=order,
                                            count=count, access_rights_uid=access_rights_uid)
              
        return res
  


class ProcurementPlan(models.Model):
    _name = 'procurement.plan'
    _inherit = ['mail.thread']
    _description = "Procurement Plan"
    _order = 'name desc'


    name = fields.Char(string='Control Number')
    date = fields.Date("Date", required=True, index=True, default=fields.Date.context_today)
#     project_id = fields.Many2one('procurement.project', string='Project/Program')
    project_id = fields.Many2one('procurement.project', string='Project/Program', required=True)
    year = fields.Char(string='Year')
    trans_type = fields.Selection([
         ('ppmp', 'PPMP'),
         ('adj', 'PPMP Ajustment'),
         ], 'Transaction Type', readonly=True,
         )
    source_id = fields.Many2one('budgeting.source', string='Budget Source', required=True)
    partner_id = fields.Many2one('res.partner', string='Procurement Unit')
    ppd_ids = fields.One2many('procurement.plan.det', 'pp_id', copy=False)
    prepared_by = fields.Char(string='Prepared By', tracking=True, default=lambda self: self.env.user.partner_id.name)
    prepared_by_des = fields.Char(string='Designation')
    approved_by = fields.Char(string='Approved By', tracking=True)
    approved_by_des = fields.Char(string='Designation')
    state = fields.Selection([
         ('draft', 'Draft'),
         ('confirmed', 'Confirmed'),
         ('approved', 'Approved'),
         ('cancel', 'Cancelled')
         ], 'Status', readonly=True, tracking=True, copy=False, default='draft',
         )
    total = fields.Float(compute="_get_total", stored=True)

    @api.onchange('ppd_ids.month01','ppd_ids.month02','ppd_ids.month03','ppd_ids.month04','ppd_ids.month05','ppd_ids.month06','ppd_ids.month07','ppd_ids.month07','ppd_ids.month09','ppd_ids.month10','ppd_ids.month11','ppd_ids.month12','ppd_ids.unit_price')
    def _get_total(self):
        for rec in self:
            rec.total = sum(x.est_budget for x in rec.ppd_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            cde = 'procurement.plan' + str(vals['year'])

            vals['name'] = self.env['ir.sequence'].next_by_code(cde)
            if not vals['name']:
                raise ValidationError(_('Sequence not set. Please contact the programmer.'))

        res = super(ProcurementPlan, self).create(vals_list)

        return res

    def confirm(self):
        
        for rec in self:
            for det in rec.ppd_ids:
                if det.unit_price == 0:
                    raise ValidationError(_('No unit price in one of the items.'))
        
        return self.write({'state': 'confirmed'})

    def update_unit_price(self):
        
        for dets in self:
            for rec in dets.ppd_ids:
                rec.unit_price = 0.00
                cost = self.env['procurement.product.unit.price'].search([('product_id', '=', rec.product_id.product_tmpl_id.id), ('date_of_effectivity', '<=', dets.date)], limit=1, order='date_of_effectivity desc')
                if not cost:
                    cost = self.env['procurement.product.unit.price'].search([('product_id', '=', rec.product_id.product_tmpl_id.id), ('date_of_effectivity', '>', dets.date)], limit=1, order='date_of_effectivity')
                
                if cost:
                    rec.unit_price = cost.unit_price

    
    def approve(self):
        return self.write({'state': 'approved'})
    
    def cancel(self):
        return self.write({'state': 'cancel'})

    def draft(self):
        return self.write({'state': 'draft'})

    def group_prod_type(self):
        res = []

        sql = """ 
            SELECT distinct pt.categ_id 
            FROM procurement_plan_det ppd
            inner join product_product pp on pp.id = ppd.product_id
            inner join product_template pt on pt.id = pp.product_tmpl_id
            where ppd.pp_id = %s  
              """ % (self.id)
              
        self.env.cr.execute(sql)
        query_results = self.env.cr.dictfetchall()
        for rec in query_results:
            res.append(rec['categ_id'])
        res = self.env['product.category'].browse(res)
        return res 

    def group_project(self):
        res = []
 
        sql = """ 
            SELECT distinct pp.project_id 
            FROM procurement_plan pp
            where pp.id = %s  
              """ % (self.id)
               
        self.env.cr.execute(sql)
        query_results = self.env.cr.dictfetchall()
        for rec in query_results:
            res.append(rec['project_id'])
        res = self.env['procurement.project'].browse(res)
        return res 


    def _get_details(self, project_id):
        self.ensure_one()
        res = []
        dets = self.env['procurement.plan.det'].search([('pp_id', '=', self.id), ('pp_id.project_id', '=', project_id)])
        for det in dets:
            res += [(det.product_id.name, det.product_uom_id.name, det.qty, det.unit_price, det.est_budget, det.mode_id.name,
                  det.month_01, det.month_02, det.month_03, det.month_04, det.month_05, det.month_06, det.month_07, det.month_08, det.month_09, det.month_10, det.month_11, det.month_12)]
        
#         currency = self.currency_id or self.company_id.currency_id
#         for line in self.tax_line_ids:
#             res.setdefault(line.tax_id.tax_group_id, 0.0)
#             res[line.tax_id.tax_group_id] += line.amount
#         res = sorted(res.items(), key=lambda l: l[0].sequence)
#         res = [(r[0].name, r[1], formatLang(self.with_context(lang=self.partner_id.lang).env, r[1], currency_obj=currency)) for r in res]
        return res
    
class ProcurementPlanDet(models.Model):
    _name = 'procurement.plan.det'

    pp_id = fields.Many2one('procurement.plan', string='Procurement Plan')
#     program_id = fields.Many2one('procurement.program', string='Program')
    
    product_id = fields.Many2one('product.product', string='Item')
    account_id = fields.Many2one('account.account', string='Item Description')
    product_uom_id = fields.Many2one('uom.uom', string='Unit')
    qty = fields.Integer('Quantity')
    qty_disp = fields.Integer('Quantity', compute="compute_qty")
    mode_id = fields.Many2one('procurement.mode', string='Mode of Procurement')
    month_01 = fields.Integer('Jan')
    month_02 = fields.Integer('Feb')
    month_03 = fields.Integer('Mar')
    month_04 = fields.Integer('Apr')
    month_05 = fields.Integer('May')
    month_06 = fields.Integer('Jun')
    month_07 = fields.Integer('Jul')
    month_08 = fields.Integer('Aug')
    month_09 = fields.Integer('Sep')
    month_10 = fields.Integer('Oct')
    month_11 = fields.Integer('Nov')
    month_12 = fields.Integer('Dec')
    unit_price = fields.Float('Unit Price')
    est_budget = fields.Float('Estimated Budget')
        
    @api.onchange('month_01', 'month_02', 'month_03', 'month_04', 'month_05', 'month_06', 'month_07', 'month_08', 'month_09', 'month_10', 'month_11', 'month_12', 'unit_price')
    def compute_qty(self):
        
        for rec in self:
            rec.qty = rec.month_01 + rec.month_02 + rec.month_03 + rec.month_04 + rec.month_05 + rec.month_06 + rec.month_07 + rec.month_08 + rec.month_09 + rec.month_10 + rec.month_11 + rec.month_12    
            rec.qty_disp = rec.qty
            rec.est_budget = rec.qty * rec.unit_price


    @api.model
    def create(self, vals):
        
        if 'qty' in vals and 'unit_price' in vals:
            vals['est_budget'] = vals['qty'] * vals['unit_price']  
             
        res = super(ProcurementPlanDet, self).create(vals)
        
        return res

    @api.model
    def write(self, vals):
        
        xqty = self.qty
        xunit_price = self.unit_price
        
        if 'qty' in vals:
            xqty = vals['qty']
        
        if 'unit_price' in vals:
            xunit_price = vals['unit_price']
        
        if 'qty' in vals or 'unit_price' in vals:
            vals['est_budget'] = xqty * xunit_price
             
        super(ProcurementPlanDet, self).write(vals)
        
        return True

class ProductUnitPrice(models.Model):
    _name = 'procurement.product.unit.price'

    product_id = fields.Many2one('product.template', string='Product')
    unit_price = fields.Float('Unit Price')
    date_of_effectivity = fields.Date("Date of Effectivity")
    
class Product(models.Model):
    _inherit = 'product.template'
    
    unit_price_ids = fields.One2many('procurement.product.unit.price', 'product_id')

class TransactionLevel(models.Model):
    _name = 'purchase.order.level'
    _order = 'level'
    
    name = fields.Char('Description', required=True, index=True, copy=False)
    level = fields.Integer(string='Level')
    amount_from = fields.Float(string='From')
    amount_to = fields.Float(string='To')
        
class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.model
    def _get_signatory(self):
        signatory = self.env['procurement.signatory'].search([('active', '=', True)], limit=1, order='id desc')
        if signatory:
            for sign in signatory:
                return sign.mayor

    @api.model
    def _get_conforme(self):
        signatory = self.env['procurement.signatory'].search([('active', '=', True)], limit=1, order='id desc')
        if signatory:
            for sign in signatory:
                return sign.conforme_by
    @api.model
    def _get_proc_head(self):
        signatory = self.env['procurement.signatory'].search([('active', '=', True)], limit=1, order='id desc')
        if signatory:
            for sign in signatory:
                return sign.bac_chairman


    transaction_level = fields.Many2one('purchase.order.level', string='Level', required=True)
    year = fields.Char(string='Year', required=True)
    pu_id = fields.Many2one('res.partner', string='Procurement Unit', required=True)
    mode_id = fields.Many2one('procurement.mode', string='Mode of Procurement', required=True)
    project_id = fields.Many2one('procurement.project', string='Project/Program', required=True)
#     program_id = fields.Many2one('procurement.program', string='Program', required=True)
    conforme_by = fields.Char("Conforme By", default=_get_conforme)
    conforme_designation = fields.Char("Designation",default='RCC II/GSO Designated')
    signatory = fields.Char("Signatory", default=_get_signatory)
    signatory_designation = fields.Char("Designation",default='Municipal Mayor')
    place_of_delivery = fields.Char("Place of Delivery")
    delivery_term = fields.Char("Delivery Term")
    proc_head = fields.Char("Procurement Head", default=_get_proc_head)
    proc_head_designation = fields.Char(string="Designation", default='BAC Chairman')
    bid_sec = fields.Char(string="Form of Bid Security")
    bs_bank_comp = fields.Char(string="Bank/Company")
    bs_number = fields.Char(string="Number")
    bs_validity = fields.Char(string="Validity Period")
    bs_amount = fields.Float(string="Bid Security Amount")
    res_bs = fields.Float(string="Required Bid Security")
    sufficiency = fields.Selection([
         ('suf', 'SUFFICIENT'),
         ('ins', 'INSUFFICIENT'),
         ], 'Sufficiency')
    bs_remarks = fields.Char(string="Remarks")
    supplier_owner = fields.Char(string="Vendor / In-charge")
    supplier_designation = fields.Char(string="Designation")
    salutation = fields.Char(string="Salutation")
    noa_date = fields.Date(string="Notice of Award Date")
    ntp_date = fields.Date(string="Notice to Proceed Date")
    fund_source = fields.Text(string="Fund Source")
    amount_in_words = fields.Char(compute='_get_words', string='Amount In Words')
    ntp_date10 = fields.Date(string="Notice to Proceed Date+10",compute='_get_plus10')
    source_id = fields.Many2one('budgeting.source', string='Budget Source', required=True)
    reso_number = fields.Char('BAC Resolution #')

    def _get_words(self):
        for rec in self:
            currency = self.env.ref('base.PHP')
            check_amount_in_words = currency.amount_to_text(rec.amount_total)

            # amount_to_text_en.amount_to_text(math.floor(rec.amount_total), lang='en', currency='')
            check_amount_in_words = check_amount_in_words.replace(' and Zero Cent', '')  # Ugh
            decimals = rec.amount_total % 1
            if not float_is_zero(decimals, precision_digits=2):
                check_amount_in_words += _(' and %s/100') % str(
                    int(round(float_round(decimals * 100, precision_rounding=1))))
            rec.amount_in_words = check_amount_in_words

    def _get_plus10(self):
        for rec in self:
            dte = None
            if rec.ntp_date:
                dte = datetime.datetime.strptime(rec.ntp_date, '%Y-%m-%d') + datetime.timedelta(days=10)
            rec.ntp_date10 = dte

    @api.onchange('requisition_id')
    def _onchange_requisition_id(self):
        if not self.requisition_id:
            return

        requisition = self.requisition_id
        if self.partner_id:
            partner = self.partner_id
        else:
            partner = requisition.vendor_id
        payment_term = partner.property_supplier_payment_term_id
        currency = partner.property_purchase_currency_id or requisition.company_id.currency_id

        FiscalPosition = self.env['account.fiscal.position']
        fpos = FiscalPosition._get_fiscal_position(partner)
        fpos = FiscalPosition.browse(fpos)

        self.partner_id = partner.id
        self.fiscal_position_id = fpos.id
        self.payment_term_id = payment_term.id
        self.company_id = requisition.company_id.id
        self.currency_id = currency.id
        self.origin = requisition.name
        self.partner_ref = requisition.name  # to control vendor bill based on agreement reference
        self.notes = requisition.description
        self.date_order = requisition.date_end or fields.Datetime.now()
        self.picking_type_id = requisition.picking_type_id.id
        self.pu_id = requisition.pu_id.id
        self.year = requisition.year
        self.mode_id = requisition.mode_id.id
        self.transaction_level = requisition.transaction_level.id
        self.project_id = requisition.project_id.id
        self.source_id = requisition.source_id.id

        if requisition.type_id.line_copy != 'copy':
            return

        # Create PO lines if necessary
        order_lines = []
        for line in requisition.line_ids:
            # Compute name
            product_lang = line.product_id.with_context({
                'lang': partner.lang,
                'partner_id': partner.id,
            })
            name = product_lang.display_name
            if product_lang.description_purchase:
                name += '\n' + product_lang.description_purchase

            # Compute taxes
            if fpos:
                taxes_ids = fpos.map_tax(line.product_id.supplier_taxes_id.filtered(lambda tax: tax.company_id == requisition.company_id)).ids
            else:
                taxes_ids = line.product_id.supplier_taxes_id.filtered(lambda tax: tax.company_id == requisition.company_id).ids

            # Compute quantity and price_unit
            if line.product_uom_id != line.product_id.uom_po_id:
                product_qty = line.product_uom_id._compute_quantity(line.product_qty, line.product_id.uom_po_id)
                price_unit = line.product_uom_id._compute_price(line.price_unit, line.product_id.uom_po_id)
            else:
                product_qty = line.product_qty
                price_unit = line.price_unit

            if requisition.type_id.quantity_copy != 'copy':
                product_qty = 0

            # Compute price_unit in appropriate currency
            if requisition.company_id.currency_id != currency:
                price_unit = requisition.company_id.currency_id.compute(price_unit, currency)

            # Create PO line
            order_lines.append((0, 0, {
                'name': name,
                'account_id': line.account_id.id,
                'product_id': line.product_id.id,
                'product_uom': line.product_id.uom_po_id.id,
                'product_qty': product_qty,
                'price_unit': price_unit,
                # 'taxes_id': [(6, 0, taxes_ids)],

                'date_planned': requisition.schedule_date or fields.Date.today(),
                # 'procurement_ids': [(6, 0, [requisition.procurement_id.id])] if requisition.procurement_id else False,
                # 'account_analytic_id': line.account_analytic_id.id,
            }))
        self.order_line = order_lines

    def button_confirm(self):
        for order in self:
            if order.state not in ['draft', 'sent']:
                continue
            
            # validate level limit
            if not (order.amount_total >= order.transaction_level.amount_from and order.amount_total <= order.transaction_level.amount_to):
                raise UserError(_("Order amount does not coincide with the selected level.")) 
            
            # validate availability
            for line in order.order_line:         
                if line.account_id and line.product_id and line.product_qty and line.date_planned:
                    get_ppmps = self.env['procurement.plan.det'].search([('pp_id.project_id', '=', order.project_id.id),
                                                                         ('account_id.id', '=', line.account_id.id),
                                                                         ('pp_id.partner_id.id', '=', order.pu_id.id),
                                                                         ('pp_id.state', '=', 'approved'),
                                                                         ('pp_id.year', '=', order.year)
                                                                         ])

                    mnth = int(line.date_planned.strftime('%m'))
                    qty_ppmp = 0
                    amt_ppmp = 0
                    for ppmp in get_ppmps:
                        if mnth >= 1 and ppmp.month_01:
                            qty_ppmp += ppmp.month_01
                            amt_ppmp += ppmp.month_01 * ppmp.unit_price 
                        if mnth >= 2 and ppmp.month_02:
                            qty_ppmp += ppmp.month_02
                            amt_ppmp += ppmp.month_02 * ppmp.unit_price 
                        if mnth >= 3 and ppmp.month_03:
                            qty_ppmp += ppmp.month_03
                            amt_ppmp += ppmp.month_03 * ppmp.unit_price
                        if mnth >= 4 and ppmp.month_04:
                            qty_ppmp += ppmp.month_04
                            amt_ppmp += ppmp.month_04 * ppmp.unit_price 
                        if mnth >= 5 and ppmp.month_05:
                            qty_ppmp += ppmp.month_05
                            amt_ppmp += ppmp.month_05 * ppmp.unit_price 
                        if mnth >= 6 and ppmp.month_06:
                            qty_ppmp += ppmp.month_06
                            amt_ppmp += ppmp.month_06 * ppmp.unit_price
                        if mnth >= 7 and ppmp.month_07:
                            qty_ppmp += ppmp.month_07
                            amt_ppmp += ppmp.month_07 * ppmp.unit_price 
                        if mnth >= 8 and ppmp.month_08:
                            qty_ppmp += ppmp.month_08
                            amt_ppmp += ppmp.month_08 * ppmp.unit_price 
                        if mnth >= 9 and ppmp.month_09:
                            qty_ppmp += ppmp.month_09
                            amt_ppmp += ppmp.month_09 * ppmp.unit_price
                        if mnth >= 10 and ppmp.month_10:
                            qty_ppmp += ppmp.month_10
                            amt_ppmp += ppmp.month_10 * ppmp.unit_price 
                        if mnth >= 11 and ppmp.month_11:
                            qty_ppmp += ppmp.month_11
                            amt_ppmp += ppmp.month_11 * ppmp.unit_price 
                        if mnth >= 12 and ppmp.month_12:
                            qty_ppmp += ppmp.month_12
                            amt_ppmp += ppmp.month_12 * ppmp.unit_price
                            
                    get_outs = self.env['purchase.order.line'].search([('order_id.project_id.id', '=', order.project_id.id),
                                                                         ('order_id.pu_id.id', '=', order.pu_id.id),
                                                                         ('order_id.state', 'in', ['purchase', 'done']),
                                                                         ('order_id.year', '=', order.year)                                                               
                                                                         ])
                    for get_out in get_outs:
                        qty_ppmp -= get_out.product_qty
                        amt_ppmp -= (get_out.product_qty * get_out.price_unit)  
                    
#                     if qty_ppmp < line.product_qty:
#                         raise ValidationError(_('Remaining quantity for %s is only %s' % (line.product_id.name, qty_ppmp)))
                    
                    if amt_ppmp < (line.product_qty*line.price_unit):
                        raise ValidationError(_('Remaining amount for %s is only %s' % (line.order_id.project_id.name, amt_ppmp)))
                ########################
            
            order._add_supplier_to_product()
            # Deal with double validation process
            if order.company_id.po_double_validation == 'one_step'\
                    or (order.company_id.po_double_validation == 'two_step'\
                        and order.amount_total < self.env.user.company_id.currency_id.compute(order.company_id.po_double_validation_amount, order.currency_id))\
                    or order.user_has_groups('purchase.group_purchase_manager'):
                order.button_approve()
            else:
                order.write({'state': 'to approve'})

            if order.requisition_id:
                lost_rfq = order.requisition_id.purchase_ids.filtered(lambda x: x.id != order.id)
                if lost_rfq:
                    lost_rfq.button_cancel()

        return True


    def button_approve(self, force=False):
        for order in self:
            # validate level limit
            if not (order.amount_total >= order.transaction_level.amount_from and order.amount_total <= order.transaction_level.amount_to):
                raise UserError(_("Order amount does not coincide with the selected level."))

            # validate availability
            for line in order.order_line:         
                if line.account_id and line.product_id and line.product_qty and line.date_planned:
                    get_ppmps = self.env['procurement.plan.det'].search([('pp_id.project_id', '=', order.project_id.id),
                                                                         ('account_id.id', '=', line.account_id.id),
                                                                         ('pp_id.partner_id.id', '=', order.pu_id.id),
                                                                         ('pp_id.state', '=', 'approved'),
                                                                         ('pp_id.year', '=', order.year)
                                                                         ])
                    
                    mnth = int(line.date_planned.strftime('%m'))
                    qty_ppmp = 0
                    amt_ppmp = 0
                    for ppmp in get_ppmps:
                        if mnth >= 1 and ppmp.month_01:
                            qty_ppmp += ppmp.month_01
                            amt_ppmp += ppmp.month_01 * ppmp.unit_price
                        if mnth >= 2 and ppmp.month_02:
                            qty_ppmp += ppmp.month_02
                            amt_ppmp += ppmp.month_02 * ppmp.unit_price 
                        if mnth >= 3 and ppmp.month_03:
                            qty_ppmp += ppmp.month_03
                            amt_ppmp += ppmp.month_03 * ppmp.unit_price
                        if mnth >= 4 and ppmp.month_04:
                            qty_ppmp += ppmp.month_04
                            amt_ppmp += ppmp.month_04 * ppmp.unit_price 
                        if mnth >= 5 and ppmp.month_05:
                            qty_ppmp += ppmp.month_05
                            amt_ppmp += ppmp.month_05 * ppmp.unit_price 
                        if mnth >= 6 and ppmp.month_06:
                            qty_ppmp += ppmp.month_06
                            amt_ppmp += ppmp.month_06 * ppmp.unit_price
                        if mnth >= 7 and ppmp.month_07:
                            qty_ppmp += ppmp.month_07
                            amt_ppmp += ppmp.month_07 * ppmp.unit_price 
                        if mnth >= 8 and ppmp.month_08:
                            qty_ppmp += ppmp.month_08
                            amt_ppmp += ppmp.month_08 * ppmp.unit_price 
                        if mnth >= 9 and ppmp.month_09:
                            qty_ppmp += ppmp.month_09
                            amt_ppmp += ppmp.month_09 * ppmp.unit_price
                        if mnth >= 10 and ppmp.month_10:
                            qty_ppmp += ppmp.month_10
                            amt_ppmp += ppmp.month_10 * ppmp.unit_price 
                        if mnth >= 11 and ppmp.month_11:
                            qty_ppmp += ppmp.month_11
                            amt_ppmp += ppmp.month_11 * ppmp.unit_price 
                        if mnth >= 12 and ppmp.month_12:
                            qty_ppmp += ppmp.month_12
                            amt_ppmp += ppmp.month_12 * ppmp.unit_price
                            
                    get_outs = self.env['purchase.order.line'].search([('order_id.project_id.id', '=', order.project_id.id),
                                                                         ('order_id.pu_id.id', '=', order.pu_id.id),
                                                                         ('order_id.state', 'in', ['purchase', 'done']),
                                                                         ('order_id.year', '=', order.year)                                                               
                                                                         ])
                    for get_out in get_outs:
                        qty_ppmp += get_out.product_qty
                        amt_ppmp -= (get_out.product_qty * get_out.price_unit) 
                    
#                     if qty_ppmp < line.product_qty:
#                         raise ValidationError(_('Remaining quantity for %s is only %s' % (line.product_id.name, qty_ppmp)))
                    
                    if amt_ppmp < (line.product_qty*line.price_unit):
                        raise ValidationError(_('Remaining amount for %s is only %s' % (line.order_id.project_id.name, amt_ppmp)))
                ########################
            
        if not self.reso_number:
            reso = self.env['ir.sequence'].next_by_code('bac.resolution.seq')
        else:
            reso = self.reso_number

        self.write({'state': 'purchase',
                    'reso_number' : reso,
                    'date_approve': fields.Date.context_today(self)})
        self._create_picking()
        self.filtered(
            lambda p: p.company_id.po_lock == 'lock').write({'state': 'done'})
        return {}

class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"


    account_id = fields.Many2one('account.account', string='Item Description')

#     @api.onchange('product_qty', 'product_uom')
    def _onchange_quantity(self):
        if not self.product_id:
            return

        seller = self.product_id._select_seller(
            partner_id=self.partner_id,
            quantity=self.product_qty,
            date=self.order_id.date_order and self.order_id.date_order[:10],
            uom_id=self.product_uom)
 
        if seller or not self.date_planned:
            self.date_planned = self._get_date_planned(seller).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
 
        if not seller:
            price_search = self.env['procurement.product.unit.price'].search([('product_id', '=', self.product_id.product_tmpl_id.id), ('date_of_effectivity', '<=', self.order_id.date_order)], limit=1, order='date_of_effectivity desc')
            if price_search:
                price_unit = price_search.unit_price or 0.00 
#             return
        else:
            price_unit = self.env['account.tax']._fix_tax_included_price_company(seller.price, self.product_id.supplier_taxes_id, self.taxes_id, self.company_id) if seller else 0.0
            if price_unit and seller and self.order_id.currency_id and seller.currency_id != self.order_id.currency_id:
                price_unit = seller.currency_id.compute(price_unit, self.order_id.currency_id)
    
            if seller and self.product_uom and seller.product_uom != self.product_uom:
                price_unit = seller.product_uom._compute_price(price_unit, self.product_uom)

        # validate quantity
        if self.account_id and self.product_id and self.product_qty and self.date_planned:
            get_ppmps = self.env['procurement.plan.det'].search([('account_id', '=', self.account_id.id),
                                                                 ('pp_id.project_id.id', '=', self.order_id.project_id.id),
                                                                 ('pp_id.partner_id.id', '=', self.order_id.pu_id.id),
                                                                 ('pp_id.state', '=', 'approved'),
                                                                 ('pp_id.year', '=', self.order_id.year)
                                                                 ])
            
            mnth = int(self.date_planned.strftime('%m'))
            qty_ppmp = 0
            amt_ppmp = 0
            for ppmp in get_ppmps:
                if mnth >= 1 and ppmp.month_01:
                    qty_ppmp += ppmp.month_01
                    amt_ppmp += ppmp.month_01 * ppmp.unit_price
                if mnth >= 2 and ppmp.month_02:
                    qty_ppmp += ppmp.month_02
                    amt_ppmp += ppmp.month_02 * ppmp.unit_price
                if mnth >= 3 and ppmp.month_03:
                    qty_ppmp += ppmp.month_03
                    amt_ppmp += ppmp.month_03 * ppmp.unit_price
                if mnth >= 4 and ppmp.month_04:
                    qty_ppmp += ppmp.month_04
                    amt_ppmp += ppmp.month_04 * ppmp.unit_price
                if mnth >= 5 and ppmp.month_05:
                    qty_ppmp += ppmp.month_05
                    amt_ppmp += ppmp.month_05 * ppmp.unit_price
                if mnth >= 6 and ppmp.month_06:
                    qty_ppmp += ppmp.month_06
                    amt_ppmp += ppmp.month_06 * ppmp.unit_price
                if mnth >= 7 and ppmp.month_07:
                    qty_ppmp += ppmp.month_07
                    amt_ppmp += ppmp.month_07 * ppmp.unit_price
                if mnth >= 8 and ppmp.month_08:
                    qty_ppmp += ppmp.month_08
                    amt_ppmp += ppmp.month_08 * ppmp.unit_price
                if mnth >= 9 and ppmp.month_09:
                    qty_ppmp += ppmp.month_09
                    amt_ppmp += ppmp.month_09 * ppmp.unit_price
                if mnth >= 10 and ppmp.month_10:
                    qty_ppmp += ppmp.month_10
                    amt_ppmp += ppmp.month_10 * ppmp.unit_price
                if mnth >= 11 and ppmp.month_11:
                    qty_ppmp += ppmp.month_11
                    amt_ppmp += ppmp.month_11 * ppmp.unit_price
                if mnth >= 12 and ppmp.month_12:
                    qty_ppmp += ppmp.month_12
                    amt_ppmp += ppmp.month_12 * ppmp.unit_price
                    
            get_outs = self.env['purchase.order.line'].search([('product_id', '=', self.product_id.id),
                                                                 ('order_id.pu_id.id', '=', self.order_id.pu_id.id),
                                                                 ('order_id.state', 'in', ['purchase', 'done']),
                                                                 ('order_id.year', '=', self.order_id.year)                                                               
                                                                 ])
            for get_out in get_outs:
                qty_ppmp -= get_out.product_qty
                amt_ppmp -= (get_out.product_qty * get_out.price_unit)


            # if qty_ppmp < self.product_qty:
            #     raise ValidationError(_('Remaining quantity are only %s' % (qty_ppmp)))

            if amt_ppmp < (self.product_qty * self.price_unit):
                raise ValidationError(_('Remaining amount for %s is only %s' % (self.order_id.project_id.name, amt_ppmp)))

        self.price_unit = price_unit
        
class ProductProduct(models.Model):
    _inherit = 'product.product'

        
    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        
        filter_procurement = self.env.context.get('filter_procurement') or False
        pu_id = self.env.context.get('pu_id') or False
#         mode_id = self.env.context.get('mode_id') or False
        project_id = self.env.context.get('project_id') or False
#         program_id = self.env.context.get('program_id') or False
        year = self.env.context.get('year') or False
        if filter_procurement: 
            if not pu_id or not year:
                return False 
            
            query = """
                        SELECT distinct product_id 
                            FROM procurement_plan_det ppd
                            inner join procurement_plan pp on pp.id = ppd.pp_id
                            WHERE pp.partner_id = %s
                            and pp.year = '%s'
                            and ppd.project_id = %s
                            ;
                    """ % (pu_id, year, project_id)

            self.env.cr.execute(query)
            query_results = self.env.cr.dictfetchall()
            filt = []
            for result in query_results:
                filt.append(result['product_id'])
            
            tfilt = tuple(filt)
            args.append(['id', 'in', tfilt]) 

        res = super(ProductProduct, self)._search(args, offset=offset, limit=limit, order=order,
                                            count=count, access_rights_uid=access_rights_uid)
            
        return res        

class Account(models.Model):
    _inherit = 'account.account'

        
    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        
        filter_procurement = self.env.context.get('filter_procurement') or False
        pu_id = self.env.context.get('pu_id') or False
        project_id = self.env.context.get('project_id') or False
        year = self.env.context.get('year') or False
        if filter_procurement: 
            if not pu_id or not year:
                return False 
            
            query = """
                        SELECT distinct account_id 
                            FROM procurement_plan_det ppd
                            inner join procurement_plan pp on pp.id = ppd.pp_id
                            WHERE pp.partner_id = %s
                            and pp.year = '%s'
                            and pp.project_id = %s
                            ;
                    """ % (pu_id, year, project_id)
            print(query)
            self.env.cr.execute(query)
            query_results = self.env.cr.dictfetchall()
            filt = []
            print(query_results)
            for result in query_results:
                filt.append(result['account_id'])
            
            tfilt = tuple(filt)
            args.append(['id', 'in', tfilt]) 

        res = super(Account, self)._search(args, offset=offset, limit=limit, order=order,
                                            count=count, access_rights_uid=access_rights_uid)
            
        return res        


class PurchaseRequisition(models.Model):
    _inherit = "purchase.requisition"

    def _default_mode(self):
        
        return self.env['procurement.mode'].search([('name', '=', 'Public Bidding')], limit=1).id

    @api.model
    def _get_bac_chairman(self):
        signatory = self.env['procurement.signatory'].search([('active', '=', True)], limit=1, order='id desc')
        if signatory:
            for sign in signatory:
                return sign.bac_chairman

    @api.model
    def _get_bac_vicechairman(self):
        signatory = self.env['procurement.signatory'].search([('active', '=', True)], limit=1, order='id desc')
        if signatory:
            for sign in signatory:
                return sign.bac_vicechairman

    @api.model
    def _get_bac_member1(self):
        signatory = self.env['procurement.signatory'].search([('active', '=', True)], limit=1, order='id desc')
        if signatory:
            for sign in signatory:
                return sign.bac_member1

    @api.model
    def _get_bac_member2(self):
        signatory = self.env['procurement.signatory'].search([('active', '=', True)], limit=1, order='id desc')
        if signatory:
            for sign in signatory:
                return sign.bac_member2

    @api.model
    def _get_year(self):

        return fields.Datetime.now().strftime('%Y')

    @api.model
    def _get_bac_member3(self):
        signatory = self.env['procurement.signatory'].search([('active', '=', True)], limit=1, order='id desc')
        if signatory:
            for sign in signatory:
                return sign.bac_member3

    @api.model
    def _get_mayor(self):
        signatory = self.env['procurement.signatory'].search([('active', '=', True)], limit=1, order='id desc')
        if signatory:
            for sign in signatory:
                return sign.mayor

    transaction_level = fields.Many2one('purchase.order.level', string='Level', required=True)
    tr_level = fields.Integer(related="transaction_level.level")
    year = fields.Char(string='Year', required=True, default=_get_year)
    pu_id = fields.Many2one('res.partner', string='Procurement Unit', required=True)
    mode_id = fields.Many2one('procurement.mode', string='Mode of Procurement', required=True,  default=_default_mode)
    project_id = fields.Many2one('procurement.project', string='Project/Program', required=True)
#     program_id = fields.Many2one('procurement.program', string='Program', required=True)
    source_id = fields.Many2one('budgeting.source', string='Budget Source', required=True)
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all', tracking=True,)
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all')
    currency_id = fields.Many2one('res.currency', 'Currency', required=True, default=lambda self: self.env.user.company_id.currency_id.id)
    state = fields.Selection([('draft', 'Draft'),
                              ('ongoing', 'Ongoing'),
                              ('in_progress', 'Confirmed'),
                              ('prebid', 'Pre Bid Conference'),
                              ('philgeps', 'Posted to PhilGEPS'),
                              ('postqual', 'Post Qualification'),
                              ('open', 'Bid Selection'),
                              ('reso', 'Resolution and Sworn Statement'),
                              ('po_obr', 'Processed PO and OBR'),
                              ('done', 'Done'),
                              ('cancel', 'Cancelled')],
                              'Status', required=True,
                              copy=False, default='draft')

    state_2 = fields.Selection(related='state', string="Status", tracking=False)
    state_3 = fields.Selection(related='state', string="Status", tracking=False)
    state_4 = fields.Selection(related='state', string="Status", tracking=False)
    shw_prebid = fields.Boolean('Show PreBid', compute='_show_btn', invisible=True)
    shw_philgeps = fields.Boolean('Show PhilGEPS', compute='_show_btn', invisible=True)
    shw_postqual = fields.Boolean('Show Post Qual', compute='_show_btn', invisible=True)
    shw_reso = fields.Boolean('Show Reso', compute='_show_btn', invisible=True)
    shw_po_obr = fields.Boolean('Show PO OBR', compute='_show_btn', invisible=True)
    shw_open = fields.Boolean('Show Open', compute='_show_btn', invisible=True)
    line_dates = fields.One2many('purchase.requisition.dates', 'requisition_id', string='Status Dates')
    bac_chairman = fields.Char('BAC Chairman', default=_get_bac_chairman)
    bac_vicechairman = fields.Char('BAC Vice Chairman', default=_get_bac_vicechairman)
    bac_member1 = fields.Char('BAC Member 1', default=_get_bac_member1)
    bac_member2 = fields.Char('BAC Member 2', default=_get_bac_member2)
    bac_member3 = fields.Char('BAC Member 3', default=_get_bac_member3)
    mayor = fields.Char('Municipal Mayor', default=_get_mayor)
    requested_by = fields.Char('Requesting Officer')
    end_user = fields.Char('End User')
    bac_twg = fields.Char('BAC - TWG Head')
    observer1 = fields.Char('Observer 1')
    observer2 = fields.Char('Observer 2')
    project_loc = fields.Char('Project Location')
    approved_budget = fields.Float('Approved Budget')
    place_bid = fields.Char('Place of Bid Opening')
    bid_open = fields.Datetime('Bid Opening Date/Time')
    attendance_ids = fields.One2many('purchase.requisition.attendance', 'pr_id', string='Attendance')
    reso_number = fields.Char('BAC Resolution Number', compute='_get_reso')
    winner_bid = fields.Many2one('purchase.order', compute='_get_winner')

    def _get_reso(self):
        reso = self.env['purchase.order'].search([('requisition_id', '=',self.id), ('reso_number','!=', False)], limit=1)
        if reso:
            self.reso_number = reso.reso_number
        else:
            self.reso_number = None


    def _get_winner(self):
        top3 = []
        cr = self.env.cr
        sql = """
            with dta as 
            (select po.id, po.name, rp.name partner, po.state, po.amount_total,
                case when po.state = 'done' then 1
                     when po.state = 'purchase' then 2
                     when po.state in ('draft', 'sent', 'to approve', 'cancel') then 3
                else 4 end as prio, po.partner_id, bid_sec 		
            from purchase_order po
            inner join res_partner rp on rp.id = po.partner_id
            where requisition_id = """ + str(self.id) +\
            """
            )
            select * from dta order by prio, amount_total limit 3
              """

        cr.execute(sql)
        res = cr.dictfetchall()

        for r in res:
            r['partner_id'] = self.env['res.partner'].search([('id','=',r['partner_id'])])
            r['po'] = self.env['purchase.order'].search([('id','=',r['id'])])
            top3.append(r)
        return top3

    def get_top3(self):
        top3 = []
        cr = self.env.cr
        sql = """
            with dta as 
            (select po.id, po.name, rp.name partner, po.state, po.amount_total,
                case when po.state = 'done' then 1
                     when po.state = 'purchase' then 2
                     when po.state in ('draft', 'sent', 'to approve', 'cancel') then 3
                else 4 end as prio, po.partner_id, bid_sec 		
            from purchase_order po
            inner join res_partner rp on rp.id = po.partner_id
            where requisition_id = """ + str(self.id) +\
            """
            )
            select * from dta order by prio, amount_total limit 3
              """

        cr.execute(sql)
        res = cr.dictfetchall()

        for r in res:
            r['partner_id'] = self.env['res.partner'].search([('id','=',r['partner_id'])])
            r['po'] = self.env['purchase.order'].search([('id','=',r['id'])])
            top3.append(r)
        return top3
    
    def draft(self):
        return self.write({'state': 'draft'})

    @api.model
    def _get_tracked_fields(self, updated_fields):
        """ Return a structure of tracked fields for the current model.
            :param list updated_fields: modified field names
            :return dict: a dict mapping field name to description, containing
                always tracked fields and modified on_change fields
        """
        tracked_fields = []
        for name, field in self._fields.items():
            if getattr(field, 'tracking', False):
                if name not in ('state_2', 'state_3', 'state_4'):
                    tracked_fields.append(name)

        if tracked_fields:
            return self.fields_get(tracked_fields)
        return {}
    

    def write(self, vals):
        result = super(PurchaseRequisition, self).write(vals)
        if vals.get('state'):
            self.env['purchase.requisition.dates'].create({
                        'requisition_id': self.id,
                        'status_date': fields.Date.context_today(self),
                        'state': vals.get('state'),
                    })

        return result
    
    @api.depends('state', 'transaction_level')
    def _show_btn(self):
        for order in self:
            sh_open, sh_prebid, sh_philgeps, sh_postqual, sh_reso, sh_po_obr = False, False, False, False, False, False  
            
            if order.state == 'in_progress':
                if order.tr_level == 1:
                    sh_open = True
                if order.tr_level in (2, 3):
                    sh_philgeps = True
                if order.tr_level == 4:
                    sh_prebid = True
            if order.state == 'prebid':
                if order.tr_level == 4:
                    sh_philgeps = True
            if order.state == 'philgeps':
                if order.tr_level in (2, 3, 4):
                    sh_postqual = True
            if order.state == 'postqual':
                if order.tr_level in (2, 3, 4):
                    sh_open = True
            if order.state == 'open':
                if order.tr_level in (3, 4):
                    sh_reso = True
            if order.state == 'reso':
                if order.tr_level in (3, 4):
                    sh_po_obr = True
                    
            order.update({
                'shw_prebid': sh_prebid,
                'shw_philgeps': sh_philgeps,
                'shw_postqual': sh_postqual,
                'shw_reso': sh_reso,
                'shw_po_obr': sh_po_obr,
                'shw_open': sh_open,
            })    


    def btn_po_obr(self):
        return self.write({'state': 'po_obr'})


    def btn_reso(self):
        return self.write({'state': 'reso'})
   

    def btn_prebid(self):
        return self.write({'state': 'prebid'})
   

    def btn_philgeps(self):
        return self.write({'state': 'philgeps'})
    

    def btn_postqual(self):
        return self.write({'state': 'postqual'})
    
    @api.depends('line_ids.price_total')
    def _amount_all(self):
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.line_ids:
                amount_untaxed += line.price_subtotal
                # FORWARDPORT UP TO 10.0
                if order.company_id.tax_calculation_rounding_method == 'round_globally':
                    taxes = line.taxes_id.compute_all(line.price_unit, line.order_id.currency_id, line.product_qty, product=line.product_id, partner=line.order_id.partner_id)
                    amount_tax += sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
                else:
                    amount_tax += line.price_tax
                    
            ttl = amount_untaxed + amount_tax
            srch_level = self.env['purchase.order.level'].search([('amount_from', '<=', ttl), ('amount_to', '>=', ttl)], limit=1)
            if srch_level:
                tlevel = srch_level.id or False 
                        
            order.update({
                'amount_untaxed': order.currency_id.round(amount_untaxed),
                'amount_tax': order.currency_id.round(amount_tax),
                'amount_total': amount_untaxed + amount_tax,
                'transaction_level': tlevel,
            })
            
    
class PurchaseRequisitionDates(models.Model):
    _name = 'purchase.requisition.dates'

    requisition_id = fields.Many2one('purchase.requisition', string='Purchase Agreement')
    status_date = fields.Date(string='Date')
    state = fields.Selection([('draft', 'Draft'),
                              ('in_progress', 'Confirmed'),
                              ('prebid', 'Pre Bid Conference'),
                              ('philgeps', 'Posted to PhilGEPS'),
                              ('postqual', 'Post Qualification'),
                              ('open', 'Bid Selection'),
                              ('reso', 'Resolution and Sworn Statement'),
                              ('po_obr', 'Processed PO and OBR'),
                              ('done', 'Done'),
                              ('cancel', 'Cancelled')],
                              'Status', copy=False, default='draft')
    description = fields.Text(string="Notes")

class PurchaseRequisitionLine(models.Model):
    _inherit = "purchase.requisition.line"

    taxes_id = fields.Many2many('account.tax', string='Taxes', domain=['|', ('active', '=', False), ('active', '=', True)])
    price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total', store=True)
    price_tax = fields.Monetary(compute='_compute_amount', string='Tax', store=True)
    currency_id = fields.Many2one(related='requisition_id.currency_id', store=True, string='Currency', readonly=True)
    account_id = fields.Many2one('account.account', string='Item Description')
    
    
    @api.depends('product_qty', 'price_unit', 'taxes_id')
    def _compute_amount(self):
        for line in self:
            taxes = line.taxes_id.compute_all(line.price_unit, line.requisition_id.currency_id, line.product_qty, product=line.product_id, partner=line.requisition_id.vendor_id)
            line.update({
                'price_tax': taxes['total_included'] - taxes['total_excluded'],
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })

    @api.onchange('account_id')
    def onchange_account_id(self):
        price_unit = 0

        price_search = self.env['procurement.plan.det'].search([('pp_id.partner_id', '=', self.requisition_id.pu_id.id),
                                                                ('pp_id.project_id', '=', self.requisition_id.project_id.id),
                                                                ('account_id', '=', self.account_id.id)], limit=1)
        if price_search:
            price_unit = price_search.unit_price or 0.00

        self.price_unit = price_unit

    @api.onchange('product_qty')
    def onchange_qty(self):
        for line in self:
            if line.account_id and line.product_id and line.product_qty and line.schedule_date:
                get_ppmps = self.env['procurement.plan.det'].search([('account_id', '=', line.account_id.id),
                                                                     ('pp_id.project_id.id', '=', line.requisition_id.project_id.id),
                                                                     ('pp_id.partner_id.id', '=', line.requisition_id.pu_id.id),
                                                                     ('pp_id.state', '=', 'approved'),
                                                                     ('pp_id.year', '=', line.requisition_id.year)
                                                                     ])
                
                mnth = int(line.schedule_date.strftime('%m'))
                qty_ppmp = 0
                amt_ppmp = 0
                for ppmp in get_ppmps:
                    if mnth >= 1 and ppmp.month_01:
                        qty_ppmp += ppmp.month_01
                        amt_ppmp += ppmp.month_01 * ppmp.unit_price
                    if mnth >= 2 and ppmp.month_02:
                        qty_ppmp += ppmp.month_02
                        amt_ppmp += ppmp.month_02 * ppmp.unit_price
                    if mnth >= 3 and ppmp.month_03:
                        qty_ppmp += ppmp.month_03
                        amt_ppmp += ppmp.month_03 * ppmp.unit_price
                    if mnth >= 4 and ppmp.month_04:
                        qty_ppmp += ppmp.month_04
                        amt_ppmp += ppmp.month_04 * ppmp.unit_price
                    if mnth >= 5 and ppmp.month_05:
                        qty_ppmp += ppmp.month_05
                        amt_ppmp += ppmp.month_05 * ppmp.unit_price
                    if mnth >= 6 and ppmp.month_06:
                        qty_ppmp += ppmp.month_06
                        amt_ppmp += ppmp.month_06 * ppmp.unit_price
                    if mnth >= 7 and ppmp.month_07:
                        qty_ppmp += ppmp.month_07
                        amt_ppmp += ppmp.month_07 * ppmp.unit_price
                    if mnth >= 8 and ppmp.month_08:
                        qty_ppmp += ppmp.month_08
                        amt_ppmp += ppmp.month_08 * ppmp.unit_price
                    if mnth >= 9 and ppmp.month_09:
                        qty_ppmp += ppmp.month_09
                        amt_ppmp += ppmp.month_09 * ppmp.unit_price
                    if mnth >= 10 and ppmp.month_10:
                        qty_ppmp += ppmp.month_10
                        amt_ppmp += ppmp.month_10 * ppmp.unit_price
                    if mnth >= 11 and ppmp.month_11:
                        qty_ppmp += ppmp.month_11
                        amt_ppmp += ppmp.month_11 * ppmp.unit_price
                    if mnth >= 12 and ppmp.month_12:
                        qty_ppmp += ppmp.month_12
                        amt_ppmp += ppmp.month_12 * ppmp.unit_price
                        
                get_outs = self.env['purchase.order.line'].search([('product_id', '=', line.product_id.id),
                                                                     ('order_id.pu_id.id', '=', line.requisition_id.pu_id.id),
                                                                     ('order_id.state', 'in', ['purchase', 'done']),
                                                                     ('order_id.year', '=', line.requisition_id.year)                                                               
                                                                     ])

                for get_out in get_outs:
                    qty_ppmp -= get_out.product_qty
                    amt_ppmp -= (get_out.product_qty * get_out.price_unit)

                if amt_ppmp < (line.product_qty * line.price_unit):
                    raise ValidationError(
                        _('Remaining amount for %s is only %s' % (line.order_id.project_id.name, amt_ppmp)))

class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        filter_partner = self.env.context.get('filter_pu')
        if filter_partner:
            query = """
                        SELECT distinct partner_id 
                            FROM procurement_plan 

                            ;
                    """
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


class MinutesAttendance(models.Model):
    _name = 'purchase.requisition.attendance'
    _order = 'rec_type, sequence'

    pr_id = fields.Many2one('purchase.requisition',)
    name = fields.Char('Name', required=True)
    designation = fields.Char('Designation', required=True)
    sequence = fields.Integer(string='Sequence')
    rec_type = fields.Selection([
        ('1present', 'Present'),
        ('2attend', 'Attendees'),
    ], 'Record Type', )
