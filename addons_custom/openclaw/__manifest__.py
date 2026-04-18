{
    'name': 'OpenClaw Agent',
    'version': '19.0.1.0.0',
    'category': 'Productivity',
    'summary': 'Permissioned AI agent bridge for Odoo and external MCP tools',
    'author': 'Smart System for Information Technology',
    'website': 'https://smartsystem.sa',
    'license': 'LGPL-3',
    'icon': '/openclaw/static/description/icon.svg',
    'depends': ['base', 'base_setup', 'web'],
    'data': [
        'security/openclaw_security.xml',
        'security/ir.model.access.csv',
        'data/openclaw_policy_data.xml',
        'views/openclaw_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'openclaw/static/src/js/openclaw_chat.js',
            'openclaw/static/src/scss/openclaw_chat.scss',
            'openclaw/static/src/xml/openclaw_chat.xml',
        ],
        'web.assets_web': [
            'openclaw/static/src/js/openclaw_chat.js',
            'openclaw/static/src/scss/openclaw_chat.scss',
            'openclaw/static/src/xml/openclaw_chat.xml',
        ],
    },
    'application': True,
    'installable': True,
    'auto_install': False,
}
