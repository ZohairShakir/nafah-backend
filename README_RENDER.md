# Quick Render Deployment Guide

## One-Time Setup

1. **Push your code to GitHub/GitLab/Bitbucket**

2. **Create a new Web Service on Render:**
   - Go to https://dashboard.render.com
   - Click "New +" → "Web Service"
   - Connect your repository
   - Use these settings:
     - **Name**: `nafah-backend`
     - **Environment**: `Python 3`
     - **Build Command**: `cd backend && pip install -r requirements.txt`
     - **Start Command**: `cd backend && python run.py`

3. **Set Environment Variables in Render Dashboard:**
   ```
   API_HOST=0.0.0.0
   API_PORT=8000
   DATABASE_PATH=data/nafah.db
   LOG_LEVEL=INFO
   DEBUG=False
   ALLOWED_ORIGINS=https://your-frontend-url.com
   ```

4. **Deploy!** Render will automatically deploy your service.

## Your API URL

After deployment, your API will be available at:
```
https://your-service-name.onrender.com
```

## Update Frontend

In your frontend `.env` file:
```
VITE_BACKEND_URL=https://your-service-name.onrender.com/api/v1
```

## Important Notes

⚠️ **Database**: Render's free tier has ephemeral storage. SQLite data will be lost on restart. For production, use PostgreSQL.

✅ **CORS**: Make sure to add your frontend URL to `ALLOWED_ORIGINS` environment variable.

✅ **Port**: Render automatically sets the `PORT` variable. Our code uses it automatically.
