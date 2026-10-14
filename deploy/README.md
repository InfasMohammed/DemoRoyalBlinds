# Deployment guide

Deploy Royal Blinds Operations Studio using Google Cloud project **demoroyalblinds**, Cloud Run for FastAPI, Vercel for React, and the existing rbdemo Supabase project. Invited users access the Vercel link with a Supabase Auth account and have equal access to the shared sample dataset, including quotation creation, knowledge/material additions, approvals and work-order progress. The current deployment supports controlled evaluation; live factory integration and organization-level data isolation require further implementation.

Cloud Run requires billing to be enabled. The free allowance may cover a small demo, but builds, image storage, secrets, networking and usage beyond allowances can incur charges. Check current pricing for your account and region. Configure a budget alert; alerts do not stop charges. The script sets zero minimum instances and at most two instances. A first request can wait for a cold start.

## 1. Create reviewer accounts

In Supabase **Authentication → Users**, create confirmed email/password accounts for yourself and invited reviewers. Supply passwords securely outside the repository/chat. This frontend supports sign-in only; account creation and password recovery are managed by the demo owner through Supabase. Record the allowed emails for step 3. An unlisted account receives 403 even if it successfully signs in.

Keep Supabase RLS and anonymous-table restrictions in place. Backend secrets are the Supabase server secret/service-role key and NVIDIA API key. The browser uses only a Supabase publishable key (`sb_publishable_...`) or legacy anon key. This release requires no new SQL migration if your existing post-approval schema is installed.

## 2. Store backend secrets in Google Cloud

Select **demoroyalblinds** in Google Cloud Console and create these secrets in **Secret Manager**, with an enabled version:

| Name                  | Value entered securely in Google Cloud Console |
| --------------------- | ---------------------------------------------- |
| `rbdemo-supabase-key` | Supabase server secret/service-role key        |
| `rbdemo-nvidia-key`   | NVIDIA API key                                 |

The script grants the runtime service account access to these two secrets. Values are injected into Cloud Run at startup, not copied into the image or frontend. The Google account performing deployment needs permissions to enable APIs, build/push images, deploy Cloud Run, create/use the runtime service account and grant its secret access. Runtime permission does not grant deployment permission.

## 3. Deploy the backend from Cloud Shell

Open **Google Cloud Shell**. These are Bash commands for that hosted terminal; local Windows CMD instructions are unchanged. Cloud Build creates the Docker image, so you do not need Docker installed on your laptop.

```bash
git clone https://github.com/InfasMohammed/DemoRoyalBlinds.git
cd DemoRoyalBlinds
git pull --ff-only origin main
mkdir -p .runtime
cp deploy/cloud-run.env.example.yaml .runtime/cloud-run.env.yaml
cloudshell edit .runtime/cloud-run.env.yaml
```

Reuse an existing checkout if already cloned. For a private GitHub repository, use its supported login flow or upload a downloaded repository ZIP; never put a GitHub token into these commands.

Edit `AUTH_ALLOWED_EMAILS` to your confirmed reviewer emails. Verify the Supabase URL and NVIDIA model. Set `CORS_ORIGINS` to the anticipated Vercel production URL; update it in step 5 if Vercel assigns a different URL. Keep production authentication, Supabase data and the disabled idle worker as configured in the template. Do not put API keys in this YAML file.

```bash
export GOOGLE_CLOUD_PROJECT=demoroyalblinds
export CLOUD_RUN_REGION=us-central1
bash deploy/cloud-run.sh
```

The script checks project/billing access, enables APIs, verifies the secret names, creates an image repository/runtime identity when absent, builds the image and deploys `rbdemo-api`. It checks that an anonymous API request returns 401 and prints the backend origin. Complete step 6 to verify authenticated reads, actual NVIDIA responses and business actions before sharing.

Cloud Build's build identity needs image-writer and logging permissions. A restricted default identity or organization policy may require an administrator to grant the reported missing permission. Diagnose the reported build identity instead of granting broad roles to the runtime account.

## 4. Deploy the frontend on Vercel

Import `InfasMohammed/DemoRoyalBlinds`, select `main`, and configure:

