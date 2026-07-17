import re

with open("backend/main.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Remove the entire sqlite3 tracking block from get_whatsapp_query
start_str = "    # Track first message of the day and limit the \"yesterday\" session\n"
end_str = "    # 2. Encontrar oficinas asignadas en la distribución comercial\n"
if start_str in content and end_str in content:
    start_idx = content.find(start_str)
    end_idx = content.find(end_str)
    content = content[:start_idx] + content[end_idx:]

# 2. Remove date_filter defaults
content = content.replace('    if not isinstance(date_filter, str):\n        date_filter = "today"\n', "")

# 3. Replace remaining date_filter checks with is_past_day
content = content.replace('date_filter == "yesterday"', "is_past_day")
content = content.replace('date_filter != "yesterday"', "not is_past_day")
content = content.replace('date_filter=date_filter', "")

# 4. Fix drill-down in _process_whatsapp_message
# Find administrator block
admin_block_old = '''        elif button_id == "view_coordinators_summary" or "coordinador" in user_msg_lower:
            report_type = "coordinators"

        query_result = get_whatsapp_query(sender_phone, report_type=report_type)'''
admin_block_new = '''        elif button_id == "view_coordinators_summary" or "coordinador" in user_msg_lower:
            report_type = "coordinators"
        elif user_msg_text.isdigit():
            report_type = "administrator_coordinator_detail"
            query_result = get_whatsapp_query(sender_phone, report_type=report_type, selected_product=user_msg_text, ref_date=ref_date_param)

        if query_result is None:
            query_result = get_whatsapp_query(sender_phone, report_type=report_type, ref_date=ref_date_param)'''
content = content.replace(admin_block_old, admin_block_new)

# Find coordinator block
coor_block_old = '''        elif button_id == "view_promoter_summary" or "promotor" in user_msg_lower:
            report_type = "prompt_promoter"

        query_result = get_whatsapp_query(sender_phone, report_type=report_type)'''
coor_block_new = '''        elif button_id == "view_promoter_summary" or "promotor" in user_msg_lower:
            report_type = "prompt_promoter"
        elif user_msg_text.isdigit():
            report_type = "coordinator_promoter_detail"
            query_result = get_whatsapp_query(sender_phone, report_type=report_type, selected_product=user_msg_text, ref_date=ref_date_param)

        if query_result is None:
            query_result = get_whatsapp_query(sender_phone, report_type=report_type, ref_date=ref_date_param)'''
content = content.replace(coor_block_old, coor_block_new)

# Add ref_date_param to promoter block query calls
content = content.replace('''query_result = get_whatsapp_query(sender_phone, report_type=report_type, selected_product=selected_product)''', 
'''query_result = get_whatsapp_query(sender_phone, report_type=report_type, selected_product=selected_product, ref_date=ref_date_param)''')

# 5. Fix yesterday standalone sending logic in _process_whatsapp_message
yesterday_logic_old = '''    # Primer contacto del día: además del reporte de hoy, se adjunta un
    # mensaje independiente con el recopilatorio de ayer.
    first_session = is_first_session_of_day(sender_phone)
    yesterday_date = (date.today() - timedelta(days=1)).isoformat() if first_session else None'''
yesterday_logic_new = '''    # Primer contacto del día: usamos la ventana de tiempo para ofrecer el reporte
    # del día anterior automáticamente a cualquier consulta en esos primeros minutos.
    first_session = is_first_session_of_day(sender_phone)
    ref_date_param = (date.today() - timedelta(days=1)).isoformat() if first_session else None'''
content = content.replace(yesterday_logic_old, yesterday_logic_new)

# Remove the standalone yesterday request
standalone_old = '''    # 0. Primer contacto del día: enviar primero el recopilatorio de AYER como
    #    mensaje independiente (reporte general del día anterior).
    if first_session and yesterday_date:
        try:
            yesterday_result = get_whatsapp_query(sender_phone, report_type="products", ref_date=yesterday_date)
            yesterday_text = yesterday_result.get("text")
            if yesterday_text and dry_run:
                dry_messages.append({"kind": "text", "label": "recopilatorio_ayer", "text": yesterday_text})
            elif yesterday_text:
                y_payload = {
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": sender_phone,
                    "type": "text",
                    "text": {"body": yesterday_text}
                }
                y_req = urllib.request.Request(
                    url,
                    data=json.dumps(y_payload).encode("utf-8"),
                    headers={
                        "Authorization": f"Bearer {whatsapp_token}",
                        "Content-Type": "application/json"
                    },
                    method="POST"
                )
                with urllib.request.urlopen(y_req) as y_resp:
                    logger.info(f"WhatsApp yesterday recap sent to {sender_phone}: {y_resp.read().decode('utf-8')}")
        except Exception as e:
            logger.error(f"Error sending yesterday recap to {sender_phone}: {e}")

    # 1. Send the main report as a standard text message (limit 4096 characters, no error 400)'''
standalone_new = '''    # 1. Send the main report as a standard text message (limit 4096 characters, no error 400)'''
content = content.replace(standalone_old, standalone_new)

# Write back
with open("backend/main.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated backend/main.py")
