from datetime import datetime
import base64

def generate_memory_book_html(memories, patient_name):
    """
    Generate an HTML memory book that can be printed or saved as PDF.
    """
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{patient_name}'s Memory Book</title>
        <style>
            body {{
                font-family: 'Georgia', serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 40px;
                background: #f5f5f5;
            }}
            .cover {{
                text-align: center;
                padding: 100px 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border-radius: 10px;
                margin-bottom: 40px;
            }}
            .cover h1 {{
                font-size: 48px;
                margin: 0;
            }}
            .memory {{
                background: white;
                padding: 30px;
                margin-bottom: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                page-break-inside: avoid;
            }}
            .memory-date {{
                color: #666;
                font-size: 14px;
                margin-bottom: 10px;
            }}
            .memory-image {{
                max-width: 100%;
                border-radius: 5px;
                margin: 20px 0;
            }}
            .memory-text {{
                line-height: 1.8;
                font-size: 16px;
            }}
            .person-tag {{
                display: inline-block;
                background: #e3f2fd;
                padding: 5px 15px;
                border-radius: 20px;
                margin: 5px;
                font-size: 14px;
            }}
            @media print {{
                body {{ background: white; }}
                .memory {{ page-break-inside: avoid; }}
            }}
        </style>
    </head>
    <body>
        <div class="cover">
            <h1>{patient_name}'s</h1>
            <h2>Memory Book</h2>
            <p>Created on {datetime.now().strftime("%B %d, %Y")}</p>
        </div>
    """
    
    for mem in memories:
        timestamp = mem.get("timestamp", 0)
        date_str = datetime.fromtimestamp(timestamp).strftime("%B %d, %Y at %I:%M %p")
        
        html += f'<div class="memory">'
        html += f'<div class="memory-date">{date_str}</div>'
        
        # Person tags
        if mem.get("person_tags"):
            html += '<div>'
            for person in mem["person_tags"].split(","):
                html += f'<span class="person-tag">👤 {person.strip()}</span>'
            html += '</div>'
        
        # Image
        if mem.get("source_image_base64"):
            html += f'<img class="memory-image" src="data:image/jpeg;base64,{mem["source_image_base64"]}" />'
        
        # Caption/Content
        if mem.get("caption"):
            html += f'<div class="memory-text">{mem["caption"]}</div>'
        elif mem.get("transcript"):
            html += f'<div class="memory-text">🎤 "{mem["transcript"]}"</div>'
        elif mem.get("content"):
            html += f'<div class="memory-text">📝 {mem["content"]}</div>'
        
        html += '</div>'
    
    html += """
    </body>
    </html>
    """
    
    return html
