# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'stark',
    'category': 'course',
    'summary': 'book',
    'sequence': -1,
    'version': '1.0',
    'description': """Payment Acquirer Base Module""",
    'depends': ['base','purchase','crm'],
    'data': [

        'security/ir.model.access.csv',
        'views/stark_re.xml',



    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
