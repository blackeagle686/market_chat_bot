import subprocess
import sys
import time
from datetime import datetime

def run_cmd(cmd):
    """Runs a shell command and returns the output."""
    try:
        result = subprocess.run(cmd, shell=True, check=True, text=True, capture_output=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error executing: {cmd}")
        print(e.stderr)
        return None

def auto_push():
    print("[*] Starting auto-push to master...")
    
    # Check for changes
    changes = run_cmd("git status --porcelain")
    if not changes:
        print("[!] No changes detected. Nothing to push.")
        return

    # Prepare commit message
    if len(sys.argv) > 1:
        commit_message = " ".join(sys.argv[1:])
    else:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        commit_message = f"Auto-sync: {now}"

    print(f"[*] Committing with message: '{commit_message}'")
    
    # Execute Git steps
    steps = [
        "git add .",
        f'git commit -m "{commit_message}"',
        "git push origin master"
    ]
    
    for step in steps:
        print(f" -> Executing: {step}")
        if run_cmd(step) is None:
            print("[!] Push failed during execution.")
            return

    print("[+] Successfully pushed to master! Cheers brother.")

def monitor_and_push(interval=30):
    print(f"[*] Monitoring for changes every {interval} seconds... Press Ctrl+C to stop.")
    while True:
        try:
            # Check for changes
            changes = run_cmd("git status --porcelain")
            if changes:
                print(f"\n[*] Change detected at {datetime.now().strftime('%H:%M:%S')}")
                auto_push()
            
            time.sleep(interval)
        except KeyboardInterrupt:
            print("\n[!] Monitoring stopped by user.")
            break
        except Exception as e:
            print(f"\n[!] An error occurred: {e}")
            time.sleep(interval)

if __name__ == "__main__":
    # If arguments are passed, do a one-time push. Otherwise, start monitoring.
    if len(sys.argv) > 1:
        auto_push()
    else:
        monitor_and_push()
