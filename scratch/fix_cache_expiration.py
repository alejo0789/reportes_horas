import re

with open("backend/main.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace the expiration logic in get_ventas
old_logic = """        # Auto-expire yesterday's cache if it was created BEFORE today (e.g., missing final closing data at 20:00)
        # This ensures the first request on the next day fetches the definitive Oracle data.
        if is_yesterday:
            try:
                dt_updated = datetime.fromisoformat(last_updated)
                if dt_updated.date() < date.today():
                    cache_valid = False
            except Exception:
                pass"""

new_logic = """        # Auto-expire yesterday's cache if it was created BEFORE today (e.g., missing final closing data at 20:00)
        # This ensures the first request on the next day fetches the definitive Oracle data.
        # UPDATE: User requested to ALWAYS use SQLite for yesterday to avoid long Oracle query times.
        # if is_yesterday:
        #     try:
        #         dt_updated = datetime.fromisoformat(last_updated)
        #         if dt_updated.date() < date.today():
        #             cache_valid = False
        #     except Exception:
        #         pass"""

if old_logic in content:
    content = content.replace(old_logic, new_logic)
    with open("backend/main.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Updated backend/main.py successfully.")
else:
    print("Old logic not found!")
