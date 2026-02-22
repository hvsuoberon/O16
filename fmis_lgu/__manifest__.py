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
        'views/default_value_view.xml',
        'data/data.xml',

        'security/ir.model.access.csv',

        'views/menu_view.xml',
        'reports/advice.xml',
        'reports/reports.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],

}
