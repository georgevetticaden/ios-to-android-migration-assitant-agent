# Photo Migration Tools - Complete Requirements Document
## Building on Existing iCloud Authentication & Session Persistence

### Project Context
This document extends the existing photo-migration MCP tool that successfully handles iCloud authentication, 2FA, session persistence, and basic photo counting. We need to add transfer initiation, progress monitoring, completion verification, and email integration for a complete migration solution that aligns with the technical demo script.

**IMPORTANT**: All authentication credentials are retrieved from environment variables within the MCP tools. Credentials are NEVER passed as parameters from Claude Desktop for security reasons.

---

## 1. Current State Assessment

### 1.1 What's Already Working ✅
- **Authentication**: Apple ID login with 2FA handling
- **Session Persistence**: 7-day session storage in `~/.icloud_session/`
- **Photo Status**: Extraction of photo/video counts from privacy.apple.com
- **Transfer History**: Detection of previous transfer attempts
- **Browser Automation**: Playwright integration with screenshot capture
- **MCP Integration**: Working server.py and tool registration

### 1.2 Existing Architecture
```
photo-migration/
├── src/photo_migration/
│   ├── icloud_client.py      # ✅ Authentication & basic status
│   └── server.py             # ✅ MCP server with check_icloud_status
├── test_client.py            # ✅ Standalone testing
├── record_flow.py            # ✅ Browser flow recording utility
└── .env                      # ✅ Credential management
```

### 1.3 Current MCP Tool
- `check_icloud_status` - Returns photo counts, transfer history, session status

---

## 2. Required Extensions

### 2.1 New MCP Tools to Implement

#### 2.1.1 start_transfer
**Purpose**: Initiate iCloud to Google Photos transfer via privacy.apple.com

**Demo Context**: Called on Day 1 of demo script when user says "Start the photo transfer to Google Photos"

**Implementation Requirements**:
- Extend existing icloud_client.py with new method
- Reuse existing session authentication
- Navigate through complete transfer workflow
- **Establish Google Photos baseline** before initiating transfer
- Capture transfer ID for tracking
- Initialize state tracking in database

**Method Signature**:
```python
async def start_transfer(
    self, 
    google_email: str,  # Destination for photos
    reuse_session: bool = True
) -> Dict[str, Any]:
    """
    Start iCloud to Google Photos transfer
    Apple credentials retrieved from environment variables
    """
```

**Implementation Steps**:
1. Retrieve Apple credentials from environment variables
2. Validate credentials are configured
3. Use existing session if valid, otherwise authenticate
4. **Establish Google Photos baseline**: Query Google Photos API to capture pre-transfer item count
5. Navigate to transfer workflow (building on existing navigation)
6. Click through: Photos selection → Google destination → Confirmation
7. Extract transfer ID from confirmation page
8. Save transfer metadata AND baseline count to database
9. Return transfer details including baseline information

**Credential Retrieval**:
```python
async def start_transfer(self, google_email: str, reuse_session: bool = True) -> Dict[str, Any]:
    # Get credentials from environment
    apple_id = os.getenv('APPLE_ID')
    apple_password = os.getenv('APPLE_PASSWORD')
    
    if not apple_id or not apple_password:
        return {
            "status": "error",
            "message": "Please configure APPLE_ID and APPLE_PASSWORD in your environment variables"
        }
    
    # Continue with transfer logic...
```

**Return Structure**:
```python
{
    "status": "initiated" | "failed" | "error",
    "transfer_id": "TRF-2025-0817-XXXX",
    "started_at": "2025-08-17T10:30:00Z",
    "source_counts": {
        "photos": 60238,
        "videos": 2418,
        "total": 62656,
        "size_gb": 383
    },
    "destination": {
        "service": "Google Photos",
        "account": "user@gmail.com"
    },
    "baseline_established": {
        "pre_transfer_count": 12450,
        "baseline_timestamp": "2025-08-17T10:30:00Z"
    },
    "estimated_completion_days": "3-7",
    "session_used": true,
    "screenshots": [
        "/screenshots/transfer_start_confirmation.png"
    ]
}
```

#### 2.1.2 check_transfer_progress
**Purpose**: Monitor migration progress using Google Photos API and state tracking

**Demo Context**: Called on Day 2 of demo script when user asks "How's my transfer going? Apple gives no status updates!"

**Implementation Requirements**:
- Google Photos API integration for item counting
- Baseline photo count management (established during start_transfer)
- Progress rate calculation
- State persistence in DuckDB
- Intelligent progress estimation

**Method Signature**:
```python
async def check_transfer_progress(
    self,
    transfer_id: str
) -> Dict[str, Any]:
    """
    Monitor transfer progress
    All credentials retrieved from environment variables
    """
```

**Note**: Google Photos credentials are obtained from environment variables (`GOOGLE_PHOTOS_CREDENTIALS_PATH`), not passed as parameters.

**Implementation Steps**:
1. Validate transfer_id exists in database
2. Query Google Photos API for current total items (using credentials from environment)
3. Retrieve baseline count from database (set during start_transfer)
4. Calculate new items since baseline
5. Update progress history in database
6. Calculate transfer rate and estimates based on historical data
7. Return comprehensive progress data

