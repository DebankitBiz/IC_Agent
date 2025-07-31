def get_kpi_html_block():
    return """
    <div style="display: flex; flex-direction: column; gap: 20px;">
        <div style="display: flex; gap: 16px;">
            <div style="flex: 1;">""" + get_metric_html("Data Freshness", "0/41", "Good", "Data is fresh across all sources.") + """</div>
            <div style="flex: 1;">""" + get_metric_html("Brand Volume", "1/12", "Issues Identified", "Indicates brand volume issues.") + """</div>
        </div>
        <div style="display: flex; gap: 16px;">
            <div style="flex: 1;">""" + get_metric_html("Data Triangulation", "0/13", "Good", "No triangulation issue detected.") + """</div>
            <div style="flex: 1;">""" + get_metric_html("Restatement Detected", "0", "Good", "No Restatements were detected.") + """</div>
        </div>
        <div style="display: flex; gap: 16px;">
            <div style="flex: 1;">""" + get_metric_html("Data Validation", "0/14", "Warnings", "Some warnings based on historical trends.") + """</div>
            <div style="flex: 1;">""" + get_metric_html("Unknown Unknowns", "2/12", "Issues Identified", "Unexpected anomalies were found.") + """</div>
        </div>
    </div>
    """
def get_metric_html(title, ratio, status, tooltip):
    colors = {
        "Good": "#4CAF50",
        "Warnings": "#FFC107",
        "Issues Identified": "#F44336"
    }
    icon = "✔" if status == "Good" else "❕"
    color = colors.get(status, "#F44336")
    
    return f"""
    <div style="border:1px solid #ccc; border-radius:10px; background:#f9f9f9; padding:10px; display:flex;">
        <div style="background:{color}; color:white; padding:10px 16px; font-size:20px; border-radius:10px 0 0 10px; display:flex; align-items:center;">{icon}</div>
        <div style="margin-left:10px;">
            <div style="font-weight:bold; font-size:16px;">{title}</div>
            <div style="font-size:13px; margin-top:4px;">{tooltip}</div>
            <div style="margin-top:6px; font-weight:bold; color:{color}; font-size:14px;">{ratio} — {status}</div>
        </div>
    </div>
    """
