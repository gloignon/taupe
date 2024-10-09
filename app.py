import gradio as gr
import zipfile
import os
import tempfile
import pandas as pd

# Function to process the zip file, get document names, and calculate word counts (without keywords initially)
def process_zip_initial(zip_file):
    # Create a temporary directory to extract files
    with tempfile.TemporaryDirectory() as temp_dir:
        # Extract the zip file
        with zipfile.ZipFile(zip_file.name, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Recursively get list of all .txt files in all directories and calculate word count
        txt_files = []
        word_counts = []
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.endswith('.txt'):
                    file_path = os.path.join(root, file)
                    txt_files.append(os.path.basename(file_path))  # Only the file name
                    
                    # Calculate word count
                    with open(file_path, 'r', encoding='utf-8') as f:
                        text = f.read()
                        word_count = len(text.split())  # Split text by spaces to count words
                        word_counts.append(word_count)
        
        # Create a DataFrame with document names and word counts
        df = pd.DataFrame({"Nom du document": txt_files, "N. mots": word_counts})
        
        return df

# Function to process the zip file and search for keywords (while preserving Word Count)
def process_zip_and_search(zip_file, keywords_text):
    # Create a temporary directory to extract files
    with tempfile.TemporaryDirectory() as temp_dir:
        # Extract the zip file
        with zipfile.ZipFile(zip_file.name, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Recursively get list of all .txt files in all directories
        txt_files = []
        word_counts = []
        base_names = []
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.endswith('.txt'):
                    file_path = os.path.join(root, file)  # Full path to the file
                    txt_files.append(file_path)  # Store the full path
                    base_names.append(os.path.basename(file_path))  # Store just the base name for display
                    
                    # Calculate word count
                    with open(file_path, 'r', encoding='utf-8') as f:
                        text = f.read()
                        word_count = len(text.split())  # Split text by spaces to count words
                        word_counts.append(word_count)
        
        # Read keywords (split by line, supports multiword expressions)
        keywords = [keyword.strip().lower() for keyword in keywords_text.strip().split("\n") if keyword.strip()]  # Convert keywords to lowercase
        
        # Prepare a dictionary to store the results (initialize with Document Name and Word Count)
        results = {base_name: {keyword: "" for keyword in keywords} for base_name in base_names}
        
        # Search for keyword frequencies in each text file (support multiword)
        for i, txt_file in enumerate(txt_files):
            with open(txt_file, 'r', encoding='utf-8') as file:
                text = file.read().lower()  # Convert to lowercase for case-insensitive search
                
                # Count occurrences of each keyword (multiword expressions supported)
                for keyword in keywords:
                    keyword_count = text.count(keyword.lower())  # Use count() to get occurrences (both text and keywords are lowercased)
                    if keyword_count > 0:
                        results[base_names[i]][keyword] = keyword_count
        
        # Convert the results dictionary to a DataFrame
        df_keywords = pd.DataFrame(results).T  # Transpose to have files as rows and keywords as columns
        
        # Reset index to make the document names a column
        df_keywords.reset_index(inplace=True)
        
        # Rename the first column to 'Document Name'
        df_keywords.rename(columns={"index": "Nom du document"}, inplace=True)
        
        # Replace 0 frequencies with empty strings
        df_keywords.replace(0, "", inplace=True)
        
        # Create a DataFrame with document names and word counts
        df_word_counts = pd.DataFrame({"Nom du document": base_names, "N. mots": word_counts})
        
        # Merge the Word Count DataFrame with the Keywords DataFrame on "Document Name"
        final_df = pd.merge(df_word_counts, df_keywords, on="Nom du document")
        
        return final_df



# Function to export the DataFrame to Excel
def export_to_excel(df):
    # Create a temporary directory for storing the Excel file
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        excel_path = tmp.name
        # Save the DataFrame to Excel
        df.to_excel(excel_path, index=False)
    return excel_path

# Create Gradio interface with one results table and export functionality
with gr.Blocks() as demo:
    gr.Markdown("# Recherche simple par mots-clés")  # This line adds the title

    with gr.Row():
        # File upload and initial table with document names
        zip_file_input = gr.File(label="Téléversez votre dossier .zip contenant les fichiers texte (format .txt)")
    
    with gr.Row():
        # Textbox for entering keywords
        keywords_input = gr.Textbox(label="Entrez les mots clés (un par ligne, peuvent contenir plus d'un mot)", placeholder="mots-clés...", lines=10)
    
    with gr.Row():
        # Button to trigger keyword search
        search_button = gr.Button("Recherche")
    
    # Output the final results table after the search button
    with gr.Row():
        result_table = gr.DataFrame(label="Résultats", col_count = (1, "dynamic"), interactive=False, max_height=600)  # Disable renaming/editing
    
    # Button to trigger the Excel export
    with gr.Row():
        export_button = gr.Button("Exporter vers Excel (.xlsx)")
        download_link = gr.File(label="Télécharger le fichier")

    # Action to display document names upon ZIP upload
    zip_file_input.change(fn=process_zip_initial, inputs=zip_file_input, outputs=result_table)
    
    # Action to update the table with keywords and results
    search_button.click(fn=process_zip_and_search, inputs=[zip_file_input, keywords_input], outputs=result_table)
    
    # Action to export the results to Excel
    export_button.click(fn=export_to_excel, inputs=result_table, outputs=download_link)

# Launch the app
demo.launch()