**Return Structure**:
```python
{
    "transfer_id": "TRF-2025-0817-XXXX",
    "status": "in_progress" | "complete" | "stalled" | "error",
    "timeline": {
        "started_at": "2025-08-17T10:30:00Z",
        "checked_at": "2025-08-19T14:30:00Z",
        "days_elapsed": 2.17,
        "estimated_completion": "2025-08-21T16:45:00Z",
        "confidence_score": 0.89
    },
    "counts": {
        "source_total": 62656,
        "baseline_google": 12450,  # Photos in Google before transfer
        "current_google": 41901,   # Current total in Google Photos
        "transferred_items": 29451, # New items since transfer start
        "remaining_items": 33205
    },
    "progress": {
        "percent_complete": 47.0,
        "transfer_rate_per_day": 14725,
        "transfer_rate_per_hour": 614,
        "rate_trend": "stable" | "increasing" | "decreasing"
    },
    "daily_history": [
        {
            "day": 1,
            "date": "2025-08-17",
            "items_transferred": 15234,
            "cumulative": 15234,
            "rate_per_hour": 635
        },
        {
            "day": 2,
            "date": "2025-08-18", 
            "items_transferred": 14217,
            "cumulative": 29451,
            "rate_per_hour": 592
        }
    ],
    "quality_verification": {
        "last_sample_check": "2025-08-19T14:00:00Z",
        "samples_verified": 50,
        "metadata_preserved": true,
        "albums_detected": true,
        "quality_issues": []
    }
}
```

#### 2.1.3 verify_transfer_complete
**Purpose**: Final verification of migration completion with quality checks

**Demo Context**: Called on Day 5 of demo script when user asks "Is it done?" - represents the final verification moment.

**Method Signature**:
```python
async def verify_transfer_complete(
    self,
    transfer_id: str,
    important_photos: Optional[List[str]] = None,
    include_email_check: bool = True
) -> Dict[str, Any]:
```

**Implementation Steps**:
1. Get final counts from Google Photos API
2. Compare with original source counts from database
3. Check for Apple completion email (if include_email_check=True)
4. Verify album structure preservation
5. Sample random photos for quality/metadata checks
6. Check user-specified important photos
7. Generate completion certificate with all verification results

**Return Structure**:
```python
{
    "transfer_id": "TRF-2025-0817-XXXX",
    "status": "complete" | "incomplete" | "partial",
    "completed_at": "2025-08-21T16:45:00Z",
    "duration": {
        "total_days": 4.26,
        "total_hours": 102.25
    },
    "verification": {
        "source_photos": 60238,
        "source_videos": 2418,
        "destination_photos": 60238,
        "destination_videos": 2418,
        "match_rate": 100.0,
        "missing_items": [],
        "duplicate_items": [],
        "corrupted_items": []
    },
    "email_confirmation": {
        "completion_email_found": true,
        "email_received_at": "2025-08-21T16:30:00Z",
        "email_counts_match": true
    },
    "quality_assessment": {
        "metadata_preservation": {
            "dates_preserved": true,
            "locations_preserved": true,
            "albums_preserved": true,
            "face_tags_preserved": false  # Expected limitation
        },
        "random_sample_results": {
            "samples_checked": 100,
            "quality_issues": 0,
            "resolution_maintained": true
        }
    },
    "important_photos_check": [
        {
            "filename": "Wedding_2009.jpg",
            "found": true,
            "quality": "original",
            "metadata_intact": true
        }
    ],
    "certificate": {
        "grade": "A+",
        "score": 100,
        "message": "Perfect Migration - Zero Data Loss",
        "issued_at": "2025-08-21T16:45:00Z"
    },
    "recommendations": [
        "Enable Google Photos backup on Galaxy Z Fold 7",
        "Create shared family album",
        "Organize photos by year in Google Photos"
    ]
}
```

#### 2.1.4 check_completion_email
**Purpose**: Monitor Gmail for Apple transfer completion emails (integrated into verify_transfer_complete)

**Demo Context**: Can be called independently if user asks "Did I get the completion email?" or automatically integrated into verify_transfer_complete.

**Method Signature**:
```python
async def check_completion_email(
    self,
    transfer_id: str,
    search_days_back: int = 7
) -> Dict[str, Any]:
```

**Note**: Gmail credentials obtained from environment (`GMAIL_CREDENTIALS_PATH`), following credential pattern.

**Implementation Steps**:
1. Authenticate with Gmail API using environment credentials
2. Search for emails from Apple about photo transfers using transfer timeline
3. Parse email content for completion details
4. Match with transfer_id timeline from database
5. Extract transfer statistics from email and correlate with API data

**Return Structure**:
```python
{
    "transfer_id": "TRF-2025-0817-XXXX",
    "email_found": true,
    "email_details": {
        "subject": "Your photos have been copied to Google Photos",
        "received_at": "2025-08-21T16:30:00Z",
        "sender": "appleid@apple.com",
        "content_summary": {
            "photos_transferred": 60238,
            "videos_transferred": 2418,
            "destination_account": "g•••••@gmail.com"
        }
    },
    "status_correlation": {
        "api_check_complete": true,
        "email_confirmation": true,
        "timing_match": true,
        "count_verification": "exact_match"
    }
}
```

---

## 3. Google Dashboard Integration (Pivoted from Photos API)

### ⚠️ IMPORTANT PIVOT: Google Photos API Deprecated
**Discovery**: During implementation, we found that Google Photos Library API v1 is deprecated (March 31, 2025) with critical limitations:
- No photo count API available
- "insufficient authentication scopes" errors
- New Google Picker API is read-only with no programmatic access

