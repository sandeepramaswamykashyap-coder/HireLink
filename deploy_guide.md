# HireLink Deployment Guide 🚀

This guide explains how to take `HireLink` from your local Desktop to a live server on the internet.

## Option 1: Docker (Recommended)
We have included a `Dockerfile` that packages Python, Chrome, and the App into a single container.

### 1. Build and Run Locally
```bash
# Build the image
docker build -t hirelink-app .

# Run the container
docker run -p 8501:8501 hirelink-app
```
Access at: `http://localhost:8501`

### 2. Deploy to Railway.app (Easiest)
1.  Push this code to a **GitHub Repository**.
2.  Login to Railway.app.
3.  Click "New Project" -> "Deploy from GitHub repo".
4.  Railway will detect the `Dockerfile` automatically.
5.  **Add Variables:** Go to Settings -> Variables and add:
    *   `GEMINI_API_KEY`: Your key.
    *   `RAZORPAY_KEY_ID`: (Optional) Mock key.
6.  Click Deploy. You will get a free `https://hirelink-xxx.railway.app` URL.

### 3. Deploy to Render.com
1.  New "Web Service".
2.  Connect GitHub repo.
3.  Select "Docker" as the Environment.
4.  Add Environment Variables.
5.  Deploy.

---

## Option 2: VPS (DigitalOcean / AWS EC2)
If you prefer a raw Linux server (Ubuntu 22.04):

1.  **SSH into server:** `ssh root@your-ip`
2.  **Install System Deps:**
    ```bash
    apt-get update
    apt-get install -y python3-pip python3-venv google-chrome-stable unzip
    ```
3.  **Clone Code:** `git clone https://github.com/your/repo.git hirelink`
4.  **Setup Venv:**
    ```bash
    cd hirelink
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```
5.  **Run with Systemd** (Keep it alive):
    *   Copy `docs/hirelink.service` to `/etc/systemd/system/`
    *   `systemctl start hirelink`
    *   `systemctl enable hirelink`

---

## Important Notes
*   **Database:** The app uses `sqlite.db` by default. On cloud platforms (Railway/Render), **this file will be wiped on redeploy**.
*   **Persistent Data:** For production, switch `backend/database.py` to use `PostgreSQL` (Railway provides this for free).
*   **Google Analytics:** Edit `app.py` line 104 to replace `G-MEASUREMENT_ID` with your real ID.
