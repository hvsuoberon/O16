# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import xlsxwriter
import base64
# from cStringIO import StringIO
from datetime import datetime
from pytz import timezone
import pytz


class PPMPWizard(models.TransientModel):
    _name = "procurement.plan.wizard"
    _description = "Procurement Summary"

    year = fields.Char(string='Year', required=True)
    pu_id = fields.Many2one('res.partner', string="Procurement Unit", required=True)
    rep_ids = fields.One2many('procurement.plan.report', 'wizard_id')
    datas = fields.Binary('File', readonly=True)
    datas_fname = fields.Char('Filename', readonly=True)

    
    def _build_contexts(self, data):
        result = {}
        result['pu_id'] = 'pu_id' in data['form'] and data['form']['pu_id'] or False
        result['year'] = 'year' in data['form'] and data['form']['year'] or False

        return result

    def action_retrieve(self):
        self.ensure_one()

        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'procurement.plan.wizard')
        data['form'] = self.read(['year', 'pu_id'])[0]
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context, lang=self.env.context.get('lang') or 'en_US')
        return self._screen_show(data)

    def _print_report(self, data):
        return self.env['report'].get_action(self, 'procurement_lgu.ppmp_summary_report_view', data=data)
        
    def check_report(self):
        self.ensure_one()
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'procurement.plan.wizard')
        data['form'] = self.read(['year', 'pu_id'])[0]
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context, lang=self.env.context.get('lang') or 'en_US')
        return self._print_report(data)

    def _screen_show(self, data):
        dta = self.get_report_values_screen(data=data)

        return dta

    @api.model
    def get_report_values_screen(self, data=None):
        if not data.get('form'):
            raise UserError(_("Form content is missing, this report cannot be printed."))
        if not self.env.context.get('active_model'):
            selfmodel = 'procurement.plan.wizard'
        else:
            selfmodel = self.env.context.get('active_model')

        docs = self.env[selfmodel].browse(self.env.context.get('active_ids', []))

        pu_id = data['form'].get('pu_id', False)
        year = data['form'].get('year', False)
        docus = self.with_context(data['form'].get('used_context', {}))._get_documents(pu_id, year)

        self.env["procurement.plan.report"].search([('wizard_id', '=', self.id)]).unlink()
        
#         bal = 0
#         curbal = 0
#         cur_policy = 0
        for rec in docus:
            self.env['procurement.plan.report'].create(rec)

        search_view_ref = self.env.ref('procurement_lgu.view_procurement_plan_report_search_view', False)
        form_view_ref = self.env.ref('procurement_lgu.view_procurement_plan_report_form', False)
        tree_view_ref = self.env.ref('procurement_lgu.view_procurement_plan_report_tree', False)

        return {
            'domain': [('wizard_id', '=', self.id)],
            'context': {'search_default_group_pu': True, 'search_default_group_project': True,},
            'name': 'PPMP Report',
            'res_model': 'procurement.plan.report',
            'type': 'ir.actions.act_window',
            'views': [(tree_view_ref.id, 'tree'), (form_view_ref.id, 'form')],
            'search_view_id': search_view_ref and search_view_ref.id,
        }

    def _get_documents(self, pu_id, year):
        cr = self.env.cr
        where_clause = ''
        if pu_id:
#             prj = '('
#             for plc in project_ids:
#                 prj += str(plc) + ","
#             plcy = prj[0:len(prj)-1] + ")"
            where_clause += ' partner_id = %s ' % pu_id[0]
        
        if where_clause:
            where_clause = " where " + where_clause

        if not where_clause:
            where_clause = " where " + "pp.year = '%s' and pp.state='approved' " % year
        else:
            where_clause += " and " + "pp.year = '%s' and pp.state='approved' " % year


        sql = ("""
            select %s as wizard_id, ppd.project_id,
            ppd.product_id, ppd.product_uom_id, sum(ppd.qty) qty,  
            sum(ppd.month_01) month_01, sum(ppd.month_02) month_02, sum(ppd.month_03) month_03, sum(ppd.month_04) month_04, 
            sum(ppd.month_05) month_05, sum(ppd.month_06) month_06, sum(ppd.month_07) month_07, sum(ppd.month_08) month_08, 
            sum(ppd.month_09) month_09, sum(ppd.month_10) month_10, sum(ppd.month_11) month_11, sum(ppd.month_12) month_12,
            ppd.unit_price, sum(ppd.est_budget) est_budget, pp.partner_id pu_id, ppd.mode_id                 
            from procurement_plan pp
            inner join procurement_plan_det ppd on ppd.pp_id = pp.id
            %s
            group by 20, 1,2,3,4,18,21
            """) % (self.id, where_clause)
        cr.execute(sql)
        res = []
        for row in cr.dictfetchall():
            res.append(row)

        return res

    def group_project(self):
        res = []

        sql = """ 
            SELECT distinct project_id 
            FROM procurement_plan_report 
            where wizard_id = %s  
              """ % (self.id)
              
        self.env.cr.execute(sql)
        query_results = self.env.cr.dictfetchall()
        for rec in query_results:
            res.append(rec['project_id'])
        res = self.env['procurement.project'].browse(res)
        return res 

