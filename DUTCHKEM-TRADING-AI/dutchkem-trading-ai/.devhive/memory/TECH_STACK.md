# Technology Stack

## Backend

### Core Framework
- **Django 4.2.8** - Web framework
- **Django REST Framework 3.14.0** - REST API toolkit
- **djangorestframework-simplejwt 5.3.1** - JWT authentication

### Database
- **PostgreSQL 16** - Primary relational database
- **TimescaleDB** - Time-series data extension
- **psycopg2-binary 2.9.9** - PostgreSQL adapter
- **django-timescaledb 0.2.8** - TimescaleDB integration

### Caching & Message Queue
- **Redis 7** - Caching and WebSocket channel layers
- **RabbitMQ 3** - Celery message broker
- **celery 5.3.6** - Async task queue
- **kombu 5.3.5** - Messaging library

### Real-Time Communication
- **channels 4.0.0** - WebSocket support
- **channels-redis 4.1.0** - Redis channel layer
- **daphne 4.0.0** - ASGI server

### Authentication & Security
- **django-otp 1.2.4** - TOTP-based MFA
- **cryptography 41.0.7** - Encryption utilities
- **django-ratelimit 4.1.0** - Rate limiting

### API Documentation
- **drf-yasg 1.21.7** - Swagger/OpenAPI documentation

### Payment Processing
- **stripe 7.12.0** - Stripe payment gateway
- **paystack-sdk 0.1.0** - Paystack payment gateway
- **python-dotenv 1.0.0** - Environment variables

### Trading & Finance
- **pandas 2.1.4** - Data manipulation
- **numpy 1.26.2** - Numerical computing
- **ta 0.11.0** - Technical analysis indicators
- **yfinance 0.2.33** - Yahoo Finance data

### AI & ML
- **openai 1.6.1** - OpenAI API client
- **langchain 0.0.350** - LLM orchestration

### Web Server
- **gunicorn 21.2.0** - WSGI HTTP server
- **whitenoise 6.6.0** - Static file serving
- **Pillow 10.1.0** - Image processing

## Frontend

### Web Application
- **React 18** - UI library
- **WebSocket** - Real-time data streaming
- **REST API** - Backend communication

### Mobile Application
- **React Native** - Cross-platform mobile framework
- **iOS & Android** - Platform targets

## Infrastructure

### Containerization
- **Docker** - Container runtime
- **Docker Compose** - Multi-container orchestration

### Services
- **Nginx** - Reverse proxy and load balancer
- **PostgreSQL/TimescaleDB** - Primary database (port 5432)
- **Redis** - Caching (port 6379)
- **InfluxDB 2.7** - Time-series data (port 8086)
- **RabbitMQ** - Message broker (ports 5672, 15672)

### Monitoring & Logging
- **Django Logging** - Application logging
- **Celery Monitoring** - Task queue monitoring

## Development Tools

### Code Quality
- **pylint** - Python linter
- **black** - Code formatter
- **isort** - Import sorting

### Testing
- **pytest** - Testing framework
- **pytest-django** - Django integration
- **factory_boy** - Test fixtures

### Documentation
- **Sphinx** - Documentation generator
- **Swagger/OpenAPI** - API documentation

## Environment Variables

```env
# Django
SECRET_KEY=your-secret-key
DEBUG=1
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_NAME=dutchkem_trading
DB_USER=dutchkem_admin
DB_PASSWORD=dutchkem_secure_2024
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_URL=redis://localhost:6379/0

# RabbitMQ
RABBITMQ_URL=amqp://dutchkem:dutchkem_mq_2024@localhost:5672/

# InfluxDB
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=your-influx-token
INFLUXDB_ORG=dutchkem
INFLUXDB_BUCKET=trading_data

# MetaTrader 5
MT5_HOST=localhost
MT5_PORT=3000

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000
```

## Version Compatibility

| Component | Version | Purpose |
|-----------|---------|---------|
| Python | 3.x | Runtime |
| Django | 4.2.8 | Web framework |
| PostgreSQL | 16 | Database |
| TimescaleDB | latest | Time-series |
| Redis | 7 | Caching |
| InfluxDB | 2.7 | Tick data |
| RabbitMQ | 3 | Message broker |
| Node.js | 18+ | Frontend build |
| React | 18 | Web UI |
| React Native | 0.72+ | Mobile UI |
