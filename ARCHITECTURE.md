# CloudService Architecture

Detailed technical architecture documentation for CloudService.

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Load Balancer (Nginx)                  │
│  • Reverse Proxy  • SSL/TLS  • Rate Limiting  • Compression │
└────────────────┬──────────────────────────────────────────┘
                 │
        ┌────────┴──────────┐
        │                   │
    ┌───▼────────┐   ┌──────▼───────┐
    │   Django   │   │   Daphne     │
    │   Gunicorn │   │   (WebSocket)│
    │   (HTTP)   │   │              │
    └───┬────────┘   └──────┬───────┘
        │                   │
        └────────┬──────────┘
                 │
    ┌────────────┴─────────────┬──────────────┐
    │                          │              │
┌───▼─────────┐    ┌───────────▼──┐   ┌──────▼──────┐
│ PostgreSQL  │    │    Redis     │   │   Celery   │
│ (Database)  │    │   (Cache)    │   │  (Workers) │
└─────────────┘    └──────────────┘   └────────────┘
```

## 📦 Component Architecture

### Core Layer (core/)

**Models:**
- `StorageFile`: Represents files with full metadata
- `StorageFolder`: Folder hierarchy with recursive relationships
- `FileVersion`: Version control for files
- `ActivityLog`: Audit trail of all operations
- `Notification`: User notifications system

**Signals:**
- Auto-create initial file version on upload
- Auto-create root folder for new users
- Cleanup file from disk on deletion

**WebSocket Consumers:**
- `NotificationConsumer`: Real-time notifications
- `FileUploadConsumer`: Upload progress tracking

### Accounts Layer (accounts/)

**Models:**
- `UserProfile`: Extended user info with storage quotas
- `UserSession`: Session tracking and management
- `TwoFactorAuth`: 2FA configuration
- `AuditLog`: Account security audit trail
- `PasswordReset`: Secure password reset tokens

**Features:**
- JWT + Session authentication
- Storage quota management
- Two-factor authentication
- Session security and monitoring

### Sharing Layer (sharing/)

**Models:**
- `UserShare`: Direct user-to-user sharing
- `PublicLink`: Public access with security options
- `GroupShare`: Team sharing
- `Permission`: Granular permission control
- `ShareLog`: Sharing activity logging

**Features:**
- Role-based permissions
- Password-protected public links
- Expirable shares
- Audit logging

### Storage Layer (storage/)

**Models:**
- `StorageStats`: Cached statistics
- `StorageBackup`: Backup tracking
- `TrashBin`: Soft-delete functionality
- `StorageQuotaAlert`: Storage limit alerts

**Features:**
- Soft-delete with expiration
- Backup management
- Quota monitoring and alerts

### API Layer (api/)

**Components:**
- `Serializers`: Data validation and transformation
- `ViewSets`: REST API endpoints with CRUD
- `Permissions`: Custom permission classes
- `Pagination`: Configurable pagination

**Features:**
- OpenAPI/Swagger documentation
- Rate limiting per endpoint
- JWT authentication
- Comprehensive filtering and search

## 🔄 Request Flow

### File Upload Flow

```
Client Upload Request
    ↓
Nginx Rate Limiting
    ↓
Django View/API
    ├─ Validate file
    ├─ Check quota
    ├─ Save to disk
    ├─ Create StorageFile
    ├─ Create FileVersion
    ├─ Log activity
    └─ Send WebSocket update
    ↓
Celery Tasks
    ├─ Generate thumbnail
    ├─ Scan for viruses
    └─ Update statistics
    ↓
Client Success Response
```

### File Download Flow

```
Client Download Request
    ↓
Nginx Cache Check
    ↓
Django View
    ├─ Check permissions
    ├─ Verify ownership/share
    ├─ Increment download count
    └─ Log activity
    ↓
Return File
    ├─ Stream file content
    ├─ Set proper headers
    └─ Log completion
    ↓
Client Receives File
```

## 🔐 Security Architecture

### Authentication & Authorization

```
┌──────────────────────┐
│   User Credentials   │
└──────────┬───────────┘
           │
    ┌──────▼──────┐
    │ Django Auth │
    └──────┬──────┘
           │
    ┌──────▼──────────────┐
    │  Session/JWT Token  │
    └──────┬──────────────┘
           │
┌──────────┴────────────┬──────────────┐
│                       │              │
(User Permissions)   (File Permissions)  (Share Permissions)
```

### CORS & Headers

```python
# Allowed Origins: Configured in settings
# Security Headers:
- X-Frame-Options: SAMEORIGIN
- X-Content-Type-Options: nosniff
- X-XSS-Protection: enabled
- Content-Security-Policy: strict
- Referrer-Policy: strict-origin-when-cross-origin
```

### File Upload Validation

```
Upload Request
    ↓
Content-Type Validation
    ↓
File Extension Validation
    ↓
File Size Limit Check
    ↓
Magic Bytes Verification
    ↓
Virus Scan (optional)
    ↓
Storage Quota Check
    ↓
Save to Disk
```

## 🗄️ Database Schema Relationships

```
User (auth_user)
├── UserProfile (1-to-1)
├── StorageFolder (1-to-many)
│   └── StorageFolder (recursive)
│       └── StorageFile (1-to-many)
│           ├── FileVersion (1-to-many)
│           └── ActivityLog (1-to-many)
├── UserShare (as owner)
├── UserShare (as shared_with)
├── PublicLink (as owner)
├── Permission (through content_type)
├── UserSession (1-to-many)
├── Notification (1-to-many)
├── AuditLog (1-to-many)
└── ShareLog (through content_type)
```

## ⚡ Performance Optimization

### Database Optimization

**Indexing Strategy:**
```python
# Multi-column indexes
indexes = [
    Index(fields=['owner', 'parent']),  # Folder hierarchy
    Index(fields=['owner', 'is_public']),  # Visibility
    Index(fields=['user', '-created_at']),  # Activity logs
]
```

**Query Optimization:**
```python
# Use select_related for ForeignKey
StorageFile.objects.select_related('owner', 'folder')

