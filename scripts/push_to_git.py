import subprocess
import sys
from datetime import datetime

def run_command(command):
    try:
        result = subprocess.run(command, check=True, text=True, shell=True, capture_output=True)
        print(f"Success: {command}")
        if result.stdout:
            print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {command}")
        if e.stderr:
            print(e.stderr)
        sys.exit(1)

def push_to_git():
    print("Starting Git update process...")
    
    # Check if there are any changes
    status_result = subprocess.run("git status --porcelain", shell=True, capture_output=True, text=True)
    if not status_result.stdout.strip():
        print("No changes to commit.")
        return
        
    # Generate commit message based on current timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_msg = f"Auto-update: System Prompt and TTS improvements ({timestamp})"
    
    # Provide custom commit message if passed as argument
    if len(sys.argv) > 1:
        commit_msg = " ".join(sys.argv[1:])

    # Git commands
    run_command("git add .")
    run_command(f'git commit -m "{commit_msg}"')
    run_command("git push -u origin master")
    
    print("Successfully pushed to remote repository!")

if __name__ == "__main__":
    push_to_git()
