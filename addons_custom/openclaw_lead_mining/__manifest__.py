{
    'name': 'OpenClaw Lead Mining',
    'version': '19.0.1.0.0',
    'category': 'Sales/CRM',
    'summary': 'Genera crm.lead desde OpenStreetMap vía lead-mining-mcp (sin créditos Odoo)',
    'author': 'Smart System for Information Technology',
    'website': 'https://smartsystem.sa',
    'license': 'LGPL-3',
    'depends': ['openclaw', 'crm', 'crm_iap_mine'],
    'data': [
        'security/ir.model.access.csv',
        'wizards/openclaw_lead_mining_wizard_views.xml',
        'views/crm_lead_actions.xml',
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
}
