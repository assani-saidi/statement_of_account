# -*- coding: utf-8 -*-
{
    'name': "Statement of account",

    'summary': """
        Creates custom statement of account printable in customers model""",

    'description': """
        Creates custom statement of account printable in customers model
    """,

    'author': "Assani Saidi",
    'website': "https://github.com/assani-saidi",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '16.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'sale', 'account', 'mrp_subcontracting'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        'views/actions.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],
}