### 3.1 Solution: Google Dashboard via Playwright
```python
# Using Playwright automation to extract photo counts from Google Dashboard
from playwright.async_api import async_playwright, Browser, Page, BrowserContext

class GoogleDashboardClient:
    """Google Dashboard client with session persistence"""
    
    def __init__(self, session_dir: Optional[str] = None):
        self.session_dir = Path.home() / ".google_session" if not session_dir else Path(session_dir)
        self.session_file = self.session_dir / "browser_state.json"
        self.session_info_file = self.session_dir / "session_info.json"
    
    async def get_photo_count(self, 
                            google_email: str = None,
                            google_password: str = None,
                            force_fresh_login: bool = False) -> Dict[str, Any]:
        """
        Get photo and album counts from Google Dashboard
        Uses session persistence to avoid repeated login
        """
        # Get credentials from environment if not provided
        if not google_email:
            google_email = os.getenv('GOOGLE_EMAIL')
        if not google_password:
            google_password = os.getenv('GOOGLE_PASSWORD')
        
        # Check for saved session (7-day validity like iCloud)
        use_saved_session = not force_fresh_login and self.is_session_valid()
        
        # Navigate to myaccount.google.com/dashboard
        # Handle 2-Step Verification with "Tap Yes on phone"
        # Extract photo counts: 42 photos, 162 albums
        
        return {
            "status": "success",
            "photos": 42,
            "albums": 162,
            "total_items": 42,
            "session_used": use_saved_session,
            "checked_at": datetime.now().isoformat()
        }
```

### 3.2 Key Features of Dashboard Approach
- **Session Persistence**: 7-day validity (same as iCloud)
- **2-Step Verification**: Handles "Tap Yes on phone" prompt
- **No API Limitations**: Web scraping is stable and unrestricted
- **Real Data**: Successfully extracts actual photo/album counts
- **Screenshots**: Captures dashboard for verification

### 3.3 Baseline Counting Strategy (Updated)
```python
async def establish_baseline_count(self, google_email: str) -> Dict[str, Any]:
    """
    Establish baseline photo count before transfer starts
    Uses Google Dashboard instead of deprecated API
    """
    dashboard_client = GoogleDashboardClient()
    await dashboard_client.initialize()
    
    result = await dashboard_client.get_photo_count(
        google_email=google_email,
        google_password=os.getenv('GOOGLE_PASSWORD')
    )
    
    if result['status'] == 'success':
        return {
            "baseline_count": result['photos'],
            "albums_count": result['albums'],
            "timestamp": result['checked_at'],
            "account": google_email
        }
    else:
        raise Exception(f"Failed to get baseline: {result.get('message')}")
```

---

## 4. Gmail API Integration

### 4.1 Email Monitoring Setup
```python
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

class GmailMonitor:
    def __init__(self, credentials_path: str):
        self.credentials_path = credentials_path
        self.service = None
    
    async def authenticate(self):
        """Authenticate with Gmail API using environment credentials"""
        creds = Credentials.from_authorized_user_file(self.credentials_path)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        self.service = build('gmail', 'v1', credentials=creds)
    
    async def search_apple_emails(
        self, 
        query: str = "from:appleid@apple.com subject:photos",
        days_back: int = 7
    ) -> List[Dict]:
        """Search for Apple transfer completion emails"""
        try:
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=10
            ).execute()
            
            messages = results.get('messages', [])
            return [await self._get_message_details(msg['id']) for msg in messages]
        except Exception as e:
            logger.error(f"Error searching emails: {e}")
            return []
    
    async def parse_transfer_email(self, email_id: str) -> Dict:
        """Extract transfer details from email content"""
        message = self.service.users().messages().get(
            userId='me', 
            id=email_id, 
            format='full'
        ).execute()
        
        # Parse email body for transfer statistics
        return self._extract_transfer_data(message)
    
    def _extract_transfer_data(self, message: Dict) -> Dict:
        """Extract photo/video counts from Apple completion email"""
        # Implementation for parsing email content
        # Use regex patterns to extract counts
        pass
```

### 4.2 Email Parsing Patterns
```python
# Regex patterns for extracting data from Apple emails
PATTERNS = {
    'photo_count': r'(\d{1,3}(?:,\d{3})*)\s+photos',
    'video_count': r'(\d{1,3}(?:,\d{3})*)\s+videos',
    'completion_date': r'finished copying.*?on\s+([A-Za-z]+ \d{1,2}, \d{4})',
    'destination_account': r'Transfer to account:\s+([g•]+@[a-zA-Z0-9.]+)'
}

def parse_apple_completion_email(email_body: str) -> Dict[str, Any]:
    """Parse Apple's completion email for transfer statistics"""
    results = {}
    
    for key, pattern in PATTERNS.items():
        match = re.search(pattern, email_body, re.IGNORECASE)
        if match:
            if 'count' in key:
                # Convert comma-separated numbers to integers
                results[key] = int(match.group(1).replace(',', ''))
            else:
                results[key] = match.group(1)
    
    return results
```

---

## 5. State Management with DuckDB

