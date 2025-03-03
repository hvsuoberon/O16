# -*- coding: utf-8 -*-
{
    'name': "Budgeting",

    'summary': """
        This module is for Budgeting Module of Local Government""",

    'description': """
        Budgeting Module
    """,

    'author': "Herman Suoberon",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','account'],

    # always loaded
    'data': [
        'security/budgeting_security.xml',
        'views/budgeting_data.xml',
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        'views/budgeting.xml',
        'views/budgeting_report.xml',
        'views/layout.xml',
        'views/report_pr.xml',
        'views/report_obr.xml',
        'views/report_aug.xml',
        'views/report_app.xml',
        'wizard/report_wizard_view.xml',
        'wizard/budgeting_wizard_view.xml',
        'wizard/appstmt_report.xml',
        'wizard/budgeting_report.xml',
        'wizard/budgeting_summary_view.xml',
        'wizard/budgeting_summary.xml',
        'wizard/budgeting_summary_with_at_view.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}