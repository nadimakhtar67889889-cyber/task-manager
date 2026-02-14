import os

# Ensure the server listens on the platform-provided port.
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"

