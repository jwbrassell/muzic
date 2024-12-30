# System Routes Documentation

## Admin Routes

### Dashboard & Core
- `/admin/` → Redirects to dashboard
- `/admin/dashboard` → Main admin dashboard
- `/admin/help` → Help documentation
- `/admin/logout` → Logout user

### Media Management
- `/admin/media/library` → Media library management
- `/admin/media/upload` → Media upload interface
- `/admin/media/tags` → Media tagging system
- `/admin/media/<path:filename>` → Serve media files (supports streaming)

### System Management
- `/admin/system/status` → System status dashboard
- `/admin/system/settings` → System settings interface
- `/admin/system/logs` → System logs viewer

### System API Endpoints
- `/admin/api/system/health` → Get system health metrics
- `/admin/api/system/metrics` → Get detailed system metrics
- `/admin/api/system/optimize` [POST] → Run system optimization
- `/admin/api/system/slow-queries` → Get slow query analysis

### Campaign Management
- `/admin/campaigns` → Campaign listing (with pagination)
- `/admin/campaigns/create` → Create new campaign
- `/admin/campaigns/<id>` → Campaign details
- `/admin/campaigns/<id>/edit` → Edit campaign
- `/admin/campaigns/<id>/assets` → Campaign assets management
- `/admin/campaigns/<id>/schedule` → Campaign schedule management
- `/admin/campaigns/<id>/analytics` → Campaign analytics

### Advertisement Management
- `/admin/ad/assets` → Ad assets management
- `/admin/ad/schedules` → Ad schedules management
- `/admin/ad/analytics` → Ad analytics dashboard

### Playlist Management
- `/admin/playlist/list` → Playlist listing
- `/admin/playlist/create` → Create new playlist

### Dashboard API Endpoints
- `/admin/quick-stats` → Get quick statistics
- `/admin/recent-activity` → Get recent activity

## Media API Routes

### Media Management
- `/api/media/library` [GET] → Get list of media files with filtering and pagination
- `/api/media/<id>` [GET] → Get detailed media information
- `/api/media/` [POST] → Upload media files
- `/api/media/<id>` [PUT] → Update media metadata
- `/api/media/<id>` [DELETE] → Delete media file
- `/api/media/scan` [POST] → Scan media directory for new files

### Tags
- `/api/media/tags` [GET] → Get list of all tags with usage counts

### Storage
- `/api/media/storage/stats` [GET] → Get media storage statistics

## Advertisement API Routes

### Campaign Management
- `/api/ads/` [GET] → Get list of campaigns with filtering
- `/api/ads/<id>` [GET] → Get campaign details
- `/api/ads/` [POST] → Create new campaign
- `/api/ads/<id>` [PUT] → Update campaign details

### Asset Management
- `/api/ads/<campaign_id>/assets` [POST] → Add asset to campaign
- `/api/ads/<campaign_id>/assets/<asset_id>` [PUT] → Update asset properties
- `/api/ads/<campaign_id>/assets/<asset_id>` [DELETE] → Remove asset from campaign

### Analytics & Reporting
- `/api/ads/<campaign_id>/metrics` [GET] → Get campaign performance metrics
- `/api/ads/<campaign_id>/performance` [GET] → Get detailed performance data
- `/api/ads/<campaign_id>/report` [GET] → Generate comprehensive campaign report
- `/api/ads/compare` [GET] → Compare metrics across multiple campaigns

## Playlist API Routes

### Playlist Management
- `/api/playlist/` [GET] → Get list of playlists with pagination
- `/api/playlist/<id>` [GET] → Get detailed playlist information
- `/api/playlist/` [POST] → Create new playlist
- `/api/playlist/<id>` [PUT] → Update playlist details
- `/api/playlist/<id>` [DELETE] → Delete playlist

### Playlist Items
- `/api/playlist/<id>/items` [POST] → Add items to playlist
- `/api/playlist/<id>/items` [DELETE] → Remove items from playlist
- `/api/playlist/<id>/move` [POST] → Move item to new position

### Playback Control
- `/api/playlist/<id>/next` [POST] → Get next item (with ad scheduling)
- `/api/playlist/<id>/shuffle` [POST] → Toggle shuffle mode
- `/api/playlist/<id>/repeat` [POST] → Toggle repeat mode

### Scheduling
- `/api/playlist/<id>/schedule` [GET] → Get playlist schedule
- `/api/playlist/<id>/schedule` [POST] → Set playlist schedule
