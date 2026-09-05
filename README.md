# netsentry

A lightweight, headless network and system security monitor exposed over a REST API, built as the target application for a DevSecOps CI/CD pipeline demonstrating security scanning at every stage of the software delivery process.

![Project banner](screenshots/banner.png)
*(Screenshot: add a banner image here, e.g. a diagram of the app + pipeline)*

---

## Table of Contents

- [Why this project exists](#why-this-project-exists)
- [What netsentry does](#what-netsentry-does)
- [API Endpoints](#api-endpoints)
- [Architecture](#architecture)
- [The DevSecOps Pipeline](#the-devsecops-pipeline)
  - [Stage 1 — Lint & Unit Test](#stage-1--lint--unit-test)
  - [Stage 2 — SAST (Static Application Security Testing)](#stage-2--sast-static-application-security-testing)
  - [Stage 3 — Dependency Scanning (SCA)](#stage-3--dependency-scanning-sca)
  - [Stage 4 — Dockerfile Linting](#stage-4--dockerfile-linting)
  - [Stage 5 — Container Image Build](#stage-5--container-image-build)
  - [Stage 6 — Container Image Scanning](#stage-6--container-image-scanning)
  - [Stage 7 — Secrets Scanning](#stage-7--secrets-scanning)
  - [Stage 8 — SBOM Generation](#stage-8--sbom-generation)
  - [Stage 9 — Image Signing (optional)](#stage-9--image-signing-optional)
  - [Stage 10 — Push to Registry](#stage-10--push-to-registry)
- [Dockerfile Hardening](#dockerfile-hardening)
- [Real Finding: the starlette CVE](#real-finding-the-starlette-cve)
- [Running It Locally](#running-it-locally)
- [Screenshots](#screenshots)
- [Lessons Learned](#lessons-learned)

---

## Why this project exists

Modern application security isn't just about writing safe code — it's about proving, automatically and repeatedly, that every layer of the delivery pipeline (source code, dependencies, container image, secrets, supply chain) has been checked before anything reaches production. This is the practice known as **DevSecOps**: folding security tooling directly into CI/CD so that vulnerabilities are caught at build time, not after deployment.

`netsentry` is a small, real network/system monitoring API — but the actual point of this project isn't the app. It's the pipeline wrapped around it: a fully automated GitHub Actions workflow that runs static analysis, dependency auditing, container hardening checks, image vulnerability scanning, secrets detection, and software bill-of-materials (SBOM) generation on every single push, and refuses to let insecure code or images move forward.

## What netsentry does

`netsentry` exposes basic host and network visibility over HTTP, without needing root privileges or raw sockets — a deliberate design choice so the app can run in a locked-down, non-root container (see [Dockerfile Hardening](#dockerfile-hardening)).

It reports:
- Live CPU, memory, and disk usage
- Active network connections and per-interface I/O statistics
- Currently listening ports
- Simple rule-based security alerts (e.g. unexpected listening ports, unusually high connection counts per process)

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Liveness check |
| `/system` | GET | CPU, memory, disk snapshot |
| `/network` | GET | Connections, interface I/O, listening ports |
| `/alerts` | GET | List of rule-based security findings |

![API response example](screenshots/api-response.png)
*(Screenshot: add a browser or Postman screenshot of a /network or /alerts response here)*

## Architecture

```
                ┌─────────────┐
   HTTP request │  netsentry  │  psutil (no root, no raw sockets)
   ────────────►│  (FastAPI)  │─────────────────────────────────►
                └─────────────┘        host system stats
```

The app runs inside a hardened, non-root Docker container. It never needs elevated privileges because it reads system/network state through `psutil`, not through raw packet capture.

![Architecture diagram](screenshots/architecture.png)
*(Screenshot/diagram: add a fuller architecture diagram here — app container, pipeline stages, registry)*

---

## The DevSecOps Pipeline

The pipeline lives at `.github/workflows/security-pipeline.yml` and runs automatically on every push and pull request to `main`. Each stage is its own GitHub Actions job, and each job depends (`needs:`) on the previous one passing — so a single failed check stops everything downstream. Nothing insecure quietly slips through.

![Pipeline overview in GitHub Actions](screenshots/pipeline-overview.png)
*(Screenshot: add the full green checklist of all jobs from the GitHub Actions tab here)*

### Stage 1 — Lint & Unit Test

Runs the project's pytest suite against the FastAPI app using `TestClient`, confirming every endpoint returns the expected response before anything else runs. If the app itself is broken, there's no point running security tools against it.

### Stage 2 — SAST (Static Application Security Testing)

Uses **Semgrep** with the `p/security-audit` ruleset to scan the Python source code itself for insecure patterns (hardcoded secrets, unsafe function use, injection-prone code) without executing anything. This catches security bugs baked directly into the source before the code is ever packaged.

### Stage 3 — Dependency Scanning (SCA)

Uses **pip-audit** to check every pinned package in `requirements.txt` against known vulnerability databases (OSV/PyPA advisory feeds). If a dependency has a published CVE, the build fails here — before a vulnerable dependency ever makes it into a container image.

![pip-audit output](screenshots/pip-audit-output.png)
*(Screenshot: add the pip-audit terminal output here — good place to show the starlette CVE catch)*

### Stage 4 — Dockerfile Linting

Uses **Hadolint** to statically check the `Dockerfile` itself for bad practices — using `latest` tags, missing a non-root `USER`, unnecessary layers, insecure `ADD` usage, etc. This ensures the container *definition* is sound before it's ever built.

### Stage 5 — Container Image Build

Builds the actual Docker image from the hardened multi-stage `Dockerfile`, tagged with the commit SHA (`netsentry:<sha>`) so every build is traceable to an exact commit. The built image is saved and passed forward as a workflow artifact so later stages can scan the same image without rebuilding it.

### Stage 6 — Container Image Scanning

Uses **Trivy** to scan the actual built container image for OS-level and Python package vulnerabilities inside the final image layers — catching anything that slipped past dependency scanning (e.g. vulnerable OS packages in the base image). The build fails immediately if any `HIGH` or `CRITICAL` severity vulnerability is found.

![Trivy scan results](screenshots/trivy-scan-output.png)
*(Screenshot: add the Trivy scan output table here)*

### Stage 7 — Secrets Scanning

Uses **Gitleaks** to scan the full git history (not just the latest diff) for accidentally committed secrets — API keys, tokens, credentials, private keys. This catches secrets that may have been committed and later removed, which a diff-only scan would miss.

### Stage 8 — SBOM Generation

Uses **Syft** to generate a Software Bill of Materials for the built image — a complete, machine-readable inventory of every package and library inside it (in CycloneDX or SPDX format). This is uploaded as a build artifact on every run, giving full supply-chain visibility into exactly what's shipped in each image, independent of what's in `requirements.txt`.

### Stage 9 — Image Signing (optional)

Uses **cosign** with keyless signing (via GitHub's OIDC identity) to cryptographically sign the built image. This lets anyone verify the image was genuinely built by this pipeline and hasn't been tampered with afterward — a core supply-chain security practice.

### Stage 10 — Push to Registry

Only runs if every previous stage passed. Pushes the scanned, signed, SBOM-attached image to the container registry (GHCR), tagged with the commit SHA. This is the only path by which an image can reach the registry — there is no way to push an image that skipped any of the checks above.

---

## Dockerfile Hardening

The final container image is built with several deliberate hardening choices:

- **Multi-stage build** — dependencies are installed in a throwaway `builder` stage; the final `runtime` image contains only the app code and installed packages, no build tools or pip cache.
- **Non-root user** — the container runs as a dedicated `appuser` (fixed UID `10001`), never as root.
- **Pinned base image** — `python:3.12-slim`, no `latest` tag.
- **Minimal copy surface** — only the exact files the app needs (`main.py`, `monitor.py`) are copied in; tests, git history, and dev tooling never enter the image.

![Dockerfile](screenshots/dockerfile.png)
*(Screenshot: add a screenshot of the Dockerfile itself here)*

## Real Finding: the starlette CVE

During development, `pip-audit` (Stage 3) caught a real, published set of CVEs in `starlette 0.38.6`, a transitive dependency pulled in by an outdated `fastapi` pin. The fix required bumping `fastapi` to a version without the old upper-bound constraint on `starlette`, allowing a patched `starlette>=1.3.1` to resolve.

**Before:**
```
fastapi==0.115.0
uvicorn==0.30.6
psutil==6.0.0
```
Result: 9 known vulnerabilities flagged in `starlette 0.38.6`.

**After:**
```
fastapi>=0.116.0
uvicorn==0.30.6
psutil==6.0.0
starlette>=1.3.1
```
Result: dependency scan passes clean.

This is a concrete example of the pipeline doing exactly what it's meant to do — catching a real vulnerable dependency before it ever reached a built image.

## Running It Locally

```bash
# clone and enter the repo
git clone https://github.com/NAJIMx0/netsentry.git
cd netsentry

# install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# run tests
pytest -v

# run the app
uvicorn main:app --host 0.0.0.0 --port 8000

# build the hardened container
docker build -t netsentry:local .
docker run -p 8000:8000 netsentry:local
```

Then visit `http://localhost:8000/health`.

## Screenshots

*(Add screenshots below as you take them — recommended set:)*

- [ ] Full GitHub Actions pipeline, all stages green
- [ ] `/network` and `/alerts` endpoint responses
- [ ] pip-audit catching the starlette CVE (before fix)
- [ ] pip-audit passing clean (after fix)
- [ ] Trivy image scan output
- [ ] Hadolint output on the Dockerfile
- [ ] SBOM artifact download from a workflow run
- [ ] `docker run` output showing the container starting as non-root

## Lessons Learned

- A dependency pin can look "safe" while quietly locking you into a vulnerable transitive dependency — `fastapi==0.115.0` looked fine until `pip-audit` traced the real issue to `starlette`.
- Hardening a Dockerfile isn't just about adding `USER` — copying only the files you actually need is just as important as who runs the process.
- A pipeline is only as trustworthy as its weakest gate — each stage here blocks the next specifically so no single missed check can let something insecure through.
