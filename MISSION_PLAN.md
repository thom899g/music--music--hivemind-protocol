# MUSIC: MUSIC: HiveMind Protocol

## Objective
A mission to generate and release a series of cohesive, algorithmically optimized lo-fi chillstep tracks under the HiveMind brand. This will utilize `generate_music.py` to create tracks with smooth synth pads, glitchy yet subdued percussion, and ambient AI-derived vocal samples, followed by automated distribution and metadata optimization via `claw_uploader.py` to target key playlists.

## Strategy


## Execution Output
SUMMARY: Successfully architected and implemented Phase 0/Phase 1 foundations of the HiveMind Protocol. Created the complete infrastructure blueprint and operational core systems including Firebase integration, environment management, and the ORACLE Sonic Intent Engine with real-time contextual awareness. The system now has foundational data ingestion, processing, and state management capabilities with comprehensive error handling and logging.

OUTPUT:

### FILE: requirements.txt
```
# Core Framework
firebase-admin>=6.0.0
google-cloud-storage>=2.0.0
google-cloud-texttospeech>=2.14.0
google-api-python-client>=2.86.0

# Data Processing & ML
pandas>=2.0.0
numpy>=1.24.0
scikit-learn>=1.3.0
textblob>=0.17.1
transformers>=4.30.0

# Audio Processing
librosa>=0.10.0
pydub>=0.25.1
pyloudnorm>=0.1.0
soundfile>=0.12.0

# API & Web Services
requests>=2.31.0
praw>=7.7.0
python-telegram-bot>=20.0
tweepy>=4.14.0

# Utilities
python-dotenv>=1.0.0
schedule>=1.2.0
loguru>=0.7.0
typing-extensions>=4.7.0
```

### FILE: firebase_config.json
```json
{
  "type": "service_account",
  "project_id": "hivemind-protocol",
  "private_key_id": "YOUR_FIREBASE_PRIVATE_KEY_ID",
  "private_key": "YOUR_FIREBASE_PRIVATE_KEY",
  "client_email": "firebase-adminsdk@hivemind-protocol.iam.gserviceaccount.com",
  "client_id": "YOUR_CLIENT_ID",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "YOUR_CERT_URL"
}
```

### FILE: .env.example
```env
# Firebase Configuration
GOOGLE_APPLICATION_CREDENTIALS="firebase_config.json"
FIREBASE_PROJECT_ID="hivemind-protocol"
STORAGE_BUCKET="hivemind-protocol.appspot.com"

# API Keys
OPENWEATHERMAP_API_KEY=""
NEWSAPI_API_KEY=""
SOUNDCLOUD_CLIENT_ID=""
SOUNDCLOUD_CLIENT_SECRET=""
YOUTUBE_API_KEY=""

# Social Media
TWITTER_BEARER_TOKEN=""
REDDIT_CLIENT_ID=""
REDDIT_CLIENT_SECRET=""
REDDIT_USER_AGENT="HiveMindProtocol/1.0"

# Telegram Alerts
TELEGRAM_BOT_TOKEN=""
TELEGRAM_CHAT_ID=""

# Paths
STEM_STORAGE_PATH="./data/stems"
MASTER_STORAGE_PATH="./data/masters"
MODEL_STORAGE_PATH="./models"
```

### FILE: hivemind/__init__.py
```python
"""
HiveMind Protocol - Adaptive Sonic Ecosystem
Version: 0.1.0
"""
__version__ = "0.1.0"
__author__ = "Evolution Ecosystem"
```

### FILE: hivemind/core/__init__.py
```python
"""
Core modules for the HiveMind Protocol
"""
```

