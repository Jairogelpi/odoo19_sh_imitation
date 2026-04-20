import xmlrpc.client

url = 'http://localhost:8069'
db = 'odoo19'
user = 'admin'
password = 'admin'

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, user, password, {})
print('uid', uid)

models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
try:
    result = models.execute_kw(db, uid, password, 'openclaw.chat.session', 'rpc_create_session', [[]])
    print(result)
except Exception as exc:
    print(type(exc).__name__)
    print(exc)
