# Dutchkem Trading AI — Deployment Guide

## Deployment Options

### Option 1: DigitalOcean (Recommended for Starters)

**Cost**: ~$20-50/month

1. Create a Droplet (Ubuntu 22.04, 4GB RAM, 2 vCPUs)
2. SSH into your server:
```bash
ssh root@your-server-ip
```

3. Install Docker:
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
```

4. Clone your repository:
```bash
git clone https://github.com/yourusername/dutchkem-trading-ai.git
cd dutchkem-trading-ai
```

5. Configure environment:
```bash
cp .env.example .env
nano .env
```

6. Start services:
```bash
cd docker
docker-compose -f docker-compose.prod.yml up -d
```

7. Setup SSL:
```bash
# Install Certbot
apt install certbot
certbot certonly --standalone -d yourdomain.com

# Copy certs
cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem docker/nginx/ssl/cert.pem
cp /etc/letsencrypt/live/yourdomain.com/privkey.pem docker/nginx/ssl/key.pem
```

---

### Option 2: AWS (Production Grade)

**Cost**: ~$50-200/month

1. **EC2 Instance**: t3.medium (2 vCPU, 4GB RAM)
2. **RDS**: PostgreSQL 16 (db.t3.micro)
3. **ElastiCache**: Redis 7
4. **S3**: For static files
5. **CloudFront**: CDN

Steps:
```bash
# Launch EC2 instance (Ubuntu 22.04 AMI)
# Open ports: 80, 443, 22

# SSH into instance
ssh -i your-key.pem ubuntu@your-ec2-ip

# Install Docker
sudo apt update
sudo apt install -y docker.io docker-compose
sudo systemctl enable docker

# Clone and deploy
git clone https://github.com/yourusername/dutchkem-trading-ai.git
cd dutchkem-trading-ai
cp .env.example .env
nano .env

# Start
cd docker
sudo docker-compose -f docker-compose.prod.yml up -d
```

---

### Option 3: Railway / Render (Easiest)

**Cost**: ~$20-70/month

1. Push code to GitHub
2. Connect GitHub to Railway or Render
3. Select "Docker" as build method
4. Add environment variables
5. Deploy

---

### Option 4: VPS (Hetzner / OVH)

**Cost**: ~$10-30/month

```bash
# Hetzner CX21 (2 vCPU, 4GB RAM, 40GB SSD)

# After server creation:
ssh root@your-server-ip

# Setup
apt update && apt upgrade -y
apt install -y git docker.io docker-compose

# Clone
git clone https://github.com/yourusername/dutchkem-trading-ai.git
cd dutchkem-trading-ai

# Configure
cp .env.example .env
nano .env

# Deploy
cd docker
docker-compose -f docker-compose.prod.yml up -d
```

---

## Environment Variables

Create `.env` file:

```env
# Security
SECRET_KEY=your-super-secret-key-change-this
DEBUG=False

# Database
DB_USER=dutchkem
DB_PASSWORD=your-secure-password
DB_HOST=postgres
DB_PORT=5432

# Redis
REDIS_PASSWORD=your-redis-password

# Celery
RABBITMQ_USER=guest
RABBITMQ_PASS=your-rabbitmq-password

# InfluxDB
INFLUXDB_TOKEN=your-influxdb-token
INFLUXDB_ORG=dutchkem

# MT5
MT5_HOST=your-mt5-server
MT5_PORT=1985

# CORS
ALLOWED_HOSTS=yourdomain.com,localhost
CORS_ALLOWED_ORIGINS=https://yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com

# Stripe (Payments)
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_PUBLISHABLE_KEY=pk_live_xxx

# SMTP (Email)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
```

---

## Post-Deployment

### 1. Create Superuser
```bash
docker-compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
```

### 2. Run Migrations
```bash
docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate
```

### 3. Collect Static Files
```bash
docker-compose -f docker-compose.prod.yml exec backend python manage.py collectstatic --noinput
```

### 4. Setup SSL (Nginx)
```bash
# Create SSL directory
mkdir -p docker/nginx/ssl

# Generate self-signed cert (development)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout docker/nginx/ssl/key.pem \
  -out docker/nginx/ssl/cert.pem
```

---

## Domain & DNS

1. Buy domain (Namecheap, Cloudflare, GoDaddy)
2. Point DNS to your server:
```
A Record: @ → your-server-ip
CNAME: www → yourdomain.com
```

3. Update Nginx config:
```nginx
server_name yourdomain.com www.yourdomain.com;
```

---

## Monitoring

### Access Services
| Service | URL | Default Login |
|---------|-----|---------------|
| Web App | https://yourdomain.com | - |
| API Docs | https://yourdomain.com/swagger/ | - |
| Admin | https://yourdomain.com/admin/ | superuser |
| Grafana | https://yourdomain.com:3000 | admin/admin |
| Prometheus | https://yourdomain.com:9090 | - |
| RabbitMQ | https://yourdomain.com:15672 | guest/guest |

---

## Backup Strategy

### Database Backup (Daily)
```bash
# Add to crontab
0 2 * * * docker-compose -f docker-compose.prod.yml exec -T postgres pg_dump -U dutchkem dutchkem_trading > /backups/db_$(date +%Y%m%d).sql
```

### Automated Backups (AWS S3)
```bash
# Install AWS CLI
apt install awscli

# Configure
aws configure

# Sync backups
aws s3 sync /backups s3://your-backup-bucket/dutchkem/
```

---

## Scaling

### Vertical Scale
- Upgrade Droplet/EC2 instance
- Increase RAM for more concurrent users

### Horizontal Scale
- Use Docker Swarm or Kubernetes
- Add load balancer
- Scale backend replicas

---

## Troubleshooting

```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs -f backend

# Restart services
docker-compose -f docker-compose.prod.yml restart

# Check status
docker-compose -f docker-compose.prod.yml ps

# Enter container
docker-compose -f docker-compose.prod.yml exec backend bash

# Run Django shell
docker-compose -f docker-compose.prod.yml exec backend python manage.py shell
```

---

## Cost Estimates

| Provider | Specs | Monthly Cost |
|----------|-------|--------------|
| DigitalOcean | 4GB, 2 vCPU | $24 |
| Hetzner | 4GB, 2 vCPU | $10 |
| AWS EC2 | t3.medium | $30 |
| Railway | 4GB | $20 |
| Render | 4GB | $25 |

**Recommended**: DigitalOcean or Hetzner for best value.