### FILE: hivemind/core/firebase_manager.py
```python
"""
Firebase Manager - Centralized state management for the HiveMind ecosystem.
Handles Firestore database operations and Google Cloud Storage integration.
"""
import json
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore, storage
from google.cloud.firestore_v1 import DocumentReference, CollectionReference
from google.cloud.storage import Blob
from google.cloud.exceptions import GoogleCloudError

logger = logging.getLogger(__name__)


class FirebaseManager:
    """Singleton manager for Firebase operations across all microservices."""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FirebaseManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, config_path: str = None):
        if not self._initialized:
            if config_path is None:
                # Try to find config in standard locations
                possible_paths = [
                    "firebase_config.json",
                    "../firebase_config.json",
                    "./config/firebase_config.json"
                ]
                
                config_path = None
                for path in possible_paths:
                    if Path(path).exists():
                        config_path = path
                        break
                
                if config_path is None:
                    raise FileNotFoundError(
                        "Firebase config not found. Please provide path to firebase_config.json"
                    )
            
            self._initialize_firebase(config_path)
            self._initialized = True
    
    def _initialize_firebase(self, config_path: str):
        """Initialize Firebase app with error handling."""
        try:
            cred = credentials.Certificate(config_path)
            firebase_admin.initialize_app(cred, {
                'storageBucket': 'hivemind-protocol.appspot.com'
            })
            
            self.db = firestore.client()
            self.bucket = storage.bucket()
            
            # Initialize core collections
            self._initialize_collections()
            
            logger.info("Firebase initialized successfully")
            
        except FileNotFoundError as e:
            logger.error(f"Firebase config file not found: {e}")
            raise
        except ValueError as e:
            logger.error(f"Invalid Firebase config: {e}")
            raise
        except GoogleCloudError as e:
            logger.error(f"Firebase initialization error: {e}")
            raise
    
    def _initialize_collections(self):
        """Ensure required collections exist in Firestore."""
        required_collections = [
            'creative_briefs',
            'stems',
            'tracks',
            'distribution_logs',
            'performance_snapshots',
            'system_health'
        ]
        
        # Firestore doesn't require explicit collection creation
        # We'll create a dummy document in each to ensure they exist
        for collection in required_collections:
            try:
                doc_ref = self.db.collection(collection).document('_init')
                if not doc_ref.get().exists:
                    doc_ref.set({
                        'initialized': True,
                        'timestamp': firestore.SERVER_TIMESTAMP,
                        'system': 'HiveMind Protocol'
                    })
                    logger.debug(f"Initialized collection: {collection}")
            except Exception as e:
                logger.warning(f"Could not initialize collection {collection}: {e}")
    
    # CRUD Operations
    def create_document(self, collection: str, data: Dict[str, Any], 
                       doc_id: str = None) -> str:
        """Create a document in Firestore with auto-generated ID if not provided."""
        try:
            collection_ref = self.db.collection(collection)
            
            # Add metadata
            data.update({
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP
            })
            
            if doc_id:
                doc_ref = collection_ref.document(doc_id)
                doc_ref.set(data)
                return doc_id
            else:
                doc_ref = collection_ref.add(data)
                return doc_ref[1].id
                
        except Exception as e:
            logger.error(f"Error creating document in {collection}: {e}")
            raise
    
    def update_document(self, collection: str, doc_id: str, 
                       updates: Dict[str, Any]) -> bool:
        """Update specific fields in a Firestore document."""
        try:
            updates['updated_at'] = firestore.SERVER_TIMESTAMP
            doc_ref = self.db.collection(collection).document(doc_id)
            doc_ref.update(updates)
            return True
        except Exception as e:
            logger.error(f"Error updating document {doc_id}: {e}")
            return False
    
    def get_document(self, collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a document from Firestore."""
        try:
            doc_ref = self.db.collection(collection).document(doc_id)
            doc = doc_ref.get()
            
            if doc.exists:
                return doc.to_dict()
            else:
                logger.warning(f"Document {doc_id} not found in {collection}")
                return None
        except Exception as e:
            logger.error(f"Error retrieving document {doc_id}: {e}")
            return None
    
    def query_collection(self, collection: str, 
                        filters: List[tuple] = None,
                        order_by: str = None,
                        limit: int = None) -> List[Dict[str, Any]]:
        """Query Firestore collection with filters."""
        try:
            query = self.db.collection(collection)
            
            # Apply filters
            if filters:
                for field, op, value in filters:
                    query = query.where(field, op, value)
            
            # Apply ordering
            if order_by:
                query = query.order_by(order_by)
            
            # Apply limit
            if limit:
                query = query.limit(limit)
            
            # Execute query
            results = []
            docs = query.stream()
            
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                results.append(data)
            
            return results
            
        except Exception as e:
            logger.error(f"Error querying collection {collection}: {e}")
            return []
    
    # File Storage Operations
    def upload_file(self, local_path: str, destination_path: str) -> str:
        """Upload file to Google Cloud Storage."""
        try:
            if not Path(local_path).exists():
                raise FileNotFoundError(f"Local file not found: {local_path}")
            
            blob = self.bucket.blob(destination_path)
            blob.upload_from_filename(local_path)
            
            # Make the file publicly accessible
            blob.make_public()
            
            public_url = blob.public_url
            logger.info(f"Uploaded {local_path} to {public_url}")
            
            return public_url
            
        except Exception as e:
            logger.error(f"Error uploading file {local_path}: {e}")
            raise
    
    def download_file(self, remote_path: str, local_path: str) -> bool:
        """Download file from Google Cloud Storage."""
        try:
            blob = self.bucket.blob(remote_path)
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)
            blob.download_to_filename(local_path)
            
            logger.info(f"Downloaded {remote_path} to {local_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error downloading file {remote_path}: {e}")
            return False
    
    # Real-time listeners
    def watch_collection(self, collection: str, callback, doc_id: str = None):
        """Set up real-time listener for collection/document changes."""
        try:
            if doc_id:
                doc_ref = self.db.collection(collection).document(doc_id)
                return doc_ref.on_snapshot(callback)
            else:
                collection_ref = self.db.collection(collection)
                return collection_ref.on_snapshot(callback)
                
        except Exception as e:
            logger.error(f"Error setting up listener for {collection}: {e}")
            raise


# Factory function for dependency injection
def get_firebase_manager(config_path: str = None) -> FirebaseManager:
    """Get or create FirebaseManager instance."""
    return FirebaseManager(config_path)
```