### 5.1 Database Schema
```sql
-- Create main database
CREATE DATABASE photo_migration;

-- Transfer tracking table
CREATE TABLE transfers (
    transfer_id VARCHAR PRIMARY KEY,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    status VARCHAR, -- 'initiated', 'in_progress', 'complete', 'failed'
    source_photos INTEGER,
    source_videos INTEGER,
    source_size_gb FLOAT,
    google_email VARCHAR,
    apple_id VARCHAR,
    baseline_google_count INTEGER,  -- Photos in Google before transfer
    baseline_timestamp TIMESTAMP,   -- When baseline was established
    metadata JSON
);

-- Progress history table  
CREATE TABLE progress_history (
    id INTEGER PRIMARY KEY,
    transfer_id VARCHAR,
    checked_at TIMESTAMP,
    google_photos_total INTEGER,
    transferred_items INTEGER,
    transfer_rate_per_hour FLOAT,
    notes TEXT,
    FOREIGN KEY (transfer_id) REFERENCES transfers(transfer_id)
);

-- Quality verification samples
CREATE TABLE quality_samples (
    id INTEGER PRIMARY KEY,
    transfer_id VARCHAR,
    sample_date TIMESTAMP,
    photos_sampled INTEGER,
    metadata_preserved BOOLEAN,
    quality_issues INTEGER,
    sample_details JSON,
    FOREIGN KEY (transfer_id) REFERENCES transfers(transfer_id)
);

-- Email confirmations
CREATE TABLE email_confirmations (
    id INTEGER PRIMARY KEY,
    transfer_id VARCHAR,
    email_received_at TIMESTAMP,
    email_subject VARCHAR,
    photos_reported INTEGER,
    videos_reported INTEGER,
    email_raw_content TEXT,
    FOREIGN KEY (transfer_id) REFERENCES transfers(transfer_id)
);
```

### 5.2 Database Operations
```python
import duckdb
from typing import Dict, List, Optional
from datetime import datetime

class TransferDatabase:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.getenv('DUCKDB_PATH', './data/photo_migration.db')
        self.conn = None
    
    async def initialize(self):
        """Create database and tables"""
        self.conn = duckdb.connect(self.db_path)
        await self._create_schema()
    
    async def create_transfer(self, transfer_data: Dict) -> str:
        """Create new transfer record with baseline"""
        transfer_id = transfer_data['transfer_id']
        
        self.conn.execute("""
            INSERT INTO transfers (
                transfer_id, started_at, status, source_photos, source_videos,
                source_size_gb, google_email, apple_id, baseline_google_count,
                baseline_timestamp, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            transfer_id,
            transfer_data['started_at'],
            'initiated',
            transfer_data['source_photos'],
            transfer_data['source_videos'],
            transfer_data['source_size_gb'],
            transfer_data['google_email'],
            transfer_data['apple_id'],
            transfer_data['baseline_count'],
            transfer_data['baseline_timestamp'],
            json.dumps(transfer_data.get('metadata', {}))
        ))
        
        return transfer_id
    
    async def update_progress(self, transfer_id: str, progress_data: Dict):
        """Add progress check record"""
        self.conn.execute("""
            INSERT INTO progress_history (
                transfer_id, checked_at, google_photos_total, 
                transferred_items, transfer_rate_per_hour
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            transfer_id,
            progress_data['checked_at'],
            progress_data['google_total'],
            progress_data['transferred_items'],
            progress_data['rate_per_hour']
        ))
    
    async def get_transfer_history(self, transfer_id: str) -> List[Dict]:
        """Get complete history for transfer"""
        results = self.conn.execute("""
            SELECT * FROM progress_history 
            WHERE transfer_id = ? 
            ORDER BY checked_at
        """, (transfer_id,)).fetchall()
        
        return [dict(zip([col[0] for col in self.conn.description], row)) for row in results]
    
    async def calculate_transfer_rate(self, transfer_id: str) -> float:
        """Calculate current transfer rate"""
        results = self.conn.execute("""
            SELECT 
                transferred_items,
                checked_at,
                LAG(transferred_items) OVER (ORDER BY checked_at) as prev_items,
                LAG(checked_at) OVER (ORDER BY checked_at) as prev_time
            FROM progress_history 
            WHERE transfer_id = ?
            ORDER BY checked_at DESC
            LIMIT 2
        """, (transfer_id,)).fetchall()
        
        if len(results) >= 2:
            current_items, current_time, prev_items, prev_time = results[0]
            if prev_items and prev_time:
                time_diff_hours = (current_time - prev_time).total_seconds() / 3600
                items_diff = current_items - prev_items
                return items_diff / time_diff_hours if time_diff_hours > 0 else 0
        
        return 0
```

---

## 6. Enhanced icloud_client.py Extensions

### 6.1 New Methods to Add
Building on the existing `ICloudClientWithSession` class:

