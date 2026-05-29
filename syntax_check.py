import sys
import traceback

try:
    from app import create_app
    app = create_app()
    print("App created successfully!")
except Exception as e:
    print("Error creating app:")
    traceback.print_exc()
