# v3 audit

Added 120 course-specific six-topic curricula, PDF guides and narrated overview videos. Included study materials cover foundation-to-applied practice; full specialist instructor curricula and demonstration recordings remain outstanding.

Implemented administrator-owned pricing, server-controlled paywalls, Paystack hosted checkout/verification/signed webhooks, replay-safe settlement and access revocation. Added Resend verification and reset messages with hashed expiring single-use tokens, reset session invalidation, secure production cookies, rate limits, origin checks and deployment configuration.

Fixed account initialization rejecting JSON-header GET requests, an early-navigation listener race, and course editing dropping included media metadata. Full course data and protected PDFs are not served through public static paths by app.py. Public short overview videos support previews. Static guest preview has no payment protection.

No live provider activation, hosting deployment or DNS changes were made. Expert curriculum approval, actual provider tests, HTTPS/domain validation, backup restoration, monitoring and browser/device playback acceptance must happen before a public launch. This audit is not a penetration test. SQLite and one-worker hosting suit an initial academy; concurrent scale and larger media require separate design and load testing.