| Setting          | Value                         |
| ---------------- | ----------------------------- |
| Root Directory   | `frontend`                    |
| Framework        | Vite                          |
| Build Command    | `npm run build`               |
| Output Directory | `dist`                        |
| Node.js          | 22 or newer supported version |

Set these **Production** environment variables before building:

| Variable                        | Value                                        |
| ------------------------------- | -------------------------------------------- |
| `VITE_API_BASE_URL`             | Cloud Run origin from step 3, without `/api` |
| `VITE_REQUIRE_AUTH`             | `true`                                       |
| `VITE_SUPABASE_URL`             | `https://neeupsyqguamtfmpanmp.supabase.co`   |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | Supabase publishable or legacy anon key      |

Vite embeds these at build time; redeploy after changing them. Never set a server key, NVIDIA key or LLM key in a `VITE_` variable. The build rejects Vercel deployments without authentication, malformed origins and browser server keys. Browser requests go directly to Cloud Run, with the user's access token, rather than through a Vercel function or local Vite proxy.

Vercel can rebuild the frontend after Git pushes. The initial backend deployment is manual; a Git push does not create Google billing resources or deploy the backend automatically.

## 5. Set the exact frontend origin

If Vercel's URL differs from `CORS_ORIGINS`, update Cloud Run in Cloud Shell:

```bash
gcloud run services update rbdemo-api \
  --project=demoroyalblinds --region=us-central1 \
  --update-env-vars=CORS_ORIGINS=https://YOUR-ACTUAL-PROJECT.vercel.app
```

Also update `.runtime/cloud-run.env.yaml` for future deployments. Use an exact HTTPS origin without a path/trailing slash. Share the production URL for this first demo; unlisted Vercel preview origins are not allowed. Add the exact custom-domain origin when you configure one.

Cloud Run's `--allow-unauthenticated` permits browsers to reach the HTTPS endpoint. Every application API route still requires a Supabase-verified, confirmed user and an invited email. Production startup rejects disabled authentication. API documentation is hidden in private mode.

## 6. Verify the shared link

1. Open Vercel in an incognito window and confirm the sign-in screen appears. An anonymous request to Cloud Run `/api/projects` must return 401.
2. Sign in with an invited reviewer. Confirm the Material library and knowledge sources show current Supabase data. An unlisted confirmed account must receive 403.
3. Analyze a small synthetic quotation with stocked material and a flexible deadline. Inspect all six findings, actual AI/fallback labels and the saved quotation.
4. Approve with every confirmation. Verify one reservation/work order, then test production, quality and installation. Use a separate quotation to test cancellation/release.
5. Reopen the saved report, sign out, and confirm sign-in is required again.

New authenticated approvals record verified user ID/email alongside the display name. Progress uses the verified email as its actor. Existing reports are preserved. Per-role permissions, tenant isolation, rate controls and broader audit requirements remain work for a real business rollout.

Quotation requests remain synchronous and wait for agent commentary. Cloud Run uses a 600-second timeout to accommodate that existing workflow. For delayed responses, inspect browser Network and Cloud Run request logs; check saved reports before submitting the same quotation again.

The idle approval worker is disabled with request-based Cloud Run CPU. Approval performs execution within its request; Retry execution recovers durable pending/blocked jobs. Automatic idle recovery needs a separate worker/scheduled service or an explicitly budgeted always-on CPU configuration.

## Local container and browser checks

```bash
docker build -t rbdemo-backend .
docker run --rm -p 8080:8080 \
  -e APP_ENV=development -e AUTH_REQUIRED=false -e BUSINESS_DATA_SOURCE=demo \
  rbdemo-backend
```

This local override uses credential-free sample calculations. The image defaults to production authentication and Supabase persistence. Its build accepts an optional BuildKit secret named `build_ca` for a managed TLS proxy: mount that environment's trusted CA bundle without disabling certificate verification. It is used only during dependency installation and is not copied into the runtime image.

Run `npm run test:auth` from `frontend` after installing Playwright Chromium (or set `CHROMIUM_PATH` to an existing browser). These tests mock Supabase sign-in and verify gating, session persistence, bearer headers, direct API routing and sign-out. Backend tests independently verify Supabase token validation and invited-user enforcement. Mocked tests do not establish live account access.
