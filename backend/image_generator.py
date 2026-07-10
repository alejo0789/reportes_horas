import os
import json
from html2image import Html2Image
from backend.main import get_compliance_data

def generate_compliance_image(date_str: str) -> str:
    """
    Generates a PNG image of the compliance table for a given date.
    Injects data directly into the HTML to avoid async fetch issues with html2image.
    """
    output_path = os.path.join(os.getcwd(), "uploads", f"resumen_admin_{date_str}.png")
    
    # 1. Fetch data directly from backend logic
    data = get_compliance_data(date_str)
    
    # 2. Read HTML and JS files
    html_path = os.path.join(os.getcwd(), "frontend", "compliance.html")
    js_path = os.path.join(os.getcwd(), "frontend", "compliance.js")
    
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
        
    with open(js_path, "r", encoding="utf-8") as f:
        js_content = f.read()
        
    # 3. Inject data and scripts into HTML
    script_injection = f"""
    <script>
        window.PRELOADED_DATA = {json.dumps(data)};
        {js_content}
    </script>
    """
    # Remove the external script tag and inject inline script
    html_content = html_content.replace('<script src="compliance.js"></script>', script_injection)
    
    # 4. Generate image
    hti = Html2Image()
    hti.size = (1150, 750) 
    
    print(f"Generando imagen estática para {date_str}...")
    
    hti.screenshot(html_str=html_content, save_as=f"resumen_admin_{date_str}.png")
    
    if os.path.exists(f"resumen_admin_{date_str}.png"):
        os.replace(f"resumen_admin_{date_str}.png", output_path)
    
    return output_path

if __name__ == "__main__":
    # Test script
    import sys
    d = sys.argv[1] if len(sys.argv) > 1 else "2026-07-08"
    p = generate_compliance_image(d)
    print("Imagen guardada en:", p)
