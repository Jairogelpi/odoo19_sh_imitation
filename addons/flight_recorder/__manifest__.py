{
    "name": "Flight Recorder",
    "summary": "Evidence-first causal traces for Odoo incidents",
    "version": "19.0.2.0.0",
    "category": "Technical",
    "author": "Jairo Gelpi Moreno",
    "website": "https://github.com/Jairogelpi/odoo19_sh_imitation",
    "license": "AGPL-3",
    "depends": ["base", "sale"],
    "data": [
        "security/ir.model.access.csv",
        "views/flight_recorder_views.xml",
    ],
    "installable": True,
    "application": False,
}
