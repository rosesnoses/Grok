# AGENTS.md — psycho-mandala / Aurion Mandala

## Project identity

This repo is a Cloud Run-ready Aurion Mandala app.

Treat it as a Python FastAPI/Uvicorn backend plus a static browser frontend.

Canonical production target:
- Google Cloud project: aurion-sva
- Region: asia-southeast1
- Cloud Run service: mandalamatrix
- Artifact image repo: asia-southeast1-docker.pkg.dev/aurion-sva/mandala/mandalamatrix
- Runtime port: 8080

The repo uses plain Dockerfile, not Dockerfile.cloudrun.

## Expected repo layout

.
├── Dockerfile
├── cloudbuild.yaml
├── requirements.txt
├── serve.py
├── api_fastapi.py
├── web/
│   └── index.html
├── engine/
├── api/
├── .dockerignore
├── local_build_test.sh
└── AGENTS.md

## Working rules

1. Make minimal, high-confidence changes.
2. Do not deploy, push to GitHub, run gcloud run deploy, or modify production Cloud Run settings unless the user explicitly asks.
3. Do not add new production dependencies without explaining why.
4. Do not store or print secrets.
5. Do not commit .env, service account JSON, API keys, tokens, generated media, or local cache files.
6. Keep full function bodies. Do not stub or omit logic unless the user asks for a sketch.
7. When editing frontend code, avoid user-controlled innerHTML; prefer textContent and DOM node construction.
8. For crypto/security code, do not weaken encryption, hashing, verification, password handling, or artifact integrity checks.
9. For canvas/audio-heavy work, watch memory use and avoid blocking the UI unnecessarily.

## Setup assumptions

Always work from the Codex worktree:

cd "${CODEX_WORKTREE_PATH:-$PWD}"

Use a local Python virtual environment:

python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

Only run Node install commands if a Node project exists:

if [ -f package-lock.json ]; then
  npm ci
elif [ -f package.json ]; then
  npm install
fi

## Local validation

Before saying a change is complete, run the most relevant checks available.

Preferred checks:

. .venv/bin/activate
python -m compileall .

For full container validation:

chmod +x ./local_build_test.sh
./local_build_test.sh

Expected local smoke targets:
- GET /health
- GET /
- GET /api/v1/mandala/variance-catalog

If a check cannot be run, explain exactly why.

## Docker / Cloud Run rules

Use plain Dockerfile.

Expected container command:

uvicorn serve:app --host 0.0.0.0 --port ${PORT}

Expected Cloud Build config:

steps:
  - name: gcr.io/cloud-builders/docker
    args:
      - build
      - -f
      - Dockerfile
      - -t
      - ${_IMAGE}
      - .
images:
  - ${_IMAGE}

Do not switch this repo to Vercel, nginx-only, or static-only hosting unless the user explicitly asks.

## Frontend rules

The main frontend lives at:

web/index.html

Maintain the AurionMandala.com SVA flow:
- Forge Mandala
- Extract Audio
- Auto-Test Pipeline
- Canvas mandala renderer
- Trust Console prototype

Treat Trust Console localStorage controls as prototype-only unless backed by real server authentication.

## Security rules

Never introduce:
- deterministic AES-GCM IV reuse
- unsanitized artifact/user data in innerHTML
- hardcoded secrets
- unauthenticated privileged backend actions
- silent integrity-check bypasses

Prefer:
- random IVs for AES-GCM encryption
- explicit SHA-256 verification
- safe DOM rendering
- clear error messages
- server-side enforcement for real auth/security features

## Response style

When reporting work:
1. State what changed.
2. State what was tested.
3. State any remaining risk or manual step.
4. Keep the answer concise.
