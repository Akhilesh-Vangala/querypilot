# Product routes and optional accounts

`api.py` attaches explicit account routes; the React router owns product pages. `accounts.py` delegates optional sessions to a configured Supabase provider and saves owner-isolated snapshots through user-token PostgREST. Missing configuration is an explicit disabled state. No service/admin key, cross-user global history or client-asserted verified report is accepted.

[Workflow, contracts, storage, security and verification](../../../docs/product/PRODUCT-WORKSPACE.md) · [SQL migration](../../../infrastructure/supabase/migrations/001_product_workspace.sql).
