import os, json
from backend.main import get_compliance_data

data = get_compliance_data('2026-07-09')

with open('frontend/compliance.html', 'r', encoding='utf-8') as f:
    html_content = f.read()

with open('frontend/compliance.js', 'r', encoding='utf-8') as f:
    js_content = f.read()

script_injection = f'''
<script>
    window.PRELOADED_DATA = {json.dumps(data)};
    {js_content}
</script>
'''

html_content = html_content.replace('<script src="compliance.js"></script>', script_injection)

with open('debug.html', 'w', encoding='utf-8') as f:
    f.write(html_content)
print('debug.html generated')
