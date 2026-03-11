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