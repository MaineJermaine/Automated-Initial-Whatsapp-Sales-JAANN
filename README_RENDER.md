# Deploying to Render.com

This guide will help you host your Flask application on Render.com using the newly created `pyproject.toml` and `render.yaml` files.

## Prerequisites

1.  **Git Hub Repository**: Your code must be pushed to a GitHub (or GitLab/Bitbucket) repository.
2.  **Render Account**: Sign up at [Render.com](https://render.com).

## Automatic Setup (Recommended)

1.  Log in to Render and click **"New +"** -> **"Blueprint"**.
2.  Connect your GitHub repository.
3.  Render will automatically detect the `render.yaml` file and set up:
    *   The Web Service (Flask app).
    *   A Persistent Disk (for your SQLite `database.db` and uploads).
4.  Click **"Apply"**.

## Manual Setup

If you prefer to set it up manually:

1.  Click **"New +"** -> **"Web Service"**.
2.  Select your repository.
3.  **Environment**: `Python`
4.  **Build Command**: `poetry install` (Render will automatically install poetry if it sees `pyproject.toml`).
5.  **Start Command**: `gunicorn app:app`
6.  Add the following **Environment Variables**:
    *   `PYTHON_VERSION`: `3.11.0` (or your preferred version)
    *   `DATABASE_URL`: `sqlite:////data/database.db` (The `/data` folder matches the persistent disk mount path).
    *   `UPLOAD_FOLDER`: `/data/uploads`
    *   `SECRET_KEY`: (Any random long string for security).

## Important Notes on SQLite

On Render, the local filesystem is **ephemeral**, meaning it resets every time you deploy or restart your server.
*   **Persistent Disk**: We have configured a 1GB Persistent Disk in `render.yaml` mounted at `/data`.
*   Ensure your `DATABASE_URL` environment variable points to `/data/database.db` so your data survives redeployments.

## Finalizing Deployment

Once the build is complete, Render will provide you with a URL (e.g., `your-app.onrender.com`). You are now live!
