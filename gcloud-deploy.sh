#!/bin/bash
# Redeploy after code changes

set -e

PROJECT=tinkerplexlabs-74d71
REGION=us-central1
REPO=puzzle-api

cd "$(dirname "$0")"

echo "=== Building new image ==="
gcloud builds submit \
  --tag $REGION-docker.pkg.dev/$PROJECT/$REPO/puzzle-generator

echo "=== Deploying to Cloud Run ==="
gcloud run deploy puzzle-generator \
  --image $REGION-docker.pkg.dev/$PROJECT/$REPO/puzzle-generator \
  --region $REGION \
  --memory 2Gi \
  --timeout 300 \
  --allow-unauthenticated

echo ""
echo "=== Deployed! ==="
echo "Your endpoint:"
gcloud run services describe puzzle-generator --region $REGION --format "value(status.url)"
