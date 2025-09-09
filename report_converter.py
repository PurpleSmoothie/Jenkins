#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys
from html import escape

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def flatten_record(item):
    """Превращает один объект JSON в плоский словарь"""
    flat = {}
    flat["query"] = item.get("query", "")
    flat["file_path"] = item.get("file_path", "")

    analysis = item.get("analysis", {})
    flat["evaluation"] = analysis.get("evaluation", "")
    flat["severity"] = analysis.get("severity", "")
    flat["execution_time"] = analysis.get("execution_time", "")

    issues = analysis.get("issues", [])
    recs = analysis.get("recommendations", [])

    flat["issues"] = "; ".join(issues) if isinstance(issues, list) else str(issues)
    flat["recommendations"] = "; ".join(recs) if isinstance(recs, list) else str(recs)

    return flat

def evaluation_class(value):
    """Возвращает CSS-класс по значению evaluation"""
    mapping = {
        "GOOD": "row-good",
        "ACCEPTABLE": "row-acceptable",
        "NEEDS_IMPROVEMENT": "row-needs",
        "CRITICAL": "row-critical"
    }
    return mapping.get(value.upper(), "")

def generate_table_html(data):
    keys = []
    seen = set()
    for item in data:
        for k in item.keys():
            if k not in seen:
                seen.add(k)
                keys.append(k)

    html = []
    html.append('<div class="container">')
    html.append('<h1>Отчёт по SQL-запросам</h1>')
    html.append('<div class="controls">')
    html.append('<input id="filter" placeholder="Фильтр (по любому полю)..." oninput="filterTable()" />')
    html.append('</div>')

    html.append('<div class="table-wrapper">')
    html.append('<table id="jsonTable">')
    html.append('<thead><tr>')
    for k in keys:
        html.append(f"<th class='{k}'>{escape(str(k))}</th>")
    html.append('</tr></thead><tbody>')

    for item in data:
        row_class = evaluation_class(item.get("evaluation", ""))
        html.append(f'<tr class="{row_class}">')
        for k in keys:
            v = item.get(k, "")
            if isinstance(v, (dict, list)):
                text = json.dumps(v, ensure_ascii=False, indent=2)
            else:
                text = str(v)
            text = escape(text)

            if len(text) > 200 or "\n" in text:
                cell = f'<div class="cell collapsed"><pre>{text}</pre><button class="toggle">Показать ещё</button></div>'
            else:
                cell = f"<div class='cell'><pre>{text}</pre></div>"
            html.append(f"<td class='{k}'>{cell}</td>")
        html.append('</tr>')
    html.append('</tbody></table></div></div>')
    return "\n".join(html)

def generate_full_html(body_html):
    css = """
    body { font-family: Inter, Arial, sans-serif; margin: 18px; background: #f7f8fb; color:#111; }
    .row-good { background: #eaf7ea; }
    .row-acceptable { background: #eaf2f7; }
    .row-needs { background: #fff9e6; }
    .row-critical { background: #fceaea; }
    .container { background:white; border-radius:8px; padding:18px; box-shadow:0 6px 18px rgba(20,20,40,0.06); }
    h1 { margin-top:0; font-size:20px; }
    .controls { margin-bottom:8px; }
    input { padding:6px 10px; border-radius:6px; border:1px solid #ccc; min-width:220px; }
    .table-wrapper { max-height:600px; overflow-y:auto; border:1px solid #eee; border-radius:6px; }
    table { border-collapse:collapse; width:100%; font-size:14px; table-layout: fixed; }
    th, td { padding:6px 8px; border-bottom:1px solid #eee; vertical-align:top; word-wrap: break-word; }
    th { background:#fafafa; position:sticky; top:0; }
    pre { margin:0; white-space:pre-wrap; word-break:break-word; }
    .cell.collapsed pre { max-height:3.6em; overflow:hidden; }
    .cell button.toggle { margin-top:4px; font-size:12px; background:#f0f0f0; border:1px solid #ccc; border-radius:4px; padding:2px 6px; cursor:pointer; }

    /* Ширина столбцов */
    #jsonTable th.query, #jsonTable td.query { width: 23%; }
    #jsonTable th.file_path, #jsonTable td.file_path { width: 7%; text-align: center;}
    #jsonTable th.evaluation, #jsonTable td.evaluation { width: 7%; text-align: center;}
    #jsonTable th.severity, #jsonTable td.severity { width: 7%; text-align: center;}
    #jsonTable th.execution_time, #jsonTable td.execution_time { width: 7%; text-align: center;}
    #jsonTable th.issues, #jsonTable td.issues { width: 23%; }
    #jsonTable th.recommendations, #jsonTable td.recommendations { width: 26%; }
    """
    js = """
    function filterTable(){
      const q=document.getElementById('filter').value.toLowerCase();
      const rows=document.querySelectorAll('#jsonTable tbody tr');
      rows.forEach(r=>{
        r.style.display = r.innerText.toLowerCase().includes(q) ? '' : 'none';
      });
    }
    document.addEventListener('click', e=>{
      if(e.target.classList.contains('toggle')){
        const cell=e.target.closest('.cell');
        if(cell.classList.contains('collapsed')){
          cell.classList.remove('collapsed');
          e.target.textContent='Свернуть';
        } else {
          cell.classList.add('collapsed');
          e.target.textContent='Показать ещё';
        }
      }
    });
    """
    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>SQL Report</title>
<style>{css}</style>
</head>
<body>
{body_html}
<script>{js}</script>
</body>
</html>"""

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python report_converter.py input.json output.html")
        sys.exit(1)

    INPUT = sys.argv[1]
    OUTPUT = sys.argv[2]

    data = load_json(INPUT)

    if isinstance(data, list):
        flat_data = [flatten_record(item) for item in data]
    else:
        flat_data = [flatten_record(data)]

    body = generate_table_html(flat_data)
    full_html = generate_full_html(body)

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(full_html)

    print(f"✅ Отчёт сохранён в {OUTPUT}")