#     def group_program(self, project_id):
#         res = []
# 
#         sql = """ 
#             SELECT distinct program_id 
#             FROM procurement_plan_report 
#             where wizard_id = %s
#             and project_id = %s  
#               """ % (self.id, project_id)
#               
#         self.env.cr.execute(sql)
#         query_results = self.env.cr.dictfetchall()
#         for rec in query_results:
#             res.append(rec['program_id'])
#         res = self.env['procurement.program'].browse(res)
#         return res 

    def _get_details(self, project_id):
        self.ensure_one()
        res = []
        dets = self.env['procurement.plan.report'].search([('wizard_id', '=', self.id), ('project_id', '=', project_id)])
        for det in dets:
            res += [(det.product_id.name,
                     det.qty,
                     det.product_uom_id.name,
                     det.est_budget,
                     det.mode_id.name,
                     det.month_01, det.month_02, det.month_03, det.month_04,
                     det.month_05, det.month_06, det.month_07, det.month_08,
                     det.month_09, det.month_10, det.month_11, det.month_12)]

        return res

    @api.model
    def get_default_date_model(self):
        return pytz.UTC.localize(datetime.now()).astimezone(timezone(self.env.user.tz or 'UTC'))

    def print_excel_report(self):
        data = self.read()[0]

        pu_id = data['pu_id']
        year = data['year']

        datetime_string = self.get_default_date_model().strftime("%Y-%m-%d %H:%M:%S")
        date_string = self.get_default_date_model().strftime("%Y-%m-%d")
        report_name = 'PPMP Summary'
        filename = '%s %s.xlsx' % (report_name, date_string)
        
        columns = [
            ('Code', 12, 'char', 'char', 'A'),
            ('General Description', 30, 'char', 'char', 'B'),
            ('Quantity', 6, 'number', 'char', 'C'),
            ('UoM', 10, 'char', 'char', 'D'),
            ('Estimated Budget', 15, 'float', 'float', 'E'),
            ('Mode of Procurement', 20, 'char', 'char', 'F'),
            ('Jan', 5, 'float', 'float', 'G'),
            ('Feb', 5, 'float', 'float', 'H'),
            ('Mar', 5, 'float', 'float', 'I'),
            ('Apr', 5, 'float', 'float', 'J'),
            ('May', 5, 'float', 'float', 'K'),
            ('Jun', 5, 'float', 'float', 'L'),
            ('Jul', 5, 'float', 'float', 'M'),
            ('Aug', 5, 'float', 'float', 'N'),
            ('Sep', 5, 'float', 'float', 'O'),
            ('Oct', 5, 'float', 'float', 'P'),
            ('Nov', 5, 'float', 'float', 'Q'),
            ('Dec', 5, 'float', 'float', 'R'),
        ]

        datetime_format = '%Y-%m-%d %H:%M:%S'
        utc = datetime.now().strftime(datetime_format)
        utc = datetime.strptime(utc, datetime_format)
        tz = self.get_default_date_model().strftime(datetime_format)
        tz = datetime.strptime(tz, datetime_format)
        duration = tz - utc
        hours = duration.seconds / 60 / 60
        if hours > 1 or hours < 1 :
            hours = str(hours) + ' hours'
        else :
            hours = str(hours) + ' hour'
        
        self.env["procurement.plan.report"].search([('wizard_id', '=', self.id)]).unlink()
        
        docus = self._get_documents(pu_id, year)
        for rec in docus:
            self.env['procurement.plan.report'].create(rec)

        
        fp = StringIO()
        workbook = xlsxwriter.Workbook(fp)
        wbf, workbook = self.add_workbook_format(workbook)

        worksheet = workbook.add_worksheet(report_name)
        worksheet.merge_range('A1:R1', 'PROJECT PROCUREMENT MANAGEMENT PLAN (PPMP)', wbf['title_doc'])
        worksheet.write('A3', "END-USER/UNIT : " + pu_id[1], wbf['company'])
        worksheet.write('A4', "Charged to Annual Budget " + year, wbf['company'])
        worksheet.write('A5', "Projects, Programs and Activities (PAPs)", wbf['company'])
        worksheet.merge_range('G5:R5', 'SCHEDULE/MILESTONE OF ACTIVITIES', wbf['header'])

        row = 5

        col = 0
        for column in columns:
            column_name = column[0]
            column_width = column[1]
            column_type = column[2]
            worksheet.set_column(col, col, column_width)
            if col <= 5:    
                worksheet.merge_range('%s%s:%s%s' % (column[4], row, column[4], row + 1), column_name, wbf['header'])
            else:
                worksheet.write('%s%s' % (column[4], row + 1), column_name, wbf['header'])
                        
            col += 1
        
        row += 2
        row1 = row
        no = 1
    
        for proj in self.group_project():
            worksheet.write('A%s' % (row), proj.code, wbf['grp_project'])
            worksheet.merge_range('B%s:R%s' % (row, row), proj.descript, wbf['grp_project'])
            row += 1
            ttl = 0
                
            for det in self._get_details(proj.id):
                worksheet.write('A%s' % (row), '', wbf['content'])
                worksheet.write('B%s' % (row), det[0], wbf['content'])
                worksheet.write('C%s' % (row), det[1], wbf['content_number'])
                worksheet.write('D%s' % (row), det[2], wbf['content'])
                worksheet.write('E%s' % (row), det[3], wbf['content_float'])
                worksheet.write('F%s' % (row), det[4], wbf['content'])
                worksheet.write('G%s' % (row), det[5], wbf['content_number'])
                worksheet.write('H%s' % (row), det[6], wbf['content_number'])
                worksheet.write('I%s' % (row), det[7], wbf['content_number'])
                worksheet.write('J%s' % (row), det[8], wbf['content_number'])
                worksheet.write('K%s' % (row), det[9], wbf['content_number'])
                worksheet.write('L%s' % (row), det[10], wbf['content_number'])
                worksheet.write('M%s' % (row), det[11], wbf['content_number'])
                worksheet.write('N%s' % (row), det[12], wbf['content_number'])
                worksheet.write('O%s' % (row), det[13], wbf['content_number'])
                worksheet.write('P%s' % (row), det[14], wbf['content_number'])
                worksheet.write('Q%s' % (row), det[15], wbf['content_number'])
                worksheet.write('R%s' % (row), det[16], wbf['content_number'])
                ttl += det[3]
                row += 1
        
            worksheet.write('A%s' % (row), 'TOTAL', wbf['total'])
            worksheet.merge_range('B%s:D%s' % (row, row), '', wbf['total'])
            worksheet.write('E%s' % (row), ttl, wbf['total_float'])
            worksheet.merge_range('F%s:R%s' % (row, row), '', wbf['total'])
            
            prov = ttl * 0.10
            contin = ttl * 0.10
            
            row += 2
            worksheet.merge_range('A%s:B%s' % (row, row), 'TOTAL BUDGET', wbf['summary'])
            worksheet.merge_range('C%s:D%s' % (row, row), ttl, wbf['summary_float'])
            row += 1
            worksheet.merge_range('A%s:B%s' % (row, row), '+ 10% Provision for Inflation', wbf['summary'])
            worksheet.merge_range('C%s:D%s' % (row, row), prov, wbf['summary_float'])
            row += 1
            worksheet.merge_range('A%s:B%s' % (row, row), '+ 10% Contingency', wbf['summary'])
            worksheet.merge_range('C%s:D%s' % (row, row), contin, wbf['summary_float'])
            row += 1
            worksheet.merge_range('A%s:B%s' % (row, row), 'TOTAL ESTIMATED BUDGET:', wbf['summary'])
            worksheet.merge_range('C%s:D%s' % (row, row), ttl + prov + contin, wbf['summary_float'])
            
            row += 2
            worksheet.write('A%s' % (row), 'NOTE: Technical Specifications for each Item/Project being proposed shall be submitted as part of the PPMP', wbf['note'])
            
            row += 2
            worksheet.write('A%s' % (row), 'Prepared By:', wbf['company'])
            worksheet.write('E%s' % (row), 'Submitted By:', wbf['company'])
            
            
