
import json
import base64
from datetime import datetime
from fpdf import FPDF
from io import BytesIO
from PIL import Image
import tempfile
import os
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor
import sys

class NotebookReportPDF(FPDF):
    def __init__(self, student_name="", assignment_name=""):
        super().__init__()
        self.student_name = student_name
        self.assignment_name = assignment_name
        self.set_auto_page_break(auto=True, margin=15)
        self.add_page()
        self.set_font("Arial", "B", 16)
        self.cell(0, 10, f"Jupyter Notebook Assignment Report", ln=True, align="C")
        self.set_font("Arial", "", 12)
        self.cell(0, 10, f"Student: {student_name}", ln=True)
        self.cell(0, 10, f"Assignment: {assignment_name}", ln=True)
        self.cell(0, 10, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)
        self.ln(10)
    
    def add_cell_marker(self, cell_type, cell_number):
        self.set_font("Arial", "B", 12)
        self.set_fill_color(220, 220, 220)
        self.cell(0, 10, f"Cell {cell_number} ({cell_type})", ln=True, fill=True)
        self.ln(5)
    
    def add_code(self, code):
        self.set_font("Courier", "", 10)
        self.set_fill_color(240, 240, 240)
        self.multi_cell(0, 5, code, fill=True)
        self.ln(5)
    
    def add_markdown(self, text):
        self.set_font("Arial", "B", 12)
        self.set_fill_color(245, 245, 250)
        self.multi_cell(0, 5, text, fill=True)
        self.ln(5)
    
    def add_raw(self, text, format_type=""):
        self.set_font("Arial", "B", 10)
        self.set_fill_color(255, 245, 230)  # Light orange/peach background to distinguish raw cells
        if format_type:
            self.set_font("Arial", "I", 10)
            self.cell(0, 5, f"Format: {format_type}", ln=True)
            self.set_font("Courier", "", 10)
        self.multi_cell(0, 5, text, fill=True)
        self.ln(5)
    
    def add_output(self, output_text):
        self.set_font("Courier", "", 10)
        self.multi_cell(0, 5, output_text)
        self.ln(5)
    
    def add_image(self, img_data):
        try:
            # Create a temporary file for the image
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
                temp_filename = temp_file.name
                
                # Decode base64 image data and save to temporary file
                image_data = base64.b64decode(img_data)
                temp_file.write(image_data)
            
            # Open the image with PIL to get dimensions
            with Image.open(temp_filename) as pil_img:
                # Calculate dimensions to fit page width while maintaining aspect ratio
                page_width = self.w - 2 * self.l_margin
                img_width = min(page_width, pil_img.width)
                img_height = (pil_img.height * img_width) / pil_img.width
            
            # Add the image to the PDF using the temporary file
            x = self.l_margin + (page_width - img_width) / 2
            self.image(temp_filename, x=x, w=img_width)
            self.ln(5)
            
            # Clean up the temporary file
            os.unlink(temp_filename)
            
        except Exception as e:
            self.set_text_color(255, 0, 0)
            self.multi_cell(0, 5, f"Error displaying image: {str(e)}")
            self.set_text_color(0, 0, 0)
            self.ln(5)

def process_notebook(notebook_file, student_name, assignment_name):
    # Load the notebook into nbformat object
    if isinstance(notebook_file, str):
        with open(notebook_file, 'r', encoding='utf-8') as f:
            nb = nbformat.read(f, as_version=4)
    else:
        nb = nbformat.read(notebook_file, as_version=4)
    
    # Define notebook path
    if isinstance(notebook_file, str):
        notebook_dir = os.path.dirname(os.path.abspath(notebook_file))
    else:
        notebook_dir = os.getcwd()
    
    # Execute the notebook
    ep = ExecutePreprocessor(timeout=600, kernel_name='python3')
    
    try:
        # Add resource dictionary with proper path information
        resources = {
            'metadata': {'path': notebook_dir},
        }
        
        # Actually execute the notebook
        executed_nb, _ = ep.preprocess(nb, resources)
        print(f"Successfully executed notebook with {len(executed_nb.cells)} cells")
        
        # Use the executed notebook for PDF generation if execution was successful
        nb = executed_nb
    except Exception as e:
        print(f"Error executing notebook: {str(e)}")
        # Continue with the original notebook if execution fails
        print("Continuing with non-executed notebook for PDF generation")

    # Create PDF
    pdf = NotebookReportPDF(student_name, assignment_name)

    # Process each cell
    for i, cell in enumerate(nb.get('cells', [])):
        cell_type = cell.get('cell_type', 'unknown')
        cell_number = i + 1

        # Add cell marker
        pdf.add_cell_marker(cell_type, cell_number)

        if cell_type == 'code':
            source = ''.join(cell.get('source', []))
            pdf.add_code(source)

            outputs = cell.get('outputs', [])
            for output in outputs:
                output_type = output.get('output_type', '')

                if output_type == 'stream':
                    pdf.add_output(f"{output.get('name', 'output')}: {''.join(output.get('text', []))}")
                elif output_type in ('display_data', 'execute_result'):
                    data = output.get('data', {})
                    if 'text/plain' in data:
                        text_content = ''.join(data['text/plain']) if isinstance(data['text/plain'], list) else data['text/plain']
                        pdf.add_output(text_content)
                    if 'image/png' in data:
                        pdf.add_image(data['image/png'])
                elif output_type == 'error':
                    error_name = output.get('ename', 'Error')
                    error_value = output.get('evalue', '')
                    traceback = '\n'.join(output.get('traceback', []))
                    pdf.set_text_color(255, 0, 0)
                    pdf.add_output(f"{error_name}: {error_value}\n{traceback}")
                    pdf.set_text_color(0, 0, 0)

        elif cell_type == 'markdown':
            markdown_text = ''.join(cell.get('source', []))
            pdf.add_markdown(markdown_text)
            
        elif cell_type == 'raw':
            raw_text = ''.join(cell.get('source', []))
            # Get format information from metadata if available
            metadata = cell.get('metadata', {})
            format_type = metadata.get('format', '')
            if isinstance(format_type, list):
                format_type = ', '.join(format_type)
            pdf.add_raw(raw_text, format_type)

    return pdf
