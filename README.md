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
