# Optional account persistence

The [migration](migrations/001_product_workspace.sql) defines owner-isolated, immutable account snapshots. It does not provision a hosted service or establish successful production authentication, email or backups.

[Operator setup, consent, session behavior and verification](../../docs/product/PRODUCT-WORKSPACE.md#optional-cloud-accounts). The local policy check creates/drops its own random test database and requires an explicit test administrative URL:

```sh
QUERY_PRODUCT_TEST_ADMIN_URL=postgresql://test-host/test-db python scripts/checks/product_rls.py
```

Do not use customer/hosted production credentials for this script. The application needs only the configured HTTPS provider URL and publishable/anon key; it refuses service/admin keys.
