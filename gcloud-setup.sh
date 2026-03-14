#!/bin/bash
# One-time setup for Google Cloud Run deployment
# Run this once before the first deploy

set -e

PROJECT=tinkerplexlabs-74d71
REGION=us-central1
REPO=puzzle-api

echo "=== Authenticating with Google Cloud ==="
gcloud auth login

echo "=== Setting project ==="
gcloud config set project $PROJECT

echo "=== Enabling required APIs ==="
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com

echo "=== Creating Artifact Registry repo ==="
gcloud artifacts repositories create $REPO \
  --repository-format=docker \
  --location=$REGION \
  --description="Puzzle pack generator images" \
  2>/dev/null || echo "  (repo already exists, skipping)"

echo "=== Building and deploying ==="
cd "$(dirname "$0")"

gcloud builds submit \
  --tag $REGION-docker.pkg.dev/$PROJECT/$REPO/puzzle-generator

gcloud run deploy puzzle-generator \
  --image $REGION-docker.pkg.dev/$PROJECT/$REPO/puzzle-generator \
  --region $REGION \
  --memory 2Gi \
  --timeout 300 \
  --allow-unauthenticated

echo ""
echo "=== Done! ==="
echo "Your endpoint:"
gcloud run services describe puzzle-generator --region $REGION --format "value(status.url)"
