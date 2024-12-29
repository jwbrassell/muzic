# Technical Specifications

## Database Schema

### Ad Campaign System

#### ad_campaigns
```sql
CREATE TABLE ad_campaigns (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    start_date DATETIME,
    end_date DATETIME,
    target_percentage FLOAT,
    status TEXT DEFAULT 'active'
);
```

Purpose:
- Stores campaign metadata
- Manages campaign lifecycle
- Controls targeting parameters

#### ad_assets
```sql
CREATE TABLE ad_assets (
    id INTEGER PRIMARY KEY,
    campaign_id INTEGER,
    image_path TEXT,
    audio_path TEXT,
    duration INTEGER,
    FOREIGN KEY (campaign_id) REFERENCES ad_campaigns(id)
);
```

Purpose:
- Links media assets to campaigns
- Tracks asset metadata
- Manages asset relationships

## API Endpoints

### Campaign Management

#### Create Campaign
```
POST /api/campaigns
{
    "name": "Campaign Name",
    "start_date": "2024-01-01",
    "end_date": "2024-02-01",
    "target_percentage": 15.0
}
```

#### Update Campaign
```
PUT /api/campaigns/{id}
{
    "status": "paused",
    "target_percentage": 20.0
}
```

### Asset Management

#### Upload Asset
```
POST /api/campaigns/{id}/assets
Content-Type: multipart/form-data
{
    "image": (binary),
    "audio": (binary)
}
```

#### List Assets
```
GET /api/campaigns/{id}/assets
Response:
{
    "assets": [
        {
            "id": 1,
            "image_url": "/media/images/ad1.jpg",
            "audio_url": "/media/audio/ad1.mp3",
            "duration": 30
        }
    ]
}
```

## Module Structure

### Core Components

#### database.py
```python
class Database:
    def __init__(self):
        self.connection = None
        
    async def connect(self):
        """Establish database connection with connection pool"""
        
    async def execute(self, query, params=None):
        """Execute query with optional parameters"""
        
    async def fetch_one(self, query, params=None):
        """Fetch single result"""
        
    async def fetch_all(self, query, params=None):
        """Fetch multiple results"""
```

#### config.py
```python
class Config:
    # Database settings
    DB_PATH = "path/to/db"
    POOL_SIZE = 5
    
    # Media settings
    MEDIA_PATH = "path/to/media"
    ALLOWED_TYPES = ["mp3", "wav", "mp4"]
    
    # Cache settings
    REDIS_URL = "redis://localhost:6379"
    CACHE_TTL = 3600
```

### Ad System Components

#### campaign.py
```python
class CampaignManager:
    def __init__(self, db, cache):
        self.db = db
        self.cache = cache
        
    async def create_campaign(self, data):
        """Create new campaign"""
        
    async def update_campaign(self, id, data):
        """Update existing campaign"""
        
    async def get_campaign(self, id):
        """Get campaign details"""
```

#### scheduler.py
```python
class AdScheduler:
    def __init__(self, db, cache):
        self.db = db
        self.cache = cache
        
    async def schedule_ad(self, campaign_id, playlist_id):
        """Schedule ad for playlist"""
        
    async def get_next_ad(self, playlist_id):
        """Get next ad for playlist"""
```

## Background Tasks

### Celery Tasks

#### Media Processing
```python
@celery.task
def process_media_asset(asset_id):
    """Process uploaded media files"""
    # 1. Validate file
    # 2. Extract metadata
    # 3. Generate thumbnails
    # 4. Update database
```

#### Analytics Processing
```python
@celery.task
def process_analytics():
    """Process analytics data"""
    # 1. Aggregate play counts
    # 2. Calculate engagement
    # 3. Generate reports
    # 4. Cache results
```

## Caching Strategy

### Redis Structure

#### Campaign Cache
```
Key: campaign:{id}
Value: {
    "name": "Campaign Name",
    "status": "active",
    "target_percentage": 15.0
}
TTL: 3600
```

#### Playlist Cache
```
Key: playlist:{id}:ads
Value: [
    {
        "ad_id": 1,
        "priority": 5,
        "last_played": "timestamp"
    }
]
TTL: 300
```

## Frontend Components

### Campaign Dashboard
```javascript
class CampaignDashboard {
    constructor() {
        this.campaigns = [];
        this.selectedCampaign = null;
    }
    
    async loadCampaigns() {
        // Load campaign data
    }
    
    async updateCampaign(id, data) {
        // Update campaign
    }
    
    renderDashboard() {
        // Render UI
    }
}
```

### Asset Manager
```javascript
class AssetManager {
    constructor(campaignId) {
        this.campaignId = campaignId;
        this.assets = [];
    }
    
    async uploadAsset(file) {
        // Handle file upload
    }
    
    async previewAsset(assetId) {
        // Show asset preview
    }
}
```

## Error Handling

### Error Codes
```python
class ErrorCodes:
    CAMPAIGN_NOT_FOUND = "CAMPAIGN_001"
    ASSET_UPLOAD_FAILED = "ASSET_001"
    SCHEDULE_CONFLICT = "SCHEDULE_001"
    INVALID_DATE_RANGE = "DATE_001"
```

### Error Responses
```json
{
    "error": {
        "code": "CAMPAIGN_001",
        "message": "Campaign not found",
        "details": {
            "campaign_id": 123
        }
    }
}
```

## Monitoring

### Metrics
- Request latency
- Cache hit rate
- Media processing time
- Ad delivery accuracy
- System resource usage

### Logging
```python
logger.info("Campaign created", extra={
    "campaign_id": campaign.id,
    "user_id": user.id,
    "timestamp": datetime.now()
})
```

## Security

### Asset Validation
```python
def validate_asset(file):
    """Validate uploaded asset"""
    # 1. Check file type
    # 2. Scan for malware
    # 3. Verify size limits
    # 4. Validate metadata
```

### Access Control
```python
@requires_permission('campaign:write')
async def update_campaign(campaign_id):
    """Update campaign with permission check"""
```

## Testing Strategy

### Unit Tests
```python
def test_campaign_creation():
    """Test campaign creation"""
    campaign = Campaign(name="Test")
    assert campaign.status == "draft"
```

### Integration Tests
```python
async def test_ad_scheduling():
    """Test ad scheduling flow"""
    # 1. Create campaign
    # 2. Upload assets
    # 3. Schedule ad
    # 4. Verify delivery
```

## Deployment

### Dependencies
```
Flask==2.0.1
Celery==5.2.3
Redis==4.3.4
SQLAlchemy==1.4.23
```

### Environment Variables
```
DATABASE_URL=sqlite:///path/to/db
REDIS_URL=redis://localhost:6379
MEDIA_PATH=/path/to/media
LOG_LEVEL=INFO
