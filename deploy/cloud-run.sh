#!/usr/bin/env bash
# Run in Google Cloud Shell from this checkout; never put keys in arguments.
set -euo pipefail

project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"
: "${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT to your Google Cloud project ID.}"
region="${CLOUD_RUN_REGION:-us-central1}"
env_file="${CLOUD_RUN_ENV_FILE:-$project_root/.runtime/cloud-run.env.yaml}"
service="rbdemo-api"
repository="rbdemo"
account="rbdemo-runtime@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com"

command -v gcloud >/dev/null || { echo 'Run this in Google Cloud Shell, which includes gcloud.' >&2; exit 1; }
test -f "$env_file" || { echo 'Copy deploy/cloud-run.env.example.yaml to .runtime/cloud-run.env.yaml and edit it first.' >&2; exit 1; }
if grep -Eq 'you@example[.]com|reviewer@example[.]com' "$env_file"; then
    echo 'Replace the example AUTH_ALLOWED_EMAILS with your confirmed Supabase Auth account emails before deploying.' >&2
    exit 1
fi
gcloud projects describe "$GOOGLE_CLOUD_PROJECT" --format='value(projectId)'
billing="$(gcloud billing projects describe "$GOOGLE_CLOUD_PROJECT" --format='value(billingEnabled)')"
test "$billing" = 'True' || test "$billing" = 'true' || { echo 'Enable billing for this project before deploying.' >&2; exit 1; }

gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
    secretmanager.googleapis.com iam.googleapis.com --project="$GOOGLE_CLOUD_PROJECT"
for secret_name in rbdemo-supabase-key rbdemo-nvidia-key; do
    gcloud secrets describe "$secret_name" --project="$GOOGLE_CLOUD_PROJECT" >/dev/null || {
        echo "Create $secret_name in Google Secret Manager, then rerun. Do not paste its value into chat." >&2
        exit 1
    }
    state="$(gcloud secrets versions describe latest --secret="$secret_name" --project="$GOOGLE_CLOUD_PROJECT" --format='value(state)')"
    test "$state" = 'ENABLED' || { echo "Enable a current version of $secret_name before deploying." >&2; exit 1; }
done

if ! gcloud artifacts repositories describe "$repository" --location="$region" --project="$GOOGLE_CLOUD_PROJECT" >/dev/null 2>&1; then
    gcloud artifacts repositories create "$repository" --repository-format=docker --location="$region" --project="$GOOGLE_CLOUD_PROJECT"
fi
if ! gcloud iam service-accounts describe "$account" --project="$GOOGLE_CLOUD_PROJECT" >/dev/null 2>&1; then
    gcloud iam service-accounts create rbdemo-runtime --display-name='Royal Blinds demo runtime' --project="$GOOGLE_CLOUD_PROJECT"
fi
for secret_name in rbdemo-supabase-key rbdemo-nvidia-key; do
    gcloud secrets add-iam-policy-binding "$secret_name" --member="serviceAccount:$account" \
        --role=roles/secretmanager.secretAccessor --project="$GOOGLE_CLOUD_PROJECT" >/dev/null
done

tag="$(git rev-parse --short HEAD 2>/dev/null || date -u +%Y%m%d%H%M%S)"
image="${region}-docker.pkg.dev/${GOOGLE_CLOUD_PROJECT}/${repository}/backend:${tag}"
gcloud builds submit --config=deploy/cloudbuild.yaml --substitutions="_IMAGE=$image" --project="$GOOGLE_CLOUD_PROJECT" .
gcloud run deploy "$service" --image="$image" --region="$region" --project="$GOOGLE_CLOUD_PROJECT" \
    --service-account="$account" --allow-unauthenticated \
    --env-vars-file="$env_file" \
    --set-secrets=SUPABASE_SERVICE_ROLE_KEY=rbdemo-supabase-key:latest,LLM_API_KEY=rbdemo-nvidia-key:latest \
    --cpu=1 --memory=1Gi --concurrency=8 --timeout=600 --min-instances=0 --max-instances=2

service_url="$(gcloud run services describe "$service" --region="$region" --project="$GOOGLE_CLOUD_PROJECT" --format='value(status.url)')"
status="$(curl -sS -o /dev/null -w '%{http_code}' "$service_url/api/projects")"
test "$status" = 401 || { echo "Expected anonymous requests to be rejected with 401; received $status. Check the deployment before sharing." >&2; exit 1; }
echo "Backend deployed with sign-in required: $service_url"
echo 'Set VITE_API_BASE_URL to this origin in Vercel and complete the signed-in checks in deploy/README.md.'
