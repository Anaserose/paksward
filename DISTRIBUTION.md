# Giving Paksward to other people

Paksward is not a website. People download it and run it on their own computer, and their vault is created there.
You do **not** need a server that runs Paksward: only a place to put the downloads and one page that points to them.
**Do not turn Paksward into a website people log in to.** That would put their vaults on your server.

## Launch steps (GitHub user: Anaserose)

Do these on your computer, in the project folder. You need a free GitHub account (you have one) and `git` installed.

1. **Create the repository.** On github.com click **New repository**. Name it exactly `paksward`, set it to **Public**, leave "Add a README" unticked, create it.
2. **Upload the project** (Terminal on Mac, or the VS Code terminal, inside the project folder):
   ```
   git init
   git add .
   git commit -m "First release"
   git branch -M main
   git remote add origin https://github.com/Anaserose/paksward.git
   git push -u origin main
   ```
   (GitHub may ask you to sign in; use a personal access token as the password, or GitHub Desktop if you prefer clicking.)
   `.gitignore` already keeps your own `data/` folder out.
3. **Switch on the download page.** Repository **Settings > Pages**: *Deploy from a branch*, branch `main`, folder `/docs`, Save. After a minute your page is at `https://Anaserose.github.io/paksward/`.
4. **Do a trial build first.** `git tag v0.0.1-test && git push origin v0.0.1-test`, then watch the **Actions** tab (10 to 20 minutes).
   When it is green, open **Releases**, download the file for your computer and test it. If a job is red, open it and send me the error text.
5. **Make the real release.** `git tag v4.0.0 && git push origin v4.0.0`. The same workflow publishes the four downloads and `SHA256SUMS.txt` on the Releases page, and the page links to the newest release automatically.
6. Open your page in a private window, check each download button, and share the page link.

Your visitors do **not** need a GitHub account: files on a public release download with a normal link (confirm this once in a private window).

**Not yet verified:** the workflow and `paksward.spec` could not be run where they were written (the build needs GitHub's machines). Expect to fix small things on the first run.

Costs: nothing. GitHub Releases allows files up to 2 GiB each; GitHub Pages is free for a project page like this one (not for a business or for collecting passwords).
Cloudflare Pages is not recommended for the downloads: each file there is capped at 25 MiB.

## The warning people will see, and what can be done about it

The apps are not code-signed, so Windows (SmartScreen) and macOS (Gatekeeper) warn on first open. **No free option removes the warning completely.**

| System | Cheapest real fix | Result |
|---|---|---|
| Windows | **SignPath Foundation**: free code signing for open-source projects (apply at signpath.org; your repo must be public and open source, which MIT satisfies; they decide on eligibility). Other routes: a certificate ($150-300 a year), Azure Artifact Signing (about $10 a month, but only for individuals in the USA and Canada), or the Microsoft Store (MSIX, no warnings, but needs repackaging). | Signed apps still show a SmartScreen warning at first; it fades as downloads build reputation. |
| macOS | **Apple Developer Program, $99 a year** (no fee waiver for individuals). Required to sign and notarize. | The only way to remove the Mac warning. Until then people must use System Settings > Privacy & Security > Open Anyway (the old right-click trick no longer works). |
| Linux | nothing needed | no warning |

Antivirus programs sometimes flag apps built with PyInstaller. Signing and a growing download count help. Publish the checksums (the workflow does).

## Phones and syncing

* **Phones are not supported yet.** Paksward is a Python program with a local web server, which iPhone and Android cannot run. A phone version is a separate project: an installable web app (PWA) that runs from a free static host with the vault encrypted inside the phone's browser. It needs the crypto written again in JavaScript (Argon2id via WebAssembly) and tested from scratch. Do not rush it: a password manager with untested crypto is worse than none.
* **Syncing by email is not possible.** An email address cannot decrypt or authenticate anything; it is not a secret. Real sync needs somewhere to store the encrypted vault, plus the keys. Options that keep your "no server saves content" rule:
  1. **Your own cloud folder (works today on computers).** Point `PAKSWARD_DATA_DIR` at a folder inside Dropbox, iCloud Drive or OneDrive, and use the same email, password and Secret Key on each computer. The synced files are encrypted and useless without the Secret Key, which is kept off that folder. Do not use two computers at the same moment (the last save wins).
  2. **Encrypted backup file** you move by hand. Not built yet (planned).
  3. **A sync server that only stores encrypted blobs.** It would hold ciphertext, not passwords, but it is a server you would have to run, secure and keep alive. Not recommended for launch.

## The name and the icon

* **Name check.** Web searches for "Paksward" found no existing app, company or brand using it. That is not a trademark clearance: search your country's trademark register (in Nigeria, the Trademarks Registry) and the App Store / Google Play before you spend money on branding.
* The icon in `packaging/icon/` is an original mark (two half rings slid out of line). Web and image searches found nothing like it; that is not proof. Run `icon-1024.png` through a reverse image search (Google Lens, TinEye) before launch.

## Before you say it is "protected"

Have someone with cryptography experience review `SECURITY.md`, `paksward/vaultkeys.py`, `paksward/secretkey.py` and `paksward/accounts.py`, and say plainly in your posts that the design is new and unreviewed.
