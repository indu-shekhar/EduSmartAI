# ChromaDB Configuration to disable telemetry
import os
import chromadb

# Disable telemetry before any ChromaDB operations
os.environ['ANONYMIZED_TELEMETRY'] = 'False'

# Override the telemetry methods to prevent errors
try:
    from chromadb.telemetry.product.posthog import Posthog
    original_capture = Posthog.capture
    
    def silent_capture(self, *args, **kwargs):
        """Silent capture method that doesn't send telemetry"""
        pass
    
    Posthog.capture = silent_capture
except ImportError:
    # If the telemetry module doesn't exist, no need to patch
    pass