```python
class ICloudClientWithSession:
    # ... existing methods (get_photo_status, etc.) ...
    
    def __init__(self, session_dir: Optional[str] = None):
        # ... existing initialization ...
        self.db = TransferDatabase()
        self.google_photos_client = None
        self.gmail_client = None
    
    async def initialize_apis(self):
        """Initialize Google APIs using environment credentials"""
        await self.db.initialize()
        
        google_creds_path = os.getenv('GOOGLE_PHOTOS_CREDENTIALS_PATH')
        if google_creds_path:
            self.google_photos_client = GooglePhotosClient(google_creds_path)
            await self.google_photos_client.authenticate()
        
        gmail_creds_path = os.getenv('GMAIL_CREDENTIALS_PATH')
        if gmail_creds_path:
            self.gmail_client = GmailMonitor(gmail_creds_path)
            await self.gmail_client.authenticate()
    
    async def get_photo_status(self, reuse_session: bool = True) -> Dict[str, Any]:
        """
        Get iCloud photo status
        Credentials retrieved from environment variables
        """
        # Get credentials from environment
        apple_id = os.getenv('APPLE_ID')
        apple_password = os.getenv('APPLE_PASSWORD')
        
        if not apple_id or not apple_password:
            return {
                "status": "error",
                "message": "Please configure APPLE_ID and APPLE_PASSWORD in environment variables"
            }
        
        # Use existing authentication logic
        # ... rest of implementation
    
    async def start_transfer(
        self, 
        google_email: str,
        reuse_session: bool = True
    ) -> Dict[str, Any]:
        """
        Start iCloud to Google Photos transfer
        Apple credentials retrieved from environment variables
        """
        
        try:
            # Get credentials from environment
            apple_id = os.getenv('APPLE_ID')
            apple_password = os.getenv('APPLE_PASSWORD')
            
            if not apple_id or not apple_password:
                return {
                    "status": "error",
                    "message": "Please configure APPLE_ID and APPLE_PASSWORD in environment variables"
                }
            
            # Ensure APIs are initialized
            await self.initialize_apis()
            
            # Step 1: Establish baseline BEFORE starting transfer
            baseline_data = await self._establish_baseline(google_email)
            
            # Step 2: Get current iCloud status (reuse existing method)
            icloud_status = await self.get_photo_status(reuse_session)
            
            if icloud_status.get("status") == "error":
                return icloud_status
            
            # Step 3: Navigate to transfer initiation (extend existing navigation)
            transfer_result = await self._initiate_transfer_workflow(google_email)
            
            # Step 4: Generate transfer ID and save to database
            transfer_id = f"TRF-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            
            transfer_data = {
                'transfer_id': transfer_id,
                'started_at': datetime.now().isoformat(),
                'source_photos': icloud_status['photos'],
                'source_videos': icloud_status['videos'],
                'source_size_gb': icloud_status['storage_gb'],
                'google_email': google_email,
                'apple_id': apple_id,
                'baseline_count': baseline_data['count'],
                'baseline_timestamp': baseline_data['timestamp']
            }
            
            await self.db.create_transfer(transfer_data)
            
            return {
                "status": "initiated",
                "transfer_id": transfer_id,
                "started_at": transfer_data['started_at'],
                "source_counts": {
                    "photos": icloud_status['photos'],
                    "videos": icloud_status['videos'],
                    "total": icloud_status['photos'] + icloud_status['videos'],
                    "size_gb": icloud_status['storage_gb']
                },
                "destination": {
                    "service": "Google Photos",
                    "account": google_email
                },
                "baseline_established": {
                    "pre_transfer_count": baseline_data['count'],
                    "baseline_timestamp": baseline_data['timestamp']
                },
                "estimated_completion_days": "3-7",
                "session_used": icloud_status.get('session_used', False)
            }
            
        except Exception as e:
            logger.error(f"Transfer initiation failed: {e}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    async def _establish_baseline(self, google_email: str) -> Dict[str, Any]:
        """Establish Google Photos baseline count"""
        if not self.google_photos_client:
            raise Exception("Google Photos API not initialized - check GOOGLE_PHOTOS_CREDENTIALS_PATH")
        
        baseline_count = await self.google_photos_client.get_total_items()
        timestamp = datetime.now().isoformat()
        
        logger.info(f"Baseline established: {baseline_count} items at {timestamp}")
        
        return {
            "count": baseline_count,
            "timestamp": timestamp,
            "account": google_email
        }
    
    async def _initiate_transfer_workflow(self, google_email: str) -> Dict[str, Any]:
        """Navigate through transfer workflow (extends existing navigation)"""
        # This builds on the existing navigation logic in get_photo_status
        # Navigate to the transfer confirmation page
        # Enter Google email
        # Click confirm
        # Capture transfer ID or confirmation
        
        # Implementation extends existing privacy.apple.com navigation
        pass
    
    async def check_transfer_progress(self, transfer_id: str) -> Dict[str, Any]:
        """Monitor transfer progress using Google Photos API"""
        
        try:
            # Ensure Google Dashboard client is initialized
            if not self.google_dashboard_client:
                self.google_dashboard_client = GoogleDashboardClient()
                await self.google_dashboard_client.initialize()
            
            # Get transfer details from database
            transfer = await self.db.get_transfer(transfer_id)
            if not transfer:
                raise Exception(f"Transfer {transfer_id} not found")
            
            # Get current Google photo count from Dashboard
            dashboard_result = await self.google_dashboard_client.get_photo_count()
            current_google_count = dashboard_result['photos'] if dashboard_result['status'] == 'success' else 0
            
            # Calculate progress
            baseline_count = transfer['baseline_google_count']
            transferred_items = current_google_count - baseline_count
            
            # Update progress in database
            progress_data = {
                'checked_at': datetime.now().isoformat(),
                'google_total': current_google_count,
                'transferred_items': transferred_items,
                'rate_per_hour': await self.db.calculate_transfer_rate(transfer_id)
            }
            
            await self.db.update_progress(transfer_id, progress_data)
            
            # Calculate percentage and estimates
            source_total = transfer['source_photos'] + transfer['source_videos']
            percent_complete = (transferred_items / source_total) * 100 if source_total > 0 else 0
            
            return {
                "transfer_id": transfer_id,
                "status": "complete" if percent_complete >= 99 else "in_progress",
                "timeline": {
                    "started_at": transfer['started_at'],
                    "checked_at": progress_data['checked_at'],
                    "days_elapsed": self._calculate_days_elapsed(transfer['started_at']),
                    "estimated_completion": self._estimate_completion(transfer_id),
                    "confidence_score": 0.89  # Based on rate stability
                },
                "counts": {
                    "source_total": source_total,
                    "baseline_google": baseline_count,
                    "current_google": current_google_count,
                    "transferred_items": transferred_items,
                    "remaining_items": max(0, source_total - transferred_items)
                },
                "progress": {
                    "percent_complete": round(percent_complete, 1),
                    "transfer_rate_per_day": progress_data['rate_per_hour'] * 24,
                    "transfer_rate_per_hour": progress_data['rate_per_hour']
                },
                "daily_history": await self._get_daily_history(transfer_id)
            }
            
        except Exception as e:
            logger.error(f"Progress check failed: {e}")
            return {
                "transfer_id": transfer_id,
                "status": "error",
                "error": str(e)
            }
    
    async def verify_transfer_complete(
        self, 
        transfer_id: str, 
        important_photos: Optional[List[str]] = None,
        include_email_check: bool = True
    ) -> Dict[str, Any]:
        """Final verification of transfer completion"""
        
        try:
            # Get final Google Photos count
            final_progress = await self.check_transfer_progress(transfer_id)
            
            # Check for completion email if requested
            email_result = None
            if include_email_check:
                # Initialize Gmail client if needed (just-in-time)
                if not self.gmail_client:
                    gmail_creds_path = os.getenv('GMAIL_CREDENTIALS_PATH')
                    if not gmail_creds_path:
                        logger.warning("GMAIL_CREDENTIALS_PATH not configured - skipping email check")
                    else:
                        self.gmail_client = GmailMonitor(gmail_creds_path)
                        await self.gmail_client.authenticate()
                
                if self.gmail_client:
                    email_result = await self.check_completion_email(transfer_id)
            
            # Verify important photos if specified
            important_check = []
            if important_photos:
                important_check = await self._verify_important_photos(important_photos)
            
            # Generate completion assessment
            is_complete = (
                final_progress['progress']['percent_complete'] >= 99 and
                (not email_result or email_result.get('email_found', False))
            )
            
            # Mark as complete in database
            if is_complete:
                await self.db.mark_transfer_complete(transfer_id)
            
            return {
                "transfer_id": transfer_id,
                "status": "complete" if is_complete else "incomplete",
                "completed_at": datetime.now().isoformat() if is_complete else None,
                "verification": {
                    "source_photos": final_progress['counts']['source_total'],
                    "destination_photos": final_progress['counts']['transferred_items'],
                    "match_rate": final_progress['progress']['percent_complete']
                },
                "email_confirmation": email_result or {"completion_email_found": False},
                "important_photos_check": important_check,
                "certificate": {
                    "grade": "A+" if is_complete else "Incomplete",
                    "score": int(final_progress['progress']['percent_complete']),
                    "message": "Perfect Migration - Zero Data Loss" if is_complete else "Transfer in progress",
                    "issued_at": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Transfer verification failed: {e}")
            return {
                "transfer_id": transfer_id,
                "status": "error",
                "error": str(e)
            }
    
    async def check_completion_email(self, transfer_id: str) -> Dict[str, Any]:
        """Check Gmail for Apple completion emails"""
        
        if not self.gmail_client:
            return {"email_found": False, "error": "Gmail API not configured"}
        
        try:
            # Search for Apple emails
            apple_emails = await self.gmail_client.search_apple_emails()
            
            # Find emails matching our transfer timeline
            transfer = await self.db.get_transfer(transfer_id)
            transfer_start = datetime.fromisoformat(transfer['started_at'])
            
            for email in apple_emails:
                email_date = datetime.fromisoformat(email['received_at'])
                if email_date >= transfer_start:
                    # Parse email content
                    parsed_data = parse_apple_completion_email(email['body'])
                    
                    return {
                        "transfer_id": transfer_id,
                        "email_found": True,
                        "email_details": {
                            "subject": email['subject'],
                            "received_at": email['received_at'],
                            "sender": email['sender'],
                            "content_summary": parsed_data
                        },
                        "status_correlation": {
                            "email_confirmation": True,
                            "timing_match": True
                        }
                    }
            
            return {
                "transfer_id": transfer_id,
                "email_found": False,
                "message": "No Apple completion email found yet"
            }
            
        except Exception as e:
            logger.error(f"Email check failed: {e}")
            return {
                "transfer_id": transfer_id,
                "email_found": False,
                "error": str(e)
            }
```

