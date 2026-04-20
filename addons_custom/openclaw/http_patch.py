from odoo.http import Session, request


_original_authenticate = Session.authenticate


def _authenticate_with_default_remote_addr(self, env, credential):
    try:
        httprequest = getattr(request, "httprequest", None)
        if httprequest is not None:
            httprequest.environ.setdefault("REMOTE_ADDR", "127.0.0.1")
    except Exception:
        pass
    return _original_authenticate(self, env, credential)


Session.authenticate = _authenticate_with_default_remote_addr