#         worksheet.merge_range('A%s:B%s'%(row,row), 'Grand Total', wbf['total_orange'])
#         for x in range(len(columns)) :
#             if x in (0,1) :
#                 continue
#             column_type = columns[x][3]
#             if column_type == 'char' :
#                 worksheet.write(row-1,x, '', wbf['total_orange'])
#             else :
#                 if column_type == 'float' :
#                     wbf_value = wbf['total_float_orange']
#                 else : #number
#                     wbf_value = wbf['total_number_orange']
#                 if x in column_float_number :
#                     worksheet.write(row-1, x, column_float_number[x], wbf_value)
#                 else :
#                     worksheet.write(row-1, x, 0, wbf_value)
        
#         worksheet.write('A%s'%(row+2), 'Date %s (%s)'%(datetime_string,self.env.user.tz or 'UTC'), wbf['content_datetime'])
        workbook.close()
        out = base64.encodestring(fp.getvalue())
        self.write({'datas':out, 'datas_fname':filename})
        fp.close()
        
        return {
            'type': 'ir.actions.report.xml',
            'report_type': 'controller',
            'report_file': '/web/content/%s/%s/datas/%s?download=true' % (self._name, self.id, self.datas_fname),
        }

    def add_workbook_format(self, workbook):
        colors = {
            'white_orange': '#FFFFDB',
            'orange': '#FFC300',
            'red': '#FF0000',
            'yellow': '#F6FA03',
        }

        wbf = {}
        wbf['header'] = workbook.add_format({'bold': 1, 'valign': 'vcenter', 'align': 'center', 'bg_color': '#FFFFDB', 'font_size':9, 'font_color': '#000000', 'font_name': 'Arial','text_wrap':True})
        wbf['header'].set_border()
        
        wbf['grp_project'] = workbook.add_format({'bold': 1, 'valign': 'vcenter','align': 'left', 'font_size':10, 'font_color': '#000000', 'font_name': 'Arial'})
        wbf['grp_project'].set_border()
        
        wbf['grp_program'] = workbook.add_format({'bold': 1, 'align': 'left', 'font_size':9, 'font_color': '#000000', 'font_name': 'Arial'})
        wbf['grp_program'].set_border()

        wbf['header_no'] = workbook.add_format({'bold': 1, 'align': 'center', 'bg_color': '#FFFFDB', 'font_color': '#000000', 'font_name': 'Arial'})
        wbf['header_no'].set_border()
        wbf['header_no'].set_align('vcenter')
                
        wbf['footer'] = workbook.add_format({'align':'left', 'font_name': 'Arial'})
        
        wbf['content_datetime'] = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm:ss', 'font_name': 'Arial'})
        wbf['content_datetime'].set_left()
        wbf['content_datetime'].set_right()
        
        wbf['content_date'] = workbook.add_format({'num_format': 'yyyy-mm-dd', 'font_name': 'Arial'})
        wbf['content_date'].set_left()
        wbf['content_date'].set_right() 
        
        wbf['title_doc'] = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 12,
            'font_name': 'Arial',
        })
        
        wbf['company'] = workbook.add_format({'align': 'left', 'font_name': 'Arial'})
        wbf['company'].set_font_size(11)
        
        wbf['content'] = workbook.add_format({'align': 'left', 'font_size':8, 'font_color': '#000000', 'font_name': 'Arial'})
        wbf['content'].set_border()