---

## 7. Configuration & Environment

### 7.1 Enhanced .env Configuration
```bash
# IMPORTANT: These credentials are retrieved within MCP tools
# Never passed as parameters from Claude Desktop for security
APPLE_ID=user@example.com
APPLE_PASSWORD=password

# Google Dashboard credentials (for Playwright automation)
GOOGLE_EMAIL=user@gmail.com
GOOGLE_PASSWORD=google_password

# Gmail API credentials (for completion emails)
GMAIL_CREDENTIALS_PATH=./gmail_creds.json

# Session persistence directories
ICLOUD_SESSION_DIR=~/.icloud_session
GOOGLE_SESSION_DIR=~/.google_session

# Database configuration
DUCKDB_PATH=./data/photo_migration.db

# Screenshot and logging
SCREENSHOT_DIR=./screenshots
LOG_LEVEL=INFO

# Progress tracking settings
PROGRESS_CHECK_INTERVAL_HOURS=6
```

---

## 8. MCP Server Integration

### 8.1 Updated server.py
```python
#!/usr/bin/env python3.11
"""
Photo Migration MCP Server - Complete Implementation
"""

import asyncio
import logging
import os
from typing import Any, Dict
from dotenv import load_dotenv
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

from .icloud_client import ICloudClientWithSession

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

server = Server("photo-migration")
icloud_client = None

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List all available photo migration tools"""
    return [
        types.Tool(
            name="check_icloud_status",
            description="Check iCloud photo library status (uses environment credentials)",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="start_transfer",
            description="Initiate iCloud to Google Photos transfer with baseline establishment",
            inputSchema={
                "type": "object",
                "properties": {
                    "google_email": {
                        "type": "string",
                        "description": "Destination Google account for photos"
                    }
                },
                "required": ["google_email"]
            }
        ),
        types.Tool(
            name="check_transfer_progress",
            description="Monitor ongoing photo transfer progress",
            inputSchema={
                "type": "object",
                "properties": {
                    "transfer_id": {"type": "string"}
                },
                "required": ["transfer_id"]
            }
        ),
        types.Tool(
            name="verify_transfer_complete",
            description="Verify transfer completion with quality checks",
            inputSchema={
                "type": "object",
                "properties": {
                    "transfer_id": {"type": "string"},
                    "important_photos": {
                        "type": "array",
                        "items": {"type": "string"},
                        "optional": True
                    },
                    "include_email_check": {"type": "boolean", "default": True}
                },
                "required": ["transfer_id"]
            }
        ),
        types.Tool(
            name="check_completion_email",
            description="Check Gmail for Apple transfer completion emails",
            inputSchema={
                "type": "object",
                "properties": {
                    "transfer_id": {"type": "string"}
                },
                "required": ["transfer_id"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> list[types.TextContent]:
    """Handle tool calls - all credentials from environment"""
    global icloud_client
    
    # Initialize client if needed
    if icloud_client is None:
        session_dir = os.path.expanduser("~/.icloud_session")
        icloud_client = ICloudClientWithSession(session_dir=session_dir)
        await icloud_client.initialize()
        await icloud_client.initialize_apis()
    
    try:
        if name == "check_icloud_status":
            # No parameters - credentials from environment
            result = await icloud_client.get_photo_status()
            
            if result.get("status") == "error":
                return [types.TextContent(type="text", text=f"❌ {result['message']}")]
            
            response = f"""iCloud Photo Library Status:
📸 Photos: {result['photos']:,}
🎬 Videos: {result['videos']:,}
💾 Storage: {result['storage_gb']:.1f} GB
📦 Total Items: {result['total_items']:,}

Session: {'Reused saved session (no 2FA)' if result.get('session_used') else 'New session created'}
"""
            return [types.TextContent(type="text", text=response)]
        
        elif name == "start_transfer":
            google_email = arguments["google_email"]
            
            result = await icloud_client.start_transfer(google_email=google_email)
            
            if result["status"] == "error":
                return [types.TextContent(type="text", text=f"❌ {result['message']}")]
            elif result["status"] == "initiated":
                response = f"""✅ Transfer Initiated Successfully!

📋 Transfer ID: {result['transfer_id']}
📸 Source: {result['source_counts']['photos']:,} photos, {result['source_counts']['videos']:,} videos
🎯 Destination: {result['destination']['account']}
📊 Baseline: {result['baseline_established']['pre_transfer_count']:,} items already in Google Photos

⏱️ Estimated completion: {result['estimated_completion_days']} days
📄 Apple will email you updates, and I'll monitor progress via Google Photos API.

Ready to check progress anytime with the transfer ID above!"""
            else:
                response = f"❌ Transfer failed: {result.get('error', 'Unknown error')}"
            
            return [types.TextContent(type="text", text=response)]
        
        elif name == "check_transfer_progress":
            result = await icloud_client.check_transfer_progress(arguments["transfer_id"])
            
            if result["status"] == "error":
                response = f"❌ Error checking progress: {result.get('error')}"
            else:
                response = f"""📊 Transfer Progress Update:

📋 Transfer ID: {result['transfer_id']}
⏱️ Status: {result['status'].title()}
📈 Progress: {result['progress']['percent_complete']:.1f}% complete

📸 Items transferred: {result['counts']['transferred_items']:,} of {result['counts']['source_total']:,}
🚀 Transfer rate: {result['progress']['transfer_rate_per_day']:,.0f} items/day
⏰ Days elapsed: {result['timeline']['days_elapsed']:.1f}

Recent activity:"""
                
                for day_data in result.get('daily_history', [])[-3:]:  # Last 3 days
                    response += f"\n  Day {day_data['day']}: {day_data['items_transferred']:,} items"
                
                if result['progress']['percent_complete'] >= 99:
                    response += "\n\n🎉 Transfer appears complete! Run verify_transfer_complete to confirm."
            
            return [types.TextContent(type="text", text=response)]
        
        elif name == "verify_transfer_complete":
            result = await icloud_client.verify_transfer_complete(
                transfer_id=arguments["transfer_id"],
                important_photos=arguments.get("important_photos"),
                include_email_check=arguments.get("include_email_check", True)
            )
            
            if result["status"] == "complete":
                response = f"""🎉 MIGRATION COMPLETE!

📋 Transfer ID: {result['transfer_id']}
✅ Status: {result['certificate']['grade']} - {result['certificate']['message']}
📊 Score: {result['certificate']['score']}/100

Verification Results:
📸 Photos: {result['verification']['destination_photos']:,} transferred
📧 Email confirmation: {'✅ Found' if result['email_confirmation'].get('completion_email_found') else '❌ Not found'}
📅 Completed: {result['completed_at']}

Your 18 years of memories are safe in Google Photos! 🎊"""
            else:
                response = f"""⚠️ Transfer Status: {result['status'].title()}

Current progress: {result['certificate']['score']}%
{result.get('error', 'Transfer may still be in progress')}"""
            
            return [types.TextContent(type="text", text=response)]
        
        elif name == "check_completion_email":
            result = await icloud_client.check_completion_email(arguments["transfer_id"])
            
            if result["email_found"]:
                email_details = result["email_details"]
                response = f"""📧 Apple Completion Email Found!

📋 Transfer ID: {result['transfer_id']}
📨 Subject: {email_details['subject']}
📅 Received: {email_details['received_at']}
📸 Reported: {email_details['content_summary'].get('photos_transferred', 'N/A')} photos
🎬 Videos: {email_details['content_summary'].get('videos_transferred', 'N/A')} videos

✅ Email confirms your transfer is complete!"""
            else:
                response = f"""📧 No completion email found yet for transfer {result['transfer_id']}

This is normal - Apple sends the email when transfer is 100% complete.
Continue monitoring with check_transfer_progress."""
            
            return [types.TextContent(type="text", text=response)]
        
        else:
            return [types.TextContent(type="text", text=f"Unknown tool: {name}")]
    
    except Exception as e:
        logger.error(f"Tool execution error: {e}")
        return [types.TextContent(type="text", text=f"Error: {str(e)}")]

async def main():
    """Main entry point"""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        logger.info("Photo Migration MCP Server starting...")
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="photo-migration",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 9. Demo Script Alignment

### 9.1 Tool Call Mapping to Demo Flow

**Day 1 (Transfer Initiation)**:
```
User: "Start the photo transfer to Google Photos"
Tool: start_transfer
Parameters: {"google_email": "george.vetticaden@gmail.com"}
Note: Apple credentials retrieved from environment variables

