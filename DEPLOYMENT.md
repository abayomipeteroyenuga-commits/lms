# Production activation — lms.ethandigitalacademy.org

The package is deployment-ready source, not an already hosted service. A hosting account, domain DNS access, verified email sender and payment merchant account are required. Enter secrets only in the provider's environment settings; never paste them into chat or commit them to Git.

## Render deployment

1. Upload the contents of this folder to a private Git repository, excluding .env, data, backups and caches. Create a Render Blueprint from render.yaml. It specifies a paid Starter web service and persistent disk; review current hosting charges before creating the service.
2. Set ETHAN_ADMIN_EMAIL and a strong ETHAN_ADMIN_PASSWORD, PAYSTACK_SECRET_KEY (test initially), RESEND_API_KEY, and ETHAN_EMAIL_FROM to a sender verified in Resend. The supplied sender is an example until your domain is verified.
3. Add lms.ethandigitalacademy.org as a custom domain in the hosting dashboard. Copy the exact DNS record values shown there to your DNS provider; wait for domain verification and HTTPS provisioning. Keep ETHAN_BASE_URL=https://lms.ethandigitalacademy.org. Set ETHAN_ALLOWED_HOSTS to lms.ethandigitalacademy.org and the assigned hosting service hostname if the health checker uses it.
4. Confirm /api/health returns server=true, then sign in as administrator. Remove ETHAN_ADMIN_PASSWORD from hosting settings after first successful account creation. Keep the persistent disk at /var/data; redeployment must retain the database.
5. Configure Paystack's webhook URL as https://lms.ethandigitalacademy.org/api/payments/webhook. The callback URL is generated from ETHAN_BASE_URL. Begin with a test secret and test checkout; confirm the return and a signed webhook grant access only once. Then switch to the live secret only after the merchant account is approved and you are ready to collect fees.
6. Configure the email sender's DNS records using Resend's exact domain-verification instructions. Register a real learner, request verification, confirm the email link, and test password reset. Verify unverified users remain blocked from full lessons and PDFs.
7. Set fees in the administrator Fees and payments page. Enable only courses whose curriculum you have reviewed. Test a paid purchase, a free verified course, an assignment review and persistence across a restart before announcing launch.

## Production environment

ETHAN_ENV=production; ETHAN_SECURE_COOKIE=1; ETHAN_REQUIRE_VERIFIED_EMAIL=1; ETHAN_BASE_URL must be HTTPS. Use ETHAN_TRUST_PROXY=1 only behind the hosting provider's trusted reverse proxy. Gunicorn runs one worker with four threads for this SQLite deployment. Local development uses python app.py; do not use the Flask development server for production.

## Backups and payment operations

Run python backup.py in the hosting shell and securely copy the database backup off the service. Include backups in a regular operational schedule, test restoration, and monitor disk use, provider errors and health. Uploaded media are stored as database BLOBs. The included overview videos/PDFs ship with the source.

Administrator access revocation removes LMS access; it does not issue a refund. Handle refunds and reconciliation in the Paystack dashboard. Verify a transaction's final provider status before granting manual access. Fees are NGN only; recurring subscriptions and automated refunds are not implemented.

## Official references

- https://render.com/docs/blueprint-spec
- https://render.com/docs/disks
- https://render.com/docs/custom-domains
- https://paystack.com/docs/api/transaction/
- https://paystack.com/docs/payments/webhooks/
- https://resend.com/docs/api-reference/emails/send-email
- https://flask.palletsprojects.com/en/stable/deploying/gunicorn/
