"""Account routes; React owns product presentation and routing."""
WRITE_PATHS = {"/api/account/sign-in", "/api/account/sign-up", "/api/account/sign-out", "/api/account/refresh", "/api/account/projects", "/api/account/projects/delete", "/api/account/investigations", "/api/account/investigations/delete"}
def attach(app, root=None):
    from .accounts import attach as attach_accounts
    attach_accounts(app)