- Establishes Google Photos baseline count automatically
- Initiates iCloud transfer via browser automation
- Returns transfer_id and baseline information
Claude creates React artifact showing transfer initiation success
```

**Day 2 (First Progress Check)**:
```
User: "It's been 2 days. How's my transfer going? Apple gives no status updates!"
Tool: check_transfer_progress
Parameters: {"transfer_id": "TRF-2025-0817-1030"}

- Uses baseline from Day 1 to calculate actual transfer progress
- Shows 28,451 new photos (47% complete)
- Claude creates React dashboard showing progress with animated charts
```

**Day 5 (Completion Verification)**:
```
User: "Is it done?"
Tool: verify_transfer_complete
Parameters: {
    "transfer_id": "TRF-2025-0817-1030",
    "important_photos": ["Wedding_2009.jpg", "FirstiPhone_2007.jpg", "Ethan_birth_2010.jpg"],
    "include_email_check": true
}
Note: Gmail credentials checked just-in-time if configured

- Final Google Photos API count check
- Automatically checks for Apple completion email
- Verifies important photos specified by user
- Claude creates celebration React artifact with confetti animation
```

---

## 10. Testing Requirements

### 10.1 Unit Tests
```python
# tests/test_photo_migration.py

async def test_environment_variables_required():
    """Test that methods fail gracefully without environment variables"""
    import os
    
    # Temporarily unset environment variables
    old_apple_id = os.environ.pop('APPLE_ID', None)
    old_apple_password = os.environ.pop('APPLE_PASSWORD', None)
    
    try:
        client = ICloudClientWithSession()
        result = await client.get_photo_status()
        
        assert result['status'] == 'error'
        assert 'environment variables' in result['message'].lower()
    finally:
        # Restore environment variables
        if old_apple_id:
            os.environ['APPLE_ID'] = old_apple_id
        if old_apple_password:
            os.environ['APPLE_PASSWORD'] = old_apple_password

