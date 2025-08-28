# -*- coding: utf-8 -*-
{
    'name': "FMIS",

    'summary': """
        This module is for FMIS of Local Government""",

    'description': """
        Financial Management Information System
    """,

    'author': "Herman Suoberon",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['account'],

    # always loaded
    'data': [
        'security/fmis_security.xml',
        'views/accountable_forms_view.xml',
        'views/disbursement_view.xml',
        'views/collection_view.xml',
        'views/cheque_clearing_view.xml',
        'views/deposit_view.xml',
        'data/data.xml',

        # 'views/procurement_report.xml',
        # 'views/report_procurement_plan.xml',
        # 'views/report_po.xml',
        # 'views/report_rfq.xml',
        # 'views/report_aoc.xml',
        # 'views/report_aob.xml',
        # 'views/report_noticeofaward.xml',
        # 'views/report_noticetoproceed.xml',
        # 'views/report_minutes.xml',
        # 'views/config.xml',
        # 'views/rfq.xml',
        'security/ir.model.access.csv',
#         'views/views.xml',
#         'views/templates.xml',
#         'views/budgeting.xml',
#         'views/budgeting_report.xml',
#          'views/layout.xml',
#         'views/report_pr.xml',
#         'views/report_obr.xml',
#         'views/report_aug.xml',
#         'views/report_app.xml',
#         'wizard/ppmp_summary_view.xml',
#         'wizard/ppmp_balance_view.xml',
#         'wizard/budgeting_wizard_view.xml',
#         'wizard/appstmt_report.xml',
#         'wizard/budgeting_report.xml',
#         'wizard/budgeting_summary_view.xml',
        'views/menu_view.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],

}
