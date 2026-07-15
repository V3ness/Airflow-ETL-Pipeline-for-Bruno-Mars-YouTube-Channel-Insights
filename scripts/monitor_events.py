"""
Kafka event monitor - displays ETL events in real-time.
"""

import sys
import os
from datetime import datetime
from utils.kafka_utils import create_consumer, consume_events, print_event

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    
def handle_event(topic: str, event: dict):
    """Callback for handling events."""
    # Additional functions here:
    # - Send alerts for errors
    # - Store events in a database
    # - Update a dashboard
    print_event(topic, event)

def main():
    """Run the event monitor."""
    print("=" * 60)
    print("📊 Bruno Mars ETL Event Monitor")
    print("=" * 60)
    print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("📡 Listening for events... (Press Ctrl+C to stop)")
    print("-" * 60)
    
    # Create consumer for all topics
    consumer = create_consumer(
        topics=['youtube_etl_logs', 'youtube_etl_errors', 'youtube_etl_metrics'],
        group_id='monitoring_console'
    )
    
    try:
        # Consume events indefinitely
        consume_events(consumer, callback=handle_event, timeout=None)
        
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down monitor...")
        consumer.close()
        print("✅ Done")

if __name__ == "__main__":
    main()