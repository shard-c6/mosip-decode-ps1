# Setup — first time only

Everything you need to go from a clean laptop to a working conformance-testing
environment. Do this once. For day-to-day start/stop, see [RUNBOOK.md](RUNBOOK.md).

Instructions are given for **macOS** (Shardul) and **Windows** (Mukta). Both of us should
complete this so either of us can reproduce a run.

Budget 2–3 hours the first time, most of which is Docker pulling images.

---

## 0. What you are building

Three things run side by side on your machine:

| Piece | What it is | Where it listens |
|---|---|---|
| OpenID Conformance Suite | The examiner. Plays the wallet, checks the verifier against the spec. | `https://localhost.emobix.co.uk:8443` |
| Inji Verify | The MOSIP component under test. | `http://localhost:3000` (UI), `http://localhost:8080` (API) |
| ngrok tunnel | Gives Inji Verify a public HTTPS hostname. | a `*.ngrok-free.dev` address |

The ngrok tunnel is **not optional**. Inji Verify identifies itself with a `did:web` DID,
and a `did:web` identifier is resolved by fetching a document over public HTTPS. Nothing
can resolve a DID pointing at `localhost`.

---

## 1. Prerequisites

### macOS

Check what you already have:

```bash
brew --version
git --version
docker --version
java -version
mvn -version
python3 --version
```

Install whatever is missing:

```bash
# Homebrew (package manager) — if "command not found" above
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
# then run the two PATH commands it prints at the end

brew install git openjdk@11 maven python3
```

Link Java 11 — Homebrew prints the exact `sudo ln -sfn ...` command after install; run it,
then confirm `java -version` reports 11.x.

