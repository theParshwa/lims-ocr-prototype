# Deploying LIMS OCR to Railway

Railway hosts both the backend and frontend as Docker containers.
Cost: ~$5/month (Railway gives $5 free credit each month).

---

## Step 1 — Install Git

If you don't have Git installed:
1. Go to https://git-scm.com/download/win
2. Download and install (click Next on everything)
3. Open a new terminal and type `git --version` to confirm

---

## Step 2 — Push code to GitHub

1. Go to https://github.com and create a free account
2. Click **New repository** → name it `lims-ocr` → set to **Private** → click **Create**
3. In your VS Code terminal (from `d:\College\LIMS OCR`):

```
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/lims-ocr.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your GitHub username.

> **Note:** The `.gitignore` ensures your `.env` file (with your API key) is NOT uploaded.

---

## Step 3 — Create a Railway account

1. Go to https://railway.app
2. Click **Login** → **Login with GitHub** → authorise Railway

---

## Step 4 — Deploy the Backend

1. In Railway dashboard, click **New Project** → **Deploy from GitHub repo**
2. Select your `lims-ocr` repository
3. Railway will detect the Dockerfiles — click **Add service** → choose **Docker**
4. In the service settings:
   - **Root Directory**: `/` (leave default)
   - **Dockerfile**: `Dockerfile.backend`
5. Go to the **Variables** tab and add these environment variables:
   ```
   AI_PROVIDER=openai
   OPENAI_API_KEY=your-actual-api-key-here
   OPENAI_MODEL=gpt-4o
   OCR_ENABLED=true
   LOG_LEVEL=INFO
   CORS_ORIGINS=["https://YOUR-FRONTEND-URL.up.railway.app"]
   ```
   (You'll update `CORS_ORIGINS` with the real frontend URL in Step 5)
6. Click **Deploy**
7. Once deployed, copy the backend URL (e.g. `https://lims-ocr-backend.up.railway.app`)

---

## Step 5 — Deploy the Frontend

1. In the same Railway project, click **+ New Service** → **Docker**
2. Same repo, but set **Dockerfile** to `Dockerfile.frontend`
3. Go to **Variables** tab and add:
   ```
   VITE_API_URL=https://YOUR-BACKEND-URL.up.railway.app
   ```
   (Replace with the URL from Step 4)
4. Click **Deploy**
5. Copy the frontend URL (e.g. `https://lims-ocr-frontend.up.railway.app`)

---

## Step 6 — Fix CORS

1. Go back to the **backend** service in Railway
2. Update the `CORS_ORIGINS` variable to:
   ```
   ["https://lims-ocr-frontend.up.railway.app"]
   ```
   (Use your actual frontend URL from Step 5)
3. Redeploy the backend

---

## Step 7 — Open your app

Visit your frontend URL from any computer, anywhere:
```
https://lims-ocr-frontend.up.railway.app
```

---

## Persistent Storage

Railway supports persistent volumes. Your uploaded files, database, and training
examples are stored in Docker volumes and survive restarts.

---

## Updating the app later

After making code changes:
```
git add .
git commit -m "describe your change"
git push
```
Railway automatically detects the push and redeploys both services.