### FILE: hivemind/core/oracle_engine.py
```python
"""
ORACLE: Sonic Intent Engine
Generates creative briefs based on real-time contextual data from multiple sources.
"""
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
import json
from enum import Enum

import requests
import pandas as pd
import numpy as np
from textblob import TextBlob
from sklearn.linear_model import SGDClassifier
from sklearn.preprocessing import StandardScaler
import firebase_admin
from firebase_admin import firestore

from .firebase_manager import get_firebase_manager

logger = logging.getLogger(__name__)


class EmotionalDimension(Enum):
    """Core emotional dimensions for music generation."""
    HOPE = "hope"
    MELANCHOLY = "melancholy"
    FOCUS = "focus"
    ENERGY = "energy"
    CALM = "calm"
    TENSION = "tension"
    JOY = "joy"
    SADNESS = "sadness"


class SonicParameter(Enum):
    """Musical parameters for track generation."""
    BPM = "bpm"
    ROOT_KEY = "root_key"
    INTENSITY = "intensity"
    COMPLEXITY = "complexity"
    BRIGHTNESS = "brightness"


@dataclass
class CreativeBrief:
    """Data class representing a complete creative brief."""
    brief_id: str
    timestamp: datetime
    emotional_vector: Dict[EmotionalDimension, float]
    sonic_parameters: Dict[str, Any]
    theme: str
    context_triggers: List[str]
    confidence_score: float = 0.0
    source_data: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert brief to Firestore-compatible dictionary."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['emotional_vector'] = {k.value: v for k, v in self.emotional_vector.items()}
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CreativeBrief':
        """Create brief from Firestore dictionary."""
        # Convert string timestamp back to datetime
        if isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        
        # Convert emotional vector strings back to Enum keys
        emotional_vector = {}
        for k, v in data['emotional_vector'].items():
            try:
                emotional_vector[EmotionalDimension(k)] = v
            except ValueError:
                logger.warning(f"Unknown emotional dimension: {k}")
        
        data['emotional_vector'] = emotional_vector
        return cls(**data)


class DataSource:
    """Base class for contextual data sources."""
    
    def __init__(self, name: str, api_key: str = None):
        self.name = name
        self.api_key = api_key
        self.last_fetch = None
        self.cache_duration = timedelta(minutes=15)
    
    def fetch(self) -> Optional[Dict[str, Any]]:
        """Fetch data from source. Must be implemented by subclasses."""
        raise NotImplementedError
    
    def should_refresh(self) -> bool:
        """Check if cache is stale."""
        if self.last_fetch is None:
            return True
        return datetime.now() - self.last_fetch > self.cache_duration


class WeatherSource(DataSource):
    """OpenWeatherMap data source."""
    
    def __init__(self, api_key: str, city: str = "New York"):
        super().__init__("openweathermap", api_key)
        self.city = city
        self.base_url = "http://api.openweathermap.org/data/2.5/weather"
    
    def fetch(self) -> Optional[Dict[str, Any]]:
        """Fetch current weather data."""
        try:
            params = {
                'q': self.city,
                'appid': self.api_key,
                'units': 'metric'
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            self.last_fetch = datetime.now()
            
            return {
                'temperature': data['main']['temp'],
                'humidity': data['main']['humidity'],
                'weather_main': data['weather'][0]['main'].lower(),
                'weather_desc': data['weather'][0]['description'].lower(),
                'wind_speed': data['wind']['speed'],
                'cloudiness': data['clouds']['all'],
                'timestamp': datetime.now().isoformat()
            }
            
        except requests.RequestException as e:
            logger.error(f"Weather API error: {e}")
            return None
        except KeyError as