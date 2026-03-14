#!/bin/bash
# Tear down the Cloud Run service and clean up

set -e

PROJECT=tinkerplexlabs-74d71
REGION=us-central1
REPO=puzzle-api

echo "=== Deleting Cloud Run service ==="
gcloud run services delete puzzle-generator --region $REGION --quiet

echo "=== Deleting container images ==="
gcloud artifacts docker images delete \
  $REGION-docker.pkg.dev/$PROJECT/$REPO/puzzle-generator \
  --delete-tags --quiet \
  2>/dev/null || echo "  (no images to delete)"

echo ""
read -p "Also delete the Artifact Registry repo '$REPO'? (y/N) " answer
if [[ "$answer" == "y" || "$answer" == "Y" ]]; then
  gcloud artifacts repositories delete $REPO --location $REGION --quiet
  echo "  Repo deleted."
fi

echo "=== Shutdown complete ==="
