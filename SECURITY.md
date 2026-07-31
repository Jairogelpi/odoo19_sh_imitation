# Security policy

Flight Recorder can observe sensitive business operations. Security and data
minimization are part of the product contract.

## Defaults

- Capture metadata, field names, and hashes; do not capture business values.
- Deny known secret keys even when value capture is explicitly enabled.
- Restrict trace access to Odoo system administrators.
- Never export credentials, sessions, API keys, payment data, or raw passwords.
- Treat incident bundles as sensitive artifacts.

Do not report vulnerabilities in a public issue. Contact the repository owner
privately through GitHub security advisories.

