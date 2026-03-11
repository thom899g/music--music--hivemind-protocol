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