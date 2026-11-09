# Paksward

A password manager that keeps your vault on your own computer. It is encrypted there and never uploaded: no account, no server, no cloud.
The app shows its screens in your browser, served by a small program that only your computer can reach (`127.0.0.1`).
The one internet feature is optional: a leaked-password check that you start yourself (see below).

## Download (no GitHub account needed)

Go to the [download page](https://anaserose.github.io/paksward/) and pick your system, or open the [Releases page](https://github.com/Anaserose/paksward/releases/latest) and download the file for Windows, Mac or Linux.

The app is not signed yet, so your system will warn you the first time:

* **Windows:** "Windows protected your PC". Click **More info**, then **Run anyway**.
* **Mac:** the app is blocked at first. Open **System Settings > Privacy & Security**, scroll down and click **Open Anyway**.
* **Linux:** you may need to mark the file as executable.

The warning appears because the app has no paid publisher signature yet. It does not mean the file is damaged.

## Using it

1. Open the app. A browser tab opens on your own computer.
2. Click **Create account**, choose a master password, and **save your Emergency Kit** (your Secret Key and Recovery Key).
3. Add your passwords. Use **Watchtower** to see weak, reused and old ones.
4. Use **Settings > Quit** when you finish. This locks the vault and stops the app.

Next time, you only type your email and master password. The Secret Key is asked for only on a device that does not have it yet.

## Run it from source

```
pip install -r requirements.txt
python3 main.py
```

Needs Python 3.9 or newer. Your browser opens Paksward. Keep the terminal open; press Ctrl+C there to quit (or use **Settings > Quit**).
If the browser does not open, use the link printed in the terminal (`python3 main.py --no-browser` prints it without opening anything).

## Your two keys. Read this.

When you create an account Paksward makes two random keys and shows them **once**:

* **Secret Key (PWSK-...)**: needed together with your password to open the vault on a new device. It is stored on this device outside the data folder, so a copy of the data folder alone cannot be opened.
* **Recovery Key (PWRK-...)**: opens the vault by itself. It is how you get back in if you forget your password.

The email you enter is only the name of the account on this computer. Paksward never sends anything to it and does not check that it exists, so a typo in it cannot lock you out.

You can get in with **your password plus the Secret Key**, or with **the Recovery Key**.
**If you lose your password and your keys, you are locked out for good.** There is no reset, no support desk and no server that can help.
Print the keys or write them down and keep them somewhere safe. [SECURITY.md](SECURITY.md) explains what this protects against and what it does not.

## Features

Watchtower (weak, reused, old and, optionally, leaked passwords, with a score), password and passphrase generator, categories, search, favorites, clipboard auto-clear, auto-lock after inactivity, change password, new Recovery Key, encrypted backup and restore, Quit button.

**Leaked-password check (optional, online).** On the Watchtower page, "Check now" asks haveibeenpwned.com whether your passwords appear in known breaches.
For each password only the first 5 characters of its SHA-1 fingerprint are sent; the comparison happens on your computer. Nothing is sent unless you press the button.

## Where things are stored

| What | Where |
|---|---|
| Vault and account list | `data/` next to `main.py` (in a packaged app: `~/Library/Application Support/Paksward/vault` on Mac, `%APPDATA%\Paksward\vault` on Windows, `~/.local/share/Paksward/vault` on Linux). Override with `PAKSWARD_DATA_DIR`. |
| Secret Key | `.../Paksward/device` in the same per-user location. Override with `PAKSWARD_SECRET_DIR`. |

### Backup and moving to another computer

In **Settings > Backup**, click **Download backup**. You get a file ending in `.pkbackup`. It holds your encrypted vault but **no password and no keys**, so it is as safe to store as the data folder, and useless without your keys. Keep it somewhere other than this computer.

To restore it, for example on a new computer, open the login screen, click **Restore from a backup file**, choose the file, and then sign in with your master password **and your Secret Key**. Restoring never overwrites an existing account.

Keep your Secret Key and Recovery Key as well. A backup is useless without a key.

## Limits you should know about

* **No recovery if you lose everything.** If you lose your master password and both keys, nobody can open your vault, including the author.
* **One computer at a time.** There is no cloud sync and no phone app yet. A synced folder such as Dropbox or iCloud can carry the data folder between your own computers, but you must enter your Secret Key once on each one.
* **Not independently audited.** The design is described in [SECURITY.md](SECURITY.md) and covered by automated tests, but no outside security expert has reviewed it yet.
* **Unsigned downloads.** See the warnings under Download.
* **Local protection only.** Someone who already controls your computer while the vault is unlocked (for example with malware) can see what you see.

## Tests

```
python3 -m unittest discover -s tests
```

## Layout

`main.py` start-up | `docs/` download page | `packaging/` icon and build files | `paksward/` logic (crypto in `vaultkeys.py`, `secretkey.py`, `devicekey.py`; online check in `breach.py`) | `frontend/` the interface | `dev/` browser preview with sample data | `tests/`

Sharing it with other people: see [DISTRIBUTION.md](DISTRIBUTION.md). Licence: [MIT](LICENSE).
