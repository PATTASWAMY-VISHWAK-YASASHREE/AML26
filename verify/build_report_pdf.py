"""Build the ER research-vs-upstream comparison report as a PDF.

Run:  .venv-pdf\\Scripts\\python.exe build_report_pdf.py
"""
from report_base import make_doc
from report_content import build

if __name__ == "__main__":
    doc = make_doc()
    F = []
    build(F)
    doc.build(F)
    print("wrote", doc.filename)
