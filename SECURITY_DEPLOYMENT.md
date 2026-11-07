# FitTogether Security Deployment Notes

This document describes the Phase 1 security controls added to the Flask application.

## Required production environment

Configure these values in your hosting provider before deploying:

- `APP_ENV=production`
- `SECRET_KEY`: a stable, randomly generated secret (at least 32 random bytes). Generate one with `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
- `DATABASE_URL`: your existing production database connection string.
- `RATELIMIT_STORAGE_URI`: a Redis connection URI, for example `redis://:<password>@<host>:6379/0`, using your provider's TLS URI where required.

Do not commit real secrets or database credentials to Git. Keep the same SECRET_KEY across application workers and restarts. The app detects Render and Railway deployments as production environments as well.

The default rate-limit storage is in-memory for local development only. Use Redis in production so limits are shared across workers and survive process restarts.

## Phase 1 controls

- Flask-WTF CSRF protection is enabled globally; all POST forms include a CSRF token.
- Logout now uses POST, rather than a state-changing GET request.
- Production startup fails if SECRET_KEY is missing.
- Session cookies use HttpOnly and SameSite=Lax; Secure is enabled in production.
- Authenticated sessions are made permanent with a 12-hour lifetime and reset on login.
- Login and signup routes have rate limits.
- Password minimum length is 12 characters for new registrations and password changes.
- Email addresses are normalized and validated; usernames are checked case-insensitively at the application layer.
- Profile uploads are limited to 3 MB per request, use allow-listed extensions, validate actual image format and dimensions, and are stored under random filenames.
- Password changes revoke the current browser session.

## Existing database compatibility

No database tables or user records are deleted or recreated by this change. The existing `users` table does not currently enforce username uniqueness at the database level. Application-level duplicate checks are included, but a database migration and duplicate-data review are still required before adding a unique index safely.

## Before production release

1. Set all required environment variables above.
2. Configure Redis and verify the rate-limit URI from the application host.
3. Run a registration, login, logout, password-change, profile-update, and profile-image upload smoke test.
4. Confirm HTTPS is enabled so Secure session cookies are sent.
5. Review any existing duplicate usernames before applying a database uniqueness migration.
6. Run dependency and application tests in CI before merging this branch.
