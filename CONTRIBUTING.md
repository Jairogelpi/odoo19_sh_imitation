# Contributing

Flight Recorder is evidence-first. A feature is complete only when its behavior,
privacy boundary, overhead, and failure mode are tested.

## Before opening a pull request

1. Describe the Odoo incident or developer problem being solved.
2. Keep the change within the smallest responsible component.
3. Add a failing test before the implementation.
4. Run `pytest` and `ruff check .`.
5. Do not commit databases, dumps, filestores, recordings with personal data,
   virtual environments, generated caches, model weights, or credentials.

Changes that instrument Odoo internals must state the supported Odoo series and
include an integration test against that series.