#         wbf['content'].set_left()
#         wbf['content'].set_right() 
        
        wbf['content_float'] = workbook.add_format({'align': 'right', 'font_size':8, 'num_format': '#,##0.00', 'font_name': 'Arial'})
        wbf['content_float'].set_border()

        wbf['content_number'] = workbook.add_format({'align': 'right', 'font_size':8, 'num_format': '#,##0', 'font_name': 'Arial'})
        wbf['content_number'].set_border() 
        
        wbf['content_percent'] = workbook.add_format({'align': 'right', 'num_format': '0.00%', 'font_name': 'Arial'})
        wbf['content_percent'].set_right() 
        wbf['content_percent'].set_left() 
                
        wbf['total_float'] = workbook.add_format({'bold':1, 'font_size':10, 'align':'right', 'num_format':'#,##0.00', 'font_name': 'Arial'})
        wbf['total_float'].set_top()
        wbf['total_float'].set_bottom()            
#         wbf['total_float'].set_left()
#         wbf['total_float'].set_right()         
        
        wbf['total_number'] = workbook.add_format({'align':'right', 'bg_color': colors['white_orange'], 'bold':1, 'num_format': '#,##0', 'font_name': 'Arial'})
        wbf['total_number'].set_top()
        wbf['total_number'].set_bottom()            
        wbf['total_number'].set_left()
        wbf['total_number'].set_right()
        
        wbf['total'] = workbook.add_format({'bold':1, 'font_size':10, 'align':'left', 'font_name': 'Arial'})
