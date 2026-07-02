import subprocess

def kill_port_8032():
    try:
        output = subprocess.check_output("netstat -ano", shell=True).decode('cp1252', errors='replace')
        pids = set()
        for line in output.splitlines():
            if ":8032" in line and "LISTENING" in line:
                parts = line.split()
                if len(parts) >= 5:
                    pids.add(parts[-1])
        
        if not pids:
            print("No process found listening on port 8032")
            return
            
        for pid in pids:
            print(f"Killing process {pid} on port 8032...")
            subprocess.call(f"taskkill /F /PID {pid}", shell=True)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    kill_port_8032()
