import re

with open("backend/main.py", "r", encoding="utf-8") as f:
    content = f.read()

# Fix recursive call 1
old_call_1 = """                result = get_whatsapp_query(
                    phone=None,
                    report_type="products",
                    selected_product=None,
                    override_promoter_name=None,
                    override_coordinator_name=selected_coord_name,
                    
                )"""
new_call_1 = """                result = get_whatsapp_query(
                    phone=None,
                    report_type="products",
                    selected_product=None,
                    override_promoter_name=None,
                    override_coordinator_name=selected_coord_name,
                    ref_date=ref_date,
                )"""
content = content.replace(old_call_1, new_call_1)

# Fix recursive call 2
old_call_2 = """                result = get_whatsapp_query(
                    phone=None,
                    report_type="offices",
                    selected_product=None,
                    override_promoter_name=selected_promoter_name,
                    override_coordinator_name=None,
                    
                )"""
new_call_2 = """                result = get_whatsapp_query(
                    phone=None,
                    report_type="offices",
                    selected_product=None,
                    override_promoter_name=selected_promoter_name,
                    override_coordinator_name=None,
                    ref_date=ref_date,
                )"""
content = content.replace(old_call_2, new_call_2)

with open("backend/main.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Fixed recursive calls in backend/main.py")
