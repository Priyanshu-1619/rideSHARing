# Deployment Guide: rideSHARing on Render

This guide will help you deploy your rideSHARing application to Render.

## Prerequisites

1. A Render account (Free: https://render.com)
2. Your GitHub repository with this code
3. Environment variables configured

## Step-by-Step Deployment

### 1. Push Code to GitHub

```bash
cd /workspaces/rideSHARing
git add .
git commit -m "Prepare for Render deployment"
git push origin main
```

### 2. Create a Render Web Service

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Select the `rideSHARing` repository

### 3. Configure the Web Service

**Settings to use:**

- **Name**: `ridesHARing` (or your preferred name)
- **Environment**: `Python`
- **Build Command**: `pip install -r rideshare2/requirements.txt`
- **Start Command**: `cd rideshare2 && gunicorn -w 4 -b 0.0.0.0:$PORT --timeout 120 wsgi:app`
- **Root Directory**: `.` (leave as default)
- **Plan**: Free or Paid (choice depends on your needs)

### 4. Set Environment Variables

In the "Environment" section, add:

| Key | Value |
|-----|-------|
| `FLASK_ENV` | `production` |
| `SECRET_KEY` | Generate a strong random key or let Render generate one |
| `USE_MYSQL` | `False` (SQLite for free tier) |
| `PYTHON_VERSION` | `3.11` |

**To generate a SECRET_KEY:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 5. Deploy

1. Click "Create Web Service"
2. Render will automatically start the deployment
3. Wait for the build to complete (usually 2-5 minutes)
4. Once deployed, your app will be available at: `https://<service-name>.onrender.com`

## Alternative: Using render.yaml

If you prefer to use `render.yaml` configuration:

1. Push your code to GitHub with the included `render.yaml`
2. Go to Render Dashboard
3. Click "New +" → "Web Service"
4. Select "Deploy an existing repository"
5. Choose this repo and Render will auto-detect `render.yaml`

## Verification

After deployment, test the application:

### 1. Check Health
```bash
curl https://<service-name>.onrender.com/
```

### 2. Test Registration
```bash
curl -X POST https://<service-name>.onrender.com/api/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Test User","email":"test@example.com","phone":"1234567890","password":"test123"}'
```

### 3. Check Logs
In Render Dashboard → Your App → "Logs" tab to view real-time logs

## Database Management

### SQLite (Current Setup)
- Database file: `database/nextride.db`
- Automatically created on first run
- **Note**: File-based storage is reset when Render free tier redeploys

### Upgrade to PostgreSQL (Recommended for Production)

1. In Render Dashboard, add a PostgreSQL database
2. Update environment variables with database connection string
3. Modify `backend/app.py` to use PostgreSQL
4. Redeploy

```python
# Example PostgreSQL config
DATABASE_URL = os.environ.get('DATABASE_URL', '')
USE_MYSQL = False
USE_POSTGRES = bool(DATABASE_URL)
```

## Common Issues & Fixes

### Issue: "Module not found" error
**Solution**: Ensure `requirements.txt` is in the `rideshare2/` directory

### Issue: Static files not loading
**Solution**: Render serves static files automatically. Ensure `static/` directory exists

### Issue: Database errors on free tier redeploy
**Solution**: Upgrade to PostgreSQL or use a persistent volume:
```yaml
# In render.yaml
disk:
  name: data
  mountPath: /data
```

### Issue: Service builds but doesn't start
**Check**: View deploy logs in Render dashboard for error messages

## Monitoring & Maintenance

### View Logs
- Dashboard → Your Service → Logs (streaming logs)
- Dashboard → Events (deployment history)

### Restart Service
- Dashboard → Your Service → Restart → Restart latest deployment

### Monitor Performance
- Check CPU and Memory usage in Render dashboard
- Upgrade plan if needed

### Automatic Deployments
- Every push to `main` branch triggers automatic redeployment
- **To disable**: Dashboard → Service → Settings → Uncheck "Auto-deploy"

## Rollback

If you need to revert to a previous version:

1. Go to Render Dashboard → Your Service
2. Click "Deployments"
3. Find the previous working deployment
4. Click "Redeploy"

## Cost Estimation (Free Tier)

- **Web Service**: Free (sleeps after 15 min inactivity)
- **Database**: Available
- **Additional**: Add-ons available for real-time databases

**For Production**: Consider upgrading to a paid plan for 99.99% uptime SLA

## Next Steps

1. ✅ Deploy to Render
2. 📧 Set up email notifications
3. 🔒 Configure custom domain
4. 🗄️ Migrate to persistent database
5. 📊 Set up monitoring & alerts

## Support

For Render-specific issues: https://render.com/docs
For application issues: Check application logs in Render dashboard

---

**Happy Deploying! 🚀**
