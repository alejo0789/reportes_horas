import re

with open("backend/main.py", "r", encoding="utf-8") as f:
    content = f.read()

pattern = re.compile(r'<<<<<<< HEAD\n(.*?)\n=======\n(.*?)\n>>>>>>> gitlab/desarrollo\n', re.DOTALL)
matches = pattern.findall(content)

with open("scratch/conflicts.txt", "w", encoding="utf-8") as f:
    for i, (head, other) in enumerate(matches):
        f.write(f"--- Conflict {i+1} ---\n")
        f.write("HEAD (main):\n")
        f.write(head.strip() + "\n")
        f.write("\nOTHER (gitlab/desarrollo):\n")
        f.write(other.strip() + "\n")
        f.write("="*40 + "\n\n")
