import subprocess

try:
    output = subprocess.check_output("netstat -ano", shell=True).decode('cp1252', errors='replace')
    found = False
    for line in output.splitlines():
        if ":8032" in line and "LISTENING" in line:
            print("Server is LISTENING:", line.strip())
            found = True
    if not found:
        print("No process is listening on port 8032.")
except Exception as e:
    print(f"Error checking ports: {e}")
