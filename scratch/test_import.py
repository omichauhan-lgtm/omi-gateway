import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from api.main import app
    print("Main app imported successfully!")
except Exception as e:
    import traceback
    traceback.print_exc()