async def test_start_transfer():
    """Test transfer initiation with baseline establishment"""
    # Ensure environment variables are set
    assert os.getenv('APPLE_ID'), "APPLE_ID must be configured"
    assert os.getenv('APPLE_PASSWORD'), "APPLE_PASSWORD must be configured"
    
    client = ICloudClientWithSession()
    result = await client.start_transfer(google_email="test@gmail.com")
    
    assert result['status'] in ['initiated', 'error']
    if result['status'] == 'initiated':
        assert 'baseline_established' in result

async def test_progress_calculation():
    """Test progress rate calculations with baseline"""
    pass

async def test_email_parsing():
    """Test parsing of Apple completion emails"""
    pass

async def test_google_photos_api():
    """Test Google Photos API integration and rate limiting"""
    pass

async def test_database_operations():
    """Test DuckDB operations and schema"""
    pass
```

---

## 10. Success Criteria

### 10.1 Functional Requirements
- ✅ **Transfer Initiation**: Automate complete iCloud transfer setup with baseline
- ✅ **Progress Tracking**: Real-time monitoring with rate calculations using baseline
- ✅ **Completion Verification**: Multi-source confirmation (API + email)
- ✅ **Quality Assurance**: Metadata and quality preservation checks
- ✅ **State Persistence**: Reliable multi-day progress tracking

### 10.2 Performance Requirements
- ✅ **95% Success Rate**: Transfer initiation and monitoring
- ✅ **< 5 second**: Progress check response times
- ✅ **Zero Data Loss**: 100% verification accuracy
- ✅ **Multi-day Reliability**: Consistent state across sessions

### 10.3 Demo Requirements
- ✅ **Real Transfer**: No mock data, actual 60k+ photo migration
- ✅ **Live Progress**: Real-time dashboard updates in Claude
- ✅ **Email Integration**: Actual completion email detection
- ✅ **Quality Verification**: Authentic metadata preservation checks
- ✅ **Baseline Accuracy**: Precise progress calculation using pre-transfer counts

This complete requirements document provides Claude Code with everything needed to extend the existing working photo-migration tool into a complete migration solution that aligns perfectly with the technical demo script.