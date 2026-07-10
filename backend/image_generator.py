import os
import time
from html2image import Html2Image

def generate_compliance_image(date_str: str) -> str:
    """
    Generates a PNG image of the compliance table for a given date.
    Uses html2image to screenshot the frontend compliance.html page.
    Returns the absolute path to the generated image.
    """
    # Assuming FastAPI runs on 8000 locally
    url = f"http://localhost:8000/compliance.html?date={date_str}"
    
    output_path = os.path.join(os.getcwd(), "uploads", f"resumen_admin_{date_str}.png")
    
    # We use html2image
    hti = Html2Image()
    # Optional: Configure browser flags if needed
    # hti.browser.flags = ['--no-sandbox', '--disable-gpu']
    
    # Set the viewport size (adjust as needed for the table)
    hti.size = (1150, 750) 
    
    print(f"Generando imagen de {url}...")
    
    # Wait a bit if needed, but html2image loads the page. 
    # To ensure data is fetched from the API, we might need a small delay.
    hti.screenshot(url=url, save_as=f"resumen_admin_{date_str}.png")
    
    # html2image saves in current directory by default if we just give filename, 
    # so we move it to uploads folder
    if os.path.exists(f"resumen_admin_{date_str}.png"):
        os.rename(f"resumen_admin_{date_str}.png", output_path)
    
    return output_path

if __name__ == "__main__":
    # Test script
    import sys
    d = sys.argv[1] if len(sys.argv) > 1 else "2026-07-08"
    p = generate_compliance_image(d)
    print("Imagen guardada en:", p)