#         wbf['total'].set_left()
#         wbf['total'].set_right()
        wbf['total'].set_top()
        wbf['total'].set_bottom()

        wbf['summary'] = workbook.add_format({'bold':1, 'font_size':10, 'align':'left', 'font_name': 'Arial'})
        wbf['summary'].set_top()
        wbf['summary'].set_bottom()
        wbf['summary'].set_left()
        wbf['summary'].set_right()
        
        wbf['note'] = workbook.add_format({'font_size':8, 'align':'left', 'font_name': 'Arial'})

        wbf['summary_float'] = workbook.add_format({'bold':1, 'font_size':10, 'align':'right', 'num_format':'#,##0.00', 'font_name': 'Arial'})
        wbf['summary_float'].set_top()
        wbf['summary_float'].set_bottom()            
        wbf['summary_float'].set_left()
        wbf['summary_float'].set_right()   


        wbf['total_float_yellow'] = workbook.add_format({'bold':1, 'bg_color':colors['yellow'], 'align':'right', 'num_format':'#,##0.00', 'font_name': 'Arial'})
        wbf['total_float_yellow'].set_top()
        wbf['total_float_yellow'].set_bottom()
        wbf['total_float_yellow'].set_left()
        wbf['total_float_yellow'].set_right()
        
        wbf['total_number_yellow'] = workbook.add_format({'align':'right', 'bg_color': colors['yellow'], 'bold':1, 'num_format': '#,##0', 'font_name': 'Arial'})
        wbf['total_number_yellow'].set_top()
        wbf['total_number_yellow'].set_bottom()
        wbf['total_number_yellow'].set_left()
        wbf['total_number_yellow'].set_right()
        
        wbf['total_yellow'] = workbook.add_format({'bold':1, 'bg_color':colors['yellow'], 'align':'center', 'font_name': 'Arial'})
        wbf['total_yellow'].set_left()
        wbf['total_yellow'].set_right()
        wbf['total_yellow'].set_top()
        wbf['total_yellow'].set_bottom()

        wbf['total_float_orange'] = workbook.add_format({'bold':1, 'bg_color':colors['orange'], 'align':'right', 'num_format':'#,##0.00', 'font_name': 'Arial'})
        wbf['total_float_orange'].set_top()
        wbf['total_float_orange'].set_bottom()            
        wbf['total_float_orange'].set_left()
        wbf['total_float_orange'].set_right()         
        
        wbf['total_number_orange'] = workbook.add_format({'align':'right', 'bg_color': colors['orange'], 'bold':1, 'num_format': '#,##0', 'font_name': 'Arial'})
        wbf['total_number_orange'].set_top()
        wbf['total_number_orange'].set_bottom()            
        wbf['total_number_orange'].set_left()
        wbf['total_number_orange'].set_right()
        
        wbf['total_orange'] = workbook.add_format({'bold':1, 'bg_color':colors['orange'], 'align':'center', 'font_name': 'Arial'})
        wbf['total_orange'].set_left()
        wbf['total_orange'].set_right()
        wbf['total_orange'].set_top()
        wbf['total_orange'].set_bottom()
        
        wbf['header_detail_space'] = workbook.add_format({'font_name': 'Arial'})
        wbf['header_detail_space'].set_left()
        wbf['header_detail_space'].set_right()
        wbf['header_detail_space'].set_top()
        wbf['header_detail_space'].set_bottom()
        
        wbf['header_detail'] = workbook.add_format({'bg_color': '#E0FFC2', 'font_name': 'Arial'})
        wbf['header_detail'].set_left()
        wbf['header_detail'].set_right()
        wbf['header_detail'].set_top()
        wbf['header_detail'].set_bottom()
        
        return wbf, workbook

    

