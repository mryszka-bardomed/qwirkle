import csv
import io

from flask import Response


def _safe_cell(value):
    # Zapobiega wstrzykiwaniu formuł w Excelu (np. imię zaczynające się od "=").
    text = "" if value is None else str(value)
    if text and text[0] in "=+-@\t\r":
        return "'" + text
    return text


def csv_response(header, rows, filename):
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";")
    writer.writerow(header)
    for row in rows:
        writer.writerow([_safe_cell(v) for v in row])
    # BOM, żeby Excel poprawnie pokazał polskie znaki.
    return Response(
        "﻿" + buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
