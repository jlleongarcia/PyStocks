# Deployment

This guide covers deploying MarketMind in a production environment, including HTTPS reverse proxy configuration and the FX rate service.

---

## Environment Configuration

Copy `.env.example` to `.env` and update the following for production:

```env
DEBUG=False
SECRET_KEY=<generate a secure random key — see below>
ALLOWED_HOSTS=your-domain.com

# Required when behind an HTTPS proxy (Cloudflare, Nginx, etc.)
CSRF_TRUSTED_ORIGINS=https://your-domain.com

# Self-hosted Frankfurter v2 for FX rates
FX_RATE_SERVICE_URL=http://<host>:<port>

# Email notifications (optional)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=user@example.com
EMAIL_HOST_PASSWORD=<password>
```

**Generate a secure secret key:**
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## Deployment Steps

```bash
cp .env.example .env
# Edit .env with production values

docker compose up -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py collectstatic --noinput
docker compose exec web python manage.py createsuperuser
```

---

## Cloudflare Tunnel

MarketMind works behind Cloudflare Tunnel with no additional infrastructure. The proxy-aware settings are already in place in `settings.py`:

```python
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
```

The only thing you must configure is `CSRF_TRUSTED_ORIGINS` in `.env`:

```env
CSRF_TRUSTED_ORIGINS=https://marketmind.your-domain.com
```

> **Without this setting, all POST requests through Cloudflare will return 403 Forbidden.** This is Django's CSRF protection rejecting requests whose `Origin` header doesn't match a trusted origin.

After updating `.env`:
```bash
docker compose restart web
```

---

## FX Rate Service

MarketMind uses a self-hosted [Frankfurter v2](https://github.com/hakanensari/frankfurter) instance for currency conversion. The service is queried at `GET /v2/rate/{from}/{to}?date=YYYY-MM-DD`.

Deploy Frankfurter alongside the main app (e.g. on port 8301) and point to it via `.env`:

```env
FX_RATE_SERVICE_URL=http://<host>:8301
```

If a rate is unavailable (weekend, bank holiday), the app automatically retries up to five prior business days. If still unavailable, the transaction form shows a warning and allows manual rate entry.

---

## Static Files

Static files are served by WhiteNoise — no Nginx or CDN required. Always run `collectstatic` after pulling frontend changes:

```bash
docker compose exec web python manage.py collectstatic --noinput
```

---

## Updating

```bash
git pull origin main
docker compose build
docker compose up -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py collectstatic --noinput
```

---

## Monitoring

```bash
make status       # Container status
make logs-web     # Web container logs
make logs-db      # Database logs
```
