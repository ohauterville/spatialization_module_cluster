# from nbconvert import PDFExporter
# from nbconvert import NotebookExporter
# import nbformat
# import os

# current_dir = os.getcwd()
# parent_dir = os.path.dirname(current_dir)

# input = os.path.join(parent_dir,"visualizer.ipynb")
# output_name = os.path.join(parent_dir, "outputs/output_")
# # Read the notebook
# with open(input, "r") as f:
#     notebook_content = nbformat.read(f, as_version=4)

# # Convert to PDF
# pdf_exporter = PDFExporter()
# (pdf_body, resources) = pdf_exporter.from_notebook_node(notebook_content)

# ###
# from datetime import datetime

# # Get the current date
# current_date = datetime.now()

# # Format the date as ddmmyyyy
# formatted_date = current_date.strftime("%d%m%Y")

# # Save the PDF
# with open(output_name + formatted_date + ".pdf", "wb") as f:
#     f.write(pdf_body)
