# Getting ClearQueue live — browser only, no terminal, no Git install

Both other guides (`GETTING_LIVE.md` and `GETTING_LIVE_HUGGINGFACE.md`) use
the command line. This one doesn't — everything happens by clicking around
on github.com and huggingface.co, dragging files, and clicking buttons. If
you're not ready to install Git yet, use this one.

You'll still end up with the same result: your code publicly on GitHub, and
a live demo running on Hugging Face Spaces.

Takes about 20–25 minutes.

---

## Before you start

Unzip `clearqueue.zip` somewhere you can find it (Desktop is fine). You
should see a folder called `clearqueue` containing:
```
clearqueue/
├── backend/
├── static/
├── sample_data/
├── app.py
├── requirements.txt
├── Dockerfile
├── README.md
├── .gitignore
├── GETTING_LIVE.md
└── GETTING_LIVE_HUGGINGFACE.md
```
Keep this Finder/Explorer window open — you'll be dragging things out of it.

---

## Part 1 — Put the code on GitHub (via browser)

### 1.1 Create a GitHub account
Go to **github.com** → **Sign up**. Free.

### 1.2 Create a new repository
1. Click the **+** icon (top right) → **New repository**.
2. **Repository name:** `clearqueue`
3. **Visibility:** Public.
4. **Leave every checkbox unchecked** (don't add a README, .gitignore, or
   license here — you already have your own copies of these and adding
   GitHub's versions too would just create a mess to clean up).
5. Click **Create repository**.

You'll land on an empty repo page with a box that says "…or push an
existing repository from the command line." Ignore that — click the smaller
link nearby that says **uploading an existing file** instead.

### 1.3 Upload the project files
1. On the upload page, drag the **entire contents** of your `clearqueue`
   folder into the drop zone — that means drag `backend`, `static`,
   `sample_data`, `app.py`, `requirements.txt`, `Dockerfile`, `README.md`,
   `.gitignore`, and the three `GETTING_LIVE*.md` files all in together.
   (Drag the individual items
   from inside the `clearqueue` folder, not the `clearqueue` folder itself
   — otherwise everything ends up nested one level too deep.)
2. Modern browsers preserve folder structure when you drag a folder like
   `backend` or `static` in, so you should end up with the same layout
   shown above. After the upload finishes, scroll through the file list
   GitHub shows you and confirm `backend/main.py`, `static/index.html`,
   etc. all show up in the right place. If a folder got flattened (rare,
   but browser-dependent), delete the misplaced files and try dragging
   that one folder in on its own.
3. Scroll down, add a commit message like `Initial commit`, and click
   **Commit changes**.

Refresh the repo page — you should see the full file tree. That's it, your
code is public on GitHub.

### 1.4 Updating the code later
Whenever you change a file, open it in the repo, click the pencil (✏️) icon
to edit it directly in the browser, or use **Add file → Upload files** again
to replace it — GitHub will ask to confirm the overwrite.

---

## Part 2 — Deploy on Hugging Face Spaces (via browser)

**Note:** Hugging Face made the **Docker SDK** paid-plan-only in mid-2026.
**Gradio** and **Static** SDKs are still free. ClearQueue is a FastAPI app,
not a Gradio app — but the project includes a small `app.py` at its root
that starts the real FastAPI app under the Gradio SDK anyway, so this still
works entirely for free. You'll just pick **Gradio** instead of Docker
below, and upload `app.py` + `requirements.txt` instead of `Dockerfile`.

### 2.1 Create a Hugging Face account
Go to **huggingface.co** → **Sign Up**. Free.

### 2.2 Create a new Space
1. Go to **huggingface.co/new-space**.
2. **Space name:** `clearqueue`
3. **License:** pick anything, doesn't matter.
4. **Select the Space SDK:** **Gradio**.
5. **Visibility:** Public.
6. Click **Create Space**.

You'll land on your new (empty) Space with a **Files** tab.

### 2.3 Upload the app files
1. Click the **Files** tab, then **Add file → Upload files**.
2. Drag in `backend`, `static`, `sample_data`, `app.py`, and the root-level
   `requirements.txt` from your `clearqueue` folder. **Don't** upload your
   project's own `README.md` here — the Space already has its own, and it
   needs a special block at the top (next step) that yours doesn't have.
3. Click **Commit changes to main**.

### 2.4 Set up the Space's README (required — this is what tells Hugging Face how to run your app)
1. Go back to the **Files** tab, click on `README.md`, then click the
   pencil (✏️) icon to edit it.
2. You'll see a block at the top like:
   ```yaml
   ---
   title: Clearqueue
   emoji: 🐳
   colorFrom: blue
   colorTo: gray
   sdk: gradio
   sdk_version: 4.44.0
   app_file: app.py
   pinned: false
   ---
   ```
3. Make sure `sdk_version` matches the `gradio==` line in `requirements.txt`
   (currently `4.44.0`) and that `app_file: app.py` is present — add it if
   it's missing. That's the only required change.
4. Click **Commit changes to main**.

### 2.5 Watch it build
Click the **App** tab. You'll see a **Building** status with logs. Because
this build also installs `scikit-learn`, `shap`, and `reportlab`, the first
build takes a bit longer than a minimal app — 3–6 minutes is normal. When
status switches to **Running**, your app is live right there in the tab
(you should see the ClearQueue upload screen, not a Gradio interface).

For a shareable direct link (better for a CV than the embedded view), click
the **⋮** menu near the top of the Space page — the direct URL follows this
pattern:
```
https://YOUR-USERNAME-clearqueue.hf.space
```

Click **Try sample data** once it loads to confirm everything works end to
end, including the ML comparison tab.

### 2.6 Updating it later
Same as GitHub: click the pencil icon on any file to edit it in the browser,
or use **Add file → Upload files** to replace a file — Hugging Face will
rebuild the Space automatically after you commit the change.

---

## A few things to know

- **Free tier sleep:** an idle free Space goes to sleep after a while and
  takes ~30–60 seconds to wake up on the next visit. Normal, not a bug —
  worth a one-line note wherever you share the link.
- **If the build fails:** click the **Logs** tab on the Space page. The most
  common cause is `sdk_version` in the README header not matching the
  `gradio` version in `requirements.txt` — keep those two in sync.
- **Keeping GitHub and Hugging Face in sync:** these are two separate,
  independent uploads. If you change a file, you'll want to update it in
  *both* places (GitHub for the public source code, Hugging Face for the
  live app) — there's no automatic syncing between them with this
  browser-only approach.

---

## Putting it on your CV

Once the Space is live, go back to your GitHub repo, open `README.md`,
click the pencil icon, and update the **Live demo** line at the top with
your `https://YOUR-USERNAME-clearqueue.hf.space` URL. Commit the change.

Now you have exactly what a hiring manager wants to see: clean public source
code on GitHub, linking straight to a live, working demo.
