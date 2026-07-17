import re

with open('backend/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

pattern = re.compile(r'(^[ \t]+)msg \+= f"🔄 \*Actualizado DB:\* \{db_update_time_str\}\\n"', re.MULTILINE)

def repl(match):
    indent = match.group(1)
    return f'{indent}if not is_past_day:\n{indent}    msg += f"🔄 *Actualizado DB:* {{db_update_time_str}}\\n"'

new_content, count = pattern.subn(repl, content)

print(f'Reemplazadas {count} ocurrencias.')

with open('backend/main.py', 'w', encoding='utf-8') as f:
    f.write(new_content)
