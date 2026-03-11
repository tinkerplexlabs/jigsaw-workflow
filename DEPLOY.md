# Deploying Puzzle Pack Generator to Google Cloud Run

Your Firebase project `tinkerplexlabs-74d71` is already a GCP project.
Cloud Run deploys directly to it.

## One-time setup

### 1. Install the gcloud CLI (if not already installed)

```bash
# On Ubuntu/Debian
sudo apt-get install google-cloud-cli

# Or via snap
sudo snap install google-cloud-cli --classic

# Or download from https://cloud.google.com/sdk/docs/install
```

### 2. Authenticate and set your project

```bash
gcloud auth login
gcloud config set project tinkerplexlabs-74d71
```

### 3. Enable required APIs

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com
```

### 4. Create an Artifact Registry repo (for Docker images)

```bash
gcloud artifacts repositories create puzzle-api \
  --repository-format=docker \
  --location=us-central1 \
  --description="Puzzle pack generator images"
```

## Deploy

From the `/home/daniel/work/pieces` directory:

### Build and push the Docker image

```bash
gcloud builds submit \
  --tag us-central1-docker.pkg.dev/tinkerplexlabs-74d71/puzzle-api/puzzle-generator
```

### Deploy to Cloud Run

```bash
gcloud run deploy puzzle-generator \
  --image us-central1-docker.pkg.dev/tinkerplexlabs-74d71/puzzle-api/puzzle-generator \
  --region us-central1 \
  --memory 2Gi \
  --timeout 300 \
  --allow-unauthenticated
```

This gives you a public URL like:
`https://puzzle-generator-XXXXX-uc.a.run.app`

## Usage

```bash
# Health check
curl https://YOUR_URL/health

# Generate a puzzle pack
curl -o puzzle.zip \
  -F "image=@photo.jpg" \
  -F "pack_name=MyPuzzle" \
  -F "grids=4x4,6x6,8x8" \
  https://YOUR_URL/generate
```

## Updating

After code changes, just re-run both commands:

```bash
gcloud builds submit \
  --tag us-central1-docker.pkg.dev/tinkerplexlabs-74d71/puzzle-api/puzzle-generator

gcloud run deploy puzzle-generator \
  --image us-central1-docker.pkg.dev/tinkerplexlabs-74d71/puzzle-api/puzzle-generator \
  --region us-central1 \
  --memory 2Gi \
  --timeout 300 \
  --allow-unauthenticated
```

## Locking down access (optional)

Remove `--allow-unauthenticated` to require authentication, then call from
your admin interface using a service account or Firebase Auth token.

## Cost

At 2-3 calls/day (~90/month), this stays comfortably within the free tier:
- 2M requests/month free
- 360,000 vCPU-seconds free
- 360,000 GB-seconds free (your 2GB × ~30s × 90 calls = 5,400 GB-seconds)
