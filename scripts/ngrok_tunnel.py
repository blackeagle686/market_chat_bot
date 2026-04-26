import sys
import time
import os
from pyngrok import ngrok

def run():
    if len(sys.argv) < 2:
        print("Usage: python ngrok_tunnel.py <auth_token>")
        sys.exit(1)
        
    auth_token = sys.argv[1]
    ngrok.set_auth_token(auth_token)
    
    try:
        # Open a HTTP tunnel on port 8000
        public_url = ngrok.connect(8000).public_url
        print(f"Ngrok tunnel established: {public_url}")
        
        # Save the URL to a file for the deployment script to read
        with open("ngrok_url.txt", "w") as f:
            f.write(public_url)
            
        # Keep the process alive
        while True:
            time.sleep(60)
    except Exception as e:
        print(f"Error starting ngrok: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run()