class PPMPReport(models.TransientModel):
    _name = "procurement.plan.report"
    _description = "Procurement Plan Report"
    # _order = 'bank_policy_id, date, id'

    wizard_id = fields.Many2one('procurement.plan.wizard', string="Wizard")
    pu_id = fields.Many2one('res.partner', string='Procurement Unit', required=True)
    project_id = fields.Many2one('procurement.project', string='Project')
    product_id = fields.Many2one('product.product', string='Item')
    product_uom_id = fields.Many2one('uom.uom', string='Unit')
    qty = fields.Integer('Quantity')
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
    

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        """
            Override read_group to calculate the sum of the non-stored fields that depend on the user context
        """
        if 'unit_price' in fields:
            fields.remove('unit_price')
 

        res = super(PPMPReport, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
 
        return res

    
class PPMPSummary(models.AbstractModel):
    """Abstract Model for report template.
    for `_name` model, please use `report.` as prefix then add `module_name.report_name`.
    """

    _name = "report.procurement_lgu.ppmp_summary_report_view"

    @api.model
    def render_html(self, docids, data=None):
        self.model = self.env.context.get('active_model')
        self.get_report_values(self.env.context.get('active_id'), data)
        docs = self.env['procurement.plan.wizard'].browse(self.env.context.get('active_id'))
        docargs = {
            'doc_ids': self.ids,
            'doc_model': self.model,
            'docs': docs,
        }
        return self.env['report'].render('procurement_lgu.ppmp_summary_report_view', docargs)

    @api.model
    def get_report_values(self, docids, data=None):
        # datefrom = datetime.strptime(data['form']['datefrom'], '%m%-d-%Y')
        
        pu_id = data['form']['pu_id']
        year = data['form']['year']

        where_clause = ""
                
        if pu_id:
            where_clause += ' partner_id = %s ' % pu_id[0]
        
        if where_clause:
            where_clause = " where " + where_clause

        if not where_clause:
            where_clause = " where " + "pp.year = '%s' and pp.state='approved' " % year
        else:
            where_clause += " and " + "pp.year = '%s' and pp.state='approved' " % year


        sql = ("""
            select %s as wizard_id, ppd.project_id,
            ppd.product_id, ppd.product_uom_id, sum(ppd.qty) qty,  
            sum(ppd.month_01) month_01, sum(ppd.month_02) month_02, sum(ppd.month_03) month_03, sum(ppd.month_04) month_04, 
            sum(ppd.month_05) month_05, sum(ppd.month_06) month_06, sum(ppd.month_07) month_07, sum(ppd.month_08) month_08, 
            sum(ppd.month_09) month_09, sum(ppd.month_10) month_10, sum(ppd.month_11) month_11, sum(ppd.month_12) month_12,
            ppd.unit_price, sum(ppd.est_budget) est_budget, pp.partner_id pu_id, ppd.mode_id                 
            from procurement_plan pp
            inner join procurement_plan_det ppd on ppd.pp_id = pp.id
            %s
            group by 20, 1,2,3,4,18,21
            """) % (self.id, where_clause)

        self.env.cr.execute(sql)
        query_results = self.env.cr.dictfetchall()

        self.env["procurement.plan.report"].search([('wizard_id', '=', data['form']['id'])]).unlink()
        
        
#         temp_balance = 0.00 
#         act_balance = 0.00
               
        rep_obj = self.env['procurement.plan.report']
        for res in query_results:
            dtadet_dict = {}
            dtadet_dict.update({
            'wizard_id': self.env.context.get('active_id'),
            'pu_id' : res['pu_id'],
            'project_id' : res['project_id'],
            'product_id': res['product_id'],
            'product_uom_id': res['product_uom_id'],
            'qty': res['qty'],
            'mode_id': res['mode_id'],
            'month_01': res['month_01'],
            'month_02': res['month_02'],
            'month_03': res['month_03'],
            'month_04': res['month_04'],
            'month_05': res['month_05'],
            'month_06': res['month_06'],
            'month_07': res['month_07'],
            'month_08': res['month_08'],
            'month_09': res['month_09'],
            'month_10': res['month_10'],
            'month_11': res['month_11'],
            'month_12': res['month_12'],
            'unit_price': res['unit_price'],
            'est_budget': res['est_budget']
            })

            rep_obj.create(dtadet_dict)
    
