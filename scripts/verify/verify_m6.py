import time
import requests

print("--- Verifying M6 WebUI Setup ---")
print("Ensure your Docker cluster is running (docker compose up -d)")
print("Checking if the FastAPI backend is serving the UI...")

try:
    res = requests.get("http://localhost:8000/ui/index.html")
    if res.status_code == 200:
        print("\nSUCCESS: WebUI is currently being served at: http://localhost:8000/ui/index.html")
        print("\nPlease open this URL in your browser to manually verify:")
        print("1. The 3-panel dwm-style glassmorphism interface.")
        print("2. Use Alt+1 through Alt+0 to switch workspaces (watch the terminal history).")
        print("3. Type /time or /joke in the center CLI panel.")
        print("4. Type 'hello' to trigger the WebSocket clarify prompt.")
        print("5. Verify the Semantic Terminal logs stream automatically on the right.")
        print("6. Click [Toggle Canvas] to verify the iframe renders correctly.")
    else:
        print(f"FAILED: UI returned status code {res.status_code}")
except Exception as e:
    print(f"FAILED: Could not reach the server: {e}")
