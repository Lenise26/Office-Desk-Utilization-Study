# Security and privacy notes

This project is designed for **anonymous workspace observations**. The database schema has no employee name, email, badge number, device identifier, or other identity field.

Recommended deployment practices:

- Restrict the application to authorized managers and observers.
- Put production deployments behind HTTPS and an authenticated reverse proxy or SSO gateway.
- Keep the SQLite data file on encrypted storage with routine backups.
- Define a retention period for raw observations and delete records that are no longer needed.
- Avoid adding free-text fields that could accidentally contain personal information.
- Review local workplace, privacy, labor, and surveillance requirements before collecting observations.

To report a security issue, use a private channel rather than opening a public issue with sensitive details.
