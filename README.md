# ETHAN LMS v3

120 digital courses with 720 topic lessons, 2,880 knowledge-check questions, 120 PDF study guides and 120 narrated slide overview videos. Includes reading, PDF, video, speech narration, practice, assessment, notes, bookmarks, planner, progress, learner accounts and administrator review.

## Run the account-enabled LMS

Use Python 3.12 or compatible installed Python:

```sh
python -m pip install -r requirements.txt
cp .env.example .env
python app.py
```

Before starting, edit .env with your administrator email and a strong unique administrator password (at least 10 characters). Open http://localhost:8080. Remove the bootstrap password from environment settings after the administrator has been created. Never publish a filled .env or the data directory. The SQLite database stores accounts, progress, uploads and payments.

Administrators use Fees and payments to enable each course and set its NGN fee; zero means free. All courses initially remain in draft for full access. Learners can preview the first lesson. Verified learners can access enabled free courses, or purchase an enabled paid course through Paystack. Administrators can edit courses, upload further teaching resources, review assignments and inspect learner reports.

## Content and media scope

The included course-specific notes, practical scenarios and checks cover foundation-to-applied practice. They are newly generated educational material, not a specialist-accredited curriculum. Instructor review and deeper projects, demonstrations and specialist modules remain necessary for advanced professional training. Videos are short synthesized-voice slide overviews, not full instructor demonstrations. PDF files include assessment answers for self-study; assessments are not secure examinations. Completion records do not confer an external qualification.

The static index.html preview has browser-local guest features and bundled content. Static preview does not enforce paid access. Deploy app.py for accounts, server-controlled course access and payments. The app server deliberately serves a metadata-only courses.js and gates full course data and PDFs.

## Activation and deployment

Read DEPLOYMENT.md for lms.ethandigitalacademy.org. Paystack and Resend integrations are implemented but need your own provider settings. No live transactions, emails, DNS changes or deployment have been performed. Dockerfile, compose.yaml and render.yaml are included; production uses Gunicorn and persistent storage.

## Verification and operations

```sh
python tests/test_server.py
python tests/test_commerce.py
python backup.py
```

Backups contain private user data: retain them securely outside the public site. To restore, stop the app, preserve the current database and replace it with a verified backup. Test restoration before relying on a backup. See TEST-RESULTS.md and AUDIT.md for coverage and limitations.

## Compact distribution

This edition contains exactly 81 files. All 240 original PDF/video assets are stored losslessly inside 55 media packs. Keep teaching/pack-*.zip intact: the server and static guest preview read them directly. Media packs remain private on the account server.

## Vercel display fix

Upload the extracted folder contents to GitHub, including index.html, vercel.json and build.mjs. Do not upload the ZIP itself as the site. In Vercel use Framework Preset Other, Build Command node build.mjs, Output Directory dist. Root Directory must be the directory containing vercel.json; leave it blank if these files are at repository root. Remove previous Python/Flask framework overrides and redeploy.

This Vercel build publishes a browser-local learning site. Courses, assessments, PDF guides, videos and narration work in guest mode. It does not deploy the SQLite backend or enforce paid course access. Keep this deployment as a preview if you intend to sell courses; use the persistent-backend instructions in DEPLOYMENT.md for the account-enabled academy. Backend source remains included but is excluded from the public build.

If a stale blank screen remains after redeployment, open in a private window or clear the old site service worker/cache.

# v3 audit

Added 120 course-specific six-topic curricula, PDF guides and narrated overview videos. Included study materials cover foundation-to-applied practice; full specialist instructor curricula and demonstration recordings remain outstanding.

Implemented administrator-owned pricing, server-controlled paywalls, Paystack hosted checkout/verification/signed webhooks, replay-safe settlement and access revocation. Added Resend verification and reset messages with hashed expiring single-use tokens, reset session invalidation, secure production cookies, rate limits, origin checks and deployment configuration.

Fixed account initialization rejecting JSON-header GET requests, an early-navigation listener race, and course editing dropping included media metadata. Full course data and protected PDFs are not served through public static paths by app.py. Public short overview videos support previews. Static guest preview has no payment protection.

No live provider activation, hosting deployment or DNS changes were made. Expert curriculum approval, actual provider tests, HTTPS/domain validation, backup restoration, monitoring and browser/device playback acceptance must happen before a public launch. This audit is not a penetration test. SQLite and one-worker hosting suit an initial academy; concurrent scale and larger media require separate design and load testing.

# v3 verification

Passed Python API regression: registration, authentication, roles, state/upload isolation, origin rejection, shared resources, assignment grading and course authoring.

Passed payment/email integration tests with mocked provider transport: draft/free/paid access, protected private paths, video range delivery, administrator prices, verification expiry/replay, password reset and session invalidation, provider-unconfigured errors, server-owned amounts, transaction ownership, amount mismatch, confirmed access, signed/idempotent webhooks and revocation. No real emails or transactions occurred.

Passed guest JavaScript DOM workflows: 120-course catalogue, search/bookmarks, progression, practice and quiz, resume, narration control, print, planner, notes, settings, authoring, PDF/video embedding, backup and reports.

Passed account-enabled JavaScript DOM integration against Flask: learner registration, verification request and confirmation, paywall, administrator fee, payment-return verification, unlocked PDF, assignment submission/review, course editing retaining media, and learner reports. Provider transport mocked. Found and fixed JSON-header GET validation and early-navigation initialization issues.

All 120 PDF files and 120 video files are checked for valid format; representative PDFs and slide imagery visually reviewed. Video checks confirm audio and video streams. This is DOM and API testing, not a complete real-browser/device acceptance test. Real audio playback, hosted checkout, inbox delivery, DNS/HTTPS and production restart/restore remain launch checks. Docker runtime unavailable in this workspace; supplied Docker files have not been built here.