**Docker Desktop**: download from <https://www.docker.com/products/docker-desktop/>,
choose **Mac with Apple Chip** (or Intel if that's your machine). Open the `.dmg`, drag to
Applications, launch it, and wait for the whale icon in the menu bar to stop animating.

### Windows

Open **PowerShell** (not Command Prompt). Check:

```powershell
git --version
docker --version
java -version
mvn -version
python --version
```

Install what's missing using winget:

```powershell
winget install --id Git.Git -e
winget install --id EclipseAdoptium.Temurin.11.JDK -e
winget install --id Apache.Maven -e
winget install --id Python.Python.3.12 -e
```

**Docker Desktop**: download from <https://www.docker.com/products/docker-desktop/> and
choose the Windows installer. It will ask to enable **WSL 2** — say yes; that is the
supported backend. Reboot when prompted, then launch Docker Desktop and wait for it to
report "Engine running".

After installing, **close and reopen PowerShell** so the new tools are on your PATH.

> **Windows note on line endings.** Configure git once so shell scripts don't get CRLF
> line endings that break inside Linux containers:
> ```powershell
> git config --global core.autocrlf input
> ```

---

## 2. Git identity (both platforms)

```bash
git config --global user.name "Your Name"
git config --global user.email "your@email.com"
```

Use the email attached to your GitHub account, otherwise commits won't be linked to your
profile.

---

## 3. Create the working folder and clone everything

Pick a folder you'll remember. These instructions assume:

- macOS: `~/projects/MOSIP`
- Windows: `C:\projects\MOSIP`

### macOS

```bash
mkdir -p ~/projects/MOSIP && cd ~/projects/MOSIP

git clone --depth 1 https://github.com/mosip/inji-verify.git
git clone --depth 1 https://github.com/mosip/inji-certify.git
git clone --depth 1 https://github.com/mosip/mosip-functional-tests.git
git clone https://gitlab.com/openid/conformance-suite.git
git clone https://gitlab.com/openid/conformance-suite-automated-testing-tutorial.git
git clone https://github.com/<your-username>/mosip-decode-ps1.git
```

### Windows

```powershell
mkdir C:\projects\MOSIP; cd C:\projects\MOSIP

git clone --depth 1 https://github.com/mosip/inji-verify.git
git clone --depth 1 https://github.com/mosip/inji-certify.git
git clone --depth 1 https://github.com/mosip/mosip-functional-tests.git
git clone https://gitlab.com/openid/conformance-suite.git
git clone https://gitlab.com/openid/conformance-suite-automated-testing-tutorial.git
git clone https://github.com/<your-username>/mosip-decode-ps1.git
```

You should end up with six folders side by side. `mosip-decode-ps1` is **our** repo — the
only one we commit to. The others are upstream code we read and run.

### Point the MOSIP clones at your forks

Fork `mosip/inji-verify`, `mosip/inji-certify` and `mosip/mosip-functional-tests` on
GitHub (the **Fork** button, top right of each repo page), then:

```bash
cd inji-verify
git remote set-url origin https://github.com/<your-username>/inji-verify.git
git remote add upstream https://github.com/mosip/inji-verify.git
cd ..
```

Repeat for the other two. `origin` is now your fork (where you push); `upstream` is MOSIP's
(where you pull updates from and open pull requests to).

---

## 4. ngrok

### Install

- **macOS**: `brew install ngrok`
- **Windows**: `winget install --id ngrok.ngrok -e`

### Authenticate

Sign up free at <https://ngrok.com>, copy your authtoken from the dashboard, then:

```bash
ngrok config add-authtoken YOUR_TOKEN_HERE
```

### Claim a static domain

In the ngrok dashboard, claim the free static domain that comes with your account. Without
it you get a **new random hostname every restart**, and you'll have to redo step 5 each
time. With it, the hostname is stable forever.

Note your domain — it looks like `something-something-something.ngrok-free.dev`.

> Shardul and Mukta will each have **different** ngrok domains. That is fine and expected.
> The domain is per-developer, which is why it is not committed to the repo.

---

## 5. Configure Inji Verify with your ngrok hostname

`inji-verify/docker-compose/docker-compose.yml` ships with the literal placeholder string
`VERIFY_SERVICE_PROXY_FOR_LOCALHOST` in **five** environment variables. Nothing substitutes
it automatically — you must replace it yourself.

### macOS

```bash
cd ~/projects/MOSIP/inji-verify/docker-compose
sed -i '' 's/VERIFY_SERVICE_PROXY_FOR_LOCALHOST/YOUR-DOMAIN.ngrok-free.dev/g' docker-compose.yml
grep -n "ngrok\|VERIFY_SERVICE_PROXY" docker-compose.yml
```

### Windows

```powershell
cd C:\projects\MOSIP\inji-verify\docker-compose
(Get-Content docker-compose.yml) -replace 'VERIFY_SERVICE_PROXY_FOR_LOCALHOST','YOUR-DOMAIN.ngrok-free.dev' | Set-Content docker-compose.yml
Select-String -Path docker-compose.yml -Pattern "ngrok|VERIFY_SERVICE_PROXY"
```

**Verify the result**: the grep must show **five lines**, all containing your hostname, and
**zero** lines still containing `VERIFY_SERVICE_PROXY_FOR_LOCALHOST`.

Use the hostname only — no `https://` prefix, no trailing slash. The compose file already
supplies `https://` and `did:web:` prefixes where needed.

> **If you get it wrong**: `git checkout docker-compose.yml` restores the original with the
> placeholder back in place, and you can redo it.

---

## 6. Set the credential scheme for conformance testing

The shipped `config/config.json` defines five credential types. For conformance testing
against the OID4VP 1.0 Final plan we use **Mock Identity (SD JWT)**, and it must use the
`pre_registered` client identifier scheme so the authorisation request is delivered
**inline** rather than by reference.

Open `inji-verify/docker-compose/config/config.json` and find the entry with
`"name": "Mock Identity (SD JWT)"`. Ensure it reads:

```json
"clientIdScheme":"pre_registered",
```

(It ships as `"did"`. See finding F-09 in the findings document for why this matters.)

---

## 7. First run

Follow [RUNBOOK.md](RUNBOOK.md) from the top. The first `docker compose up` will pull
several gigabytes of images — that is the slow part, and it only happens once.

### Verify the install worked

Once everything is up:

```bash
# 1. Conformance suite responds (expect JSON describing the dev user)
curl -k https://localhost.emobix.co.uk:8443/api/currentuser

# 2. Inji Verify's DID document resolves publicly (expect JSON with a public key)
curl https://YOUR-DOMAIN.ngrok-free.dev/v1/verify/did.json
```

If both return JSON, your environment is correct.

---

## Known first-time snags

**Browser warns the conformance suite is "not secure".** Expected. The suite uses a
self-signed certificate, and the connection is to `127.0.0.1` — your own machine. Click
through (Chrome: *Advanced* → *Proceed*; if Chrome refuses to show the link, click the page
and type `thisisunsafe`). This reasoning applies **only** because the destination is
localhost. Never dismiss certificate warnings on real remote sites.

**Apple Silicon platform warning.** `The requested image's platform (linux/amd64) does not
match the detected host platform (linux/arm64/v8)` is a warning, not an error — the image
runs under emulation. If a container refuses to start entirely:

```bash
export DOCKER_DEFAULT_PLATFORM=linux/amd64
```
then re-run the compose command.

**Ports already in use.** Inji Verify needs 3000, 8080 and 5432 free; the conformance
suite needs 8443 and 8444. If Postgres is already running locally, stop it before starting
the stack.

**Windows: `docker` not found after installing Docker Desktop.** Close and reopen
PowerShell. If it still fails, confirm Docker Desktop is actually running (whale icon in
the system tray) and that WSL 2 integration is enabled in its settings.
