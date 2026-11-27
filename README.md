# Food Donation Management System

## Configuration

The app requires a private Flask session key. Set `FLASK_SECRET_KEY` in the
deployment environment. Generate one with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

To provision the administrator account, set both `ADMIN_EMAIL` and
`ADMIN_PASSWORD` in the deployment environment. The app hashes the password
when it creates or updates the account. Do not put these values in source code
or display them on the login page. If the variables are unset, the old public
`admin@gmail.com` demo account is removed during database initialization.

On Render, add these variables under the web service's **Environment** settings
before deploying this version. Set `FLASK_DEBUG` only to `1` for local debugging;
debug mode is off by default.
