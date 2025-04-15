from flask import Flask, request, render_template, send_file
from io import BytesIO
from report_generator import process_notebook

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'notebook' not in request.files:
            return render_template('upload.html', error='No file part')
        
        notebook_file = request.files['notebook']
        if notebook_file.filename == '':
            return render_template('upload.html', error='No selected file')
        
        if notebook_file and notebook_file.filename.endswith('.ipynb'):
            student_name = request.form.get('student_name', 'Unknown Student')
            assignment_name = request.form.get('assignment_name', 'Unknown Assignment')
            
            try:
                # Process notebook
                pdf = process_notebook(notebook_file, student_name, assignment_name)
                
                # Save to BytesIO
                pdf_output = BytesIO()
                pdf_bytes = pdf.output(dest='S').encode('latin1')  # Get PDF as bytes
                pdf_output.write(pdf_bytes)  # Write bytes to BytesIO
                pdf_output.seek(0)  # Reset pointer to beginning
                
                # Return the PDF file
                return send_file(
                    pdf_output,
                    as_attachment=True,
                    download_name=f"{student_name}_{assignment_name}_report.pdf",
                    mimetype='application/pdf'
                )
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                return render_template('upload.html', error=f'Error processing notebook: {str(e)}\n{error_details}')
        
        return render_template('upload.html', error='Invalid file format. Please upload .ipynb files only')
    
    return render_template('upload.html')

if __name__ == '__main__':
    app.run(debug=True)
