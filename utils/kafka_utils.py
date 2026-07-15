"""
Kafka utilities for event logging in ETL pipeline.
"""

import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, Any

from kafka import KafkaProducer, KafkaConsumer

logger = logging.getLogger(__name__)

# Configuration - read from environment
KAFKA_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 
                          'kafka:9092' if os.path.exists('/.dockerenv') else 'localhost:9093')

# Topic names
TOPIC_ETL_LOGS = 'youtube_etl_logs'
TOPIC_ETL_ERRORS = 'youtube_etl_errors'
TOPIC_ETL_METRICS = 'youtube_etl_metrics'

# PRODUCER

def create_producer():
    """
    Create Kafka producer with retry logic.
    Returns None if Kafka is not available (graceful degradation).
    """
    try:
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_SERVERS,
            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
            acks='all',  # Wait for all replicas
            retries=3,
            request_timeout_ms=10000,
        )
        logger.info(f"✅ Kafka producer connected to {KAFKA_SERVERS}")
        return producer
    except Exception as e:
        logger.warning(f"⚠️ Kafka producer failed: {e}. Running without Kafka.")
        return None

def publish_event(producer, event_type: str, data: Dict[str, Any], 
                  topic: str = TOPIC_ETL_LOGS) -> bool:
    """
    Publish an event to Kafka.
    
    Args:
        producer: Kafka producer (can be None)
        event_type: 'extract_started', 'transform_completed', etc.
        data: Event payload
        topic: Kafka topic name
    
    Returns:
        bool: True if published, False if failed
    """
    if producer is None:
        # Log to console if Kafka not available
        logger.info(f"📝 EVENT [{event_type}]: {data}")
        return False
    
    try:
        event = {
            'event_type': event_type,
            'timestamp': datetime.now().isoformat(),
            'data': data,
        }
        
        producer.send(topic, event)
        producer.flush()
        logger.debug(f"✅ Event published: {event_type}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to publish event: {e}")
        return False

def log_extract_started(producer, channel_id: str):
    """Log extract start event."""
    publish_event(producer, 'extract_started', {
        'channel_id': channel_id,
        'timestamp_start': datetime.now().isoformat()
    })

def log_extract_completed(producer, channel_id: str, record_count: int, duration: float):
    """Log extract completion event."""
    publish_event(producer, 'extract_completed', {
        'channel_id': channel_id,
        'record_count': record_count,
        'duration_seconds': round(duration, 2),
        'timestamp_end': datetime.now().isoformat()
    })

def log_transform_started(producer, record_count: int):
    """Log transform start event."""
    publish_event(producer, 'transform_started', {
        'record_count': record_count,
        'timestamp_start': datetime.now().isoformat()
    })

def log_transform_completed(producer, record_count: int, categories: dict, duration: float):
    """Log transform completion event."""
    publish_event(producer, 'transform_completed', {
        'record_count': record_count,
        'categories': categories,
        'duration_seconds': round(duration, 2),
        'timestamp_end': datetime.now().isoformat()
    })

def log_load_started(producer, record_count: int):
    """Log load start event."""
    publish_event(producer, 'load_started', {
        'record_count': record_count,
        'timestamp_start': datetime.now().isoformat()
    })

def log_load_completed(producer, record_count: int, table_name: str, duration: float):
    """Log load completion event."""
    publish_event(producer, 'load_completed', {
        'record_count': record_count,
        'table_name': table_name,
        'duration_seconds': round(duration, 2),
        'timestamp_end': datetime.now().isoformat()
    })

def log_error(producer, error_msg: str, context: Dict[str, Any]):
    """Log error to error topic."""
    publish_event(producer, 'error', {
        'error': error_msg,
        'context': context,
        'timestamp': datetime.now().isoformat()
    }, TOPIC_ETL_ERRORS)

def log_metrics(producer, metrics: Dict[str, Any]):
    """Log performance metrics."""
    publish_event(producer, 'metrics', metrics, TOPIC_ETL_METRICS)

# CONSUMER

def create_consumer(topics, group_id='monitoring_service'):
    """
    Create Kafka consumer.
    """
    try:
        consumer = KafkaConsumer(
            *topics,
            bootstrap_servers=KAFKA_SERVERS,
            value_deserializer=lambda v: json.loads(v.decode('utf-8')),
            group_id=group_id,
            auto_offset_reset='latest',
            enable_auto_commit=True,
            consumer_timeout_ms=10000,
        )
        logger.info(f"✅ Kafka consumer connected to topics: {topics}")
        return consumer
    except Exception as e:
        logger.warning(f"⚠️ Kafka consumer failed: {e}")
        return None

def consume_events(consumer, callback=None, timeout=60):
    """
    Consume events from Kafka.
    
    Args:
        consumer: Kafka consumer
        callback: Function called for each event
        timeout: Max seconds to wait
    """
    if consumer is None:
        logger.warning("⚠️ No Kafka consumer available")
        return
    
    logger.info(f"🔄 Listening for events... (Press Ctrl+C to stop)")
    
    start_time = time.time()
    
    try:
        for message in consumer:
            event = message.value
            topic = message.topic
            
            if callback:
                callback(topic, event)
            else:
                # Default: print to console
                print_event(topic, event)
            
            # Check timeout
            if timeout and (time.time() - start_time) > timeout:
                break
                
    except KeyboardInterrupt:
        logger.info("✅ Stopping consumer...")
    except Exception as e:
        logger.error(f"❌ Consumer error: {e}")
    finally:
        consumer.close()

def print_event(topic: str, event: dict):
    """Pretty print an event."""
    event_type = event.get('event_type', 'unknown')
    data = event.get('data', {})
    timestamp = event.get('timestamp', 'unknown')
    
    # Color code for different event types
    if 'error' in event_type:
        prefix = "❌ ERROR"
    elif 'completed' in event_type or 'success' in event_type:
        prefix = "✅ SUCCESS"
    else:
        prefix = "📋 EVENT"
    
    print(f"{prefix} [{topic}] {event_type} @ {timestamp[:19]}")
    
    # Pretty print data
    for key, value in data.items():
        if key == 'categories':
            print(f"  📊 Categories: {value}")
        elif 'duration' in key:
            print(f"  ⏱️  {key}: {value}s")
        elif 'record_count' in key:
            print(f"  📊 {key}: {value:,}")
        else:
            print(f"  • {key}: {value}")
    print()