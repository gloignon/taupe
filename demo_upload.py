import gradio as gr
import zipfile
import os
import tempfile
import shutil

def process_zip(zip_file):
    # Create a temporary directory to extract files
    with tempfile.TemporaryDirectory() as temp_dir:
        # Extract the zip file
        with zipfile.ZipFile(zip_file.name, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Get list of .txt files
        txt_files = [f for f in os.listdir(temp_dir) if f.endswith('.txt')]
        
        # Create a string with the list of files
        file_list = "\n".join(txt_files)
        
        return file_list

# Create Gradio interface
iface = gr.Interface(
    fn=process_zip,
    inputs=gr.File(label="Upload ZIP file"),
    outputs=gr.Textbox(label="List of .txt files"),
    title="ZIP File Processor",
    description="Upload a ZIP file containing .txt files to see the list of text files inside."
)

# Launch the app
iface.launch()