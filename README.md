# Hosting on Render.com (Free Tier)

This project is configured to run on Render's **Free Tier**.

## Setup Instructions

1.  **GitHub**: Push your code to a GitHub repository.
2.  **Deployment**: 
    *   Go to **Blueprint** on Render.
    *   Connect your repository.
    *   Render will use `render.yaml` to automatically configure the service.
3.  **Persistence Note**: 
    *   In the Free Tier, any changes made to the database (new users, team scores, etc.) will be **wiped** whenever the server restarts or you push new code.
    *   If you want to keep specific data, ensure you push your `database.db` file to your GitHub repository.

## Commands for local sync
If you make changes to your dependencies, run:
```powershell
python -m poetry lock
```
Then commit and push your `poetry.lock` and `pyproject.toml` files.
