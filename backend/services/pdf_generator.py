import os
import datetime
from fpdf import FPDF

class ArchiShieldPDF(FPDF):
    def header(self):
        # Header banner
        self.set_fill_color(13, 31, 61)
        self.rect(0, 0, 210, 32, "F")
        self.set_text_color(255, 255, 255)
        self.set_font("Arial", "B", 16)
        self.cell(0, 10, "ArchiShield BIM Quality & Compliance Audit", ln=True, align="C")
        self.set_font("Arial", size=9)
        self.cell(0, 4, "IFC Semantic Data-Loss Analyser Report", ln=True, align="C")
        self.cell(0, 4, f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align="C")
        self.ln(12)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}} | Confidential — ArchiShield Audit Report", align="C")

def safe_str(val):
    return str(val).encode("latin-1", errors="replace").decode("latin-1")

def generate_pdf_report(analysis: dict, context: dict, file_path: str):
    pdf = ArchiShieldPDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_text_color(0, 0, 0)

    # Section 1: User Context
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "1) Audit Information & Metadata", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 6, safe_str(f"User Name  : {context.get('name', 'N/A')}"), ln=True)
    pdf.cell(0, 6, safe_str(f"User Role  : {context.get('role', 'N/A')}"), ln=True)
    pdf.cell(0, 6, safe_str(f"Domain     : {context.get('domain', 'N/A')} | Purpose: {context.get('purpose', 'N/A')}"), ln=True)
    pdf.cell(0, 6, safe_str(f"Export Tool: {analysis.get('export_source', {}).get('tool', 'Unknown')} ({analysis.get('export_source', {}).get('version', 'Unknown')})"), ln=True)
    pdf.ln(4)

    # Section 2: Summary Metrics
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "2) Model Summary Metrics", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 6, safe_str(f"Total Products     : {analysis.get('total_elements', 0)}"), ln=True)
    pdf.cell(0, 6, safe_str(f"Semantic Elements  : {analysis.get('semantic_elements', 0)} ({analysis.get('semantic_pct', 0):.1f}%)"), ln=True)
    pdf.cell(0, 6, safe_str(f"Proxy Elements     : {analysis.get('proxy_elements', 0)} ({analysis.get('proxy_pct', 0):.1f}%)"), ln=True)
    pdf.cell(0, 6, safe_str(f"Model Quality Score: {analysis.get('quality_score', 0)}/100 ({analysis.get('quality_grade', '—')})"), ln=True)
    pdf.cell(0, 6, safe_str(f"Severity Level     : {analysis.get('severity', '—')}"), ln=True)
    pdf.ln(4)

    # Section 3: 5-Level Data Loss Analysis
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "3) 5-Level Data Loss Breakdown", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 6, safe_str(f"L1 Semantic Loss (Weight 30%): {analysis.get('type_loss_pct', 0):.1f}% | {analysis.get('type_loss_count', 0)} elements"), ln=True)
    pdf.cell(0, 6, safe_str(f"L2 Property Loss (Weight 20%): {analysis.get('prop_loss_pct', 0):.1f}% | {analysis.get('prop_loss_count', 0)} elements"), ln=True)
    pdf.cell(0, 6, safe_str(f"L3 Quantity Loss (Weight 15%): {analysis.get('qty_loss_pct', 0):.1f}% | {analysis.get('qty_loss_count', 0)} elements"), ln=True)
    pdf.cell(0, 6, safe_str(f"L4 Relationship Loss (W. 25%): {analysis.get('rel_loss_pct', 0):.1f}% | {analysis.get('rel_loss_count', 0)} elements"), ln=True)
    pdf.cell(0, 6, safe_str(f"L5 Geometry Loss (Weight 10%): {analysis.get('geo_loss_pct', 0):.1f}% | {analysis.get('geo_loss_count', 0)} elements"), ln=True)
    pdf.cell(0, 6, safe_str(f"Model Integrity Score        : {analysis.get('data_integrity', 0)}/100 (Total Loss: {analysis.get('data_loss_score', 0)}%)"), ln=True)
    pdf.ln(4)

    # Section 4: Storey-wise Breakdown
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "4) Storey Quality Summary", ln=True)
    pdf.set_font("Arial", size=9)
    for storey_name, sdata in analysis.get("storey_data", {}).items():
        elev_str = f"{sdata['elevation']}m" if sdata['elevation'] != -9999 else "N/A"
        pdf.cell(0, 5, safe_str(f"  Floor: {storey_name:28} | Elevation: {elev_str:6} | Elements: {sdata['total']:4} | Score: {sdata['score']:5}/100 ({sdata['grade']})"), ln=True)
    pdf.ln(4)

    # Section 5: NBC Compliance
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "5) NBC 2016 Compliance Audit Summary", ln=True)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 6, safe_str(f"Overall NBC Compliance: {analysis.get('nbc_overall_score', 0)}%"), ln=True)
    pdf.set_font("Arial", size=9)
    for r in analysis.get("nbc_results", []):
        status_lbl = "PASS" if r["status"] == "Pass" else "FAIL"
        pdf.cell(0, 5, safe_str(f"  [{status_lbl:4}] {r['section']:32} | {r['check'][:38]:38} | Score: {r['score']}% ({r['severity']})"), ln=True)

    pdf.output(file_path)