# Use prefetch_related for reverse relations
folders = StorageFolder.objects.prefetch_related('subfolders', 'files')
```

### Caching Strategy

```
┌─────────────────────────────────┐
│     Django Cache (Redis)        │
├─────────────────────────────────┤
│ User Storage Stats              │
│ Storage Quota Information       │
│ Public Link Data                │
│ User Session Data               │
│ API Response Cache              │
└─────────────────────────────────┘
```

### API Optimization

- **Pagination**: 25 items per page (configurable)
- **Filtering**: By date, name, size, type
- **Searching**: Full-text search on file names
- **Rate Limiting**: 100 requests/hour for anonymous, 1000 for authenticated

## 🔄 Asynchronous Processing

### Celery Tasks

```
Task Queue (Redis)
    ├─ cleanup_trash (Periodic)
    ├─ update_storage_stats (Periodic)
    ├─ check_storage_quota (Periodic)
    ├─ send_activity_digest (Daily)
    ├─ cleanup_old_versions (Configurable)
    ├─ generate_backup (On-demand)
    └─ send_email (Event-triggered)
```

### WebSocket Real-time Updates

```
Client WebSocket Connection
    ├─ NotificationConsumer
    │   └─ Real-time file notifications
    └─ FileUploadConsumer
        └─ Upload progress updates
```

## 📊 Data Flow Architecture

### File Metadata Flow

```
File Upload
    ↓
Extract Metadata
├─ MIME Type Detection
├─ File Size Measurement
├─ SHA256 Hash Calculation
├─ File Extension Parsing
└─ Icon Classification
    ↓
Store in Database
    ↓
Update Cache
    ↓
WebSocket Notification
```

### Activity Logging Flow

```
User Action
    ↓
Middleware Capture
├─ User ID
├─ IP Address
├─ User Agent
└─ Timestamp
    ↓
Create ActivityLog
    ↓
Update StorageStats Cache
    ↓
Check for Alerts
    ├─ Storage Quota Warning
    └─ Security Events
        ↓
    Send Notifications
```

## 🔧 Configuration Layers

### Settings Hierarchy

```
Django Settings (config/settings.py)
    ├─ Base Configuration
    │   ├─ INSTALLED_APPS
    │   ├─ MIDDLEWARE
    │   └─ TEMPLATES
    ├─ Database Configuration
    │   ├─ PostgreSQL
    │   └─ Connection Pooling
    ├─ Cache Configuration
    │   └─ Redis
    ├─ Celery Configuration
    │   ├─ Broker
    │   └─ Result Backend
    └─ Security Configuration
        ├─ CSRF Settings
        ├─ CORS Settings
        └─ SSL/TLS Settings
```

## 📈 Scalability Considerations

### Horizontal Scaling

**Load Balancing:**
- Multiple Gunicorn workers
- Nginx upstream configuration
- Session affinity with Redis

**Database Scaling:**
- Read replicas for queries
- Write master for mutations
- Connection pooling (PgBouncer)

### Vertical Scaling

**Resource Optimization:**
- Increase CPU for faster processing
- Increase RAM for better caching
- SSD storage for database I/O

## 🔍 Monitoring & Logging

### Logging Strategy

```
Application Logs
    ├─ Django Logs
    │   ├─ DEBUG (development)
    │   ├─ INFO (events)
    │   └─ ERROR (exceptions)
    ├─ Celery Logs
    ├─ Nginx Logs
    └─ System Logs
        ↓
    Log Aggregation (optional)
        └─ Sentry/ELK Stack
```

### Metrics Collection

- Request count and response times
- Database query performance
- Cache hit/miss rates
- Celery task execution times
- Storage usage per user
- API endpoint usage

## 🚀 Deployment Architecture

### Docker Compose Services

```
┌──────────────────────────────────────────┐
│        Docker Compose Stack              │
├──────────────────────────────────────────┤
│ Web (Django)        → Port 8000          │
│ Daphne (WebSocket)  → Port 8001          │
│ Nginx (Proxy)       → Ports 80/443       │
│ PostgreSQL          → Port 5432          │
│ Redis              → Port 6379          │
│ Celery Worker      → Background          │
│ Celery Beat        → Scheduler           │
└──────────────────────────────────────────┘
```

### Kubernetes Architecture (Optional)

```
┌─────────────────────────────────────────┐
│      Kubernetes Cluster                 │
├─────────────────────────────────────────┤
│ Ingress                                 │
│ ├── Web Service                         │
│ ├── API Service                         │
│ └── WebSocket Service                   │
│ │                                       │
│ Deployments                             │
│ ├── Django (replicas: 3)                │
│ ├── Celery (replicas: 2)                │
│ ├── Celery Beat (replicas: 1)           │
│ └── Daphne (replicas: 2)                │
│ │                                       │
│ StatefulSets                            │
│ ├── PostgreSQL                          │
│ └── Redis                               │
│ │                                       │
│ ConfigMaps & Secrets                    │
│ ├── Settings                            │
│ └── Credentials                         │
└─────────────────────────────────────────┘
```

---

For implementation details, see [README.md](README.md) and source code.
