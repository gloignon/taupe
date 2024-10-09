import gradio as gr
import zipfile
import os
import tempfile
import pandas as pd
import spacy
import subprocess
from html import escape

# Ensure the spaCy French model is downloaded
try:
    nlp = spacy.load("fr_core_news_sm")
except OSError:
    print("Downloading spaCy 'fr_core_news_sm' model...")
    subprocess.run(["python", "-m", "spacy", "download", "fr_core_news_sm"])
    nlp = spacy.load("fr_core_news_sm")

# Function to lemmatize text using spaCy
def lemmatize_text(text):
    doc = nlp(text)
    return " ".join([token.lemma_ for token in doc])

# Global variable to store the lemmatized texts
lemmatized_corpus = {}
keywords = []

# Function to process the zip file, lemmatize text, get document names, and calculate word counts
def process_zip_initial(zip_file):
    global lemmatized_corpus  # To store the lemmatized texts
    lemmatized_corpus = {}  # Reset the corpus on new upload

    # Create a temporary directory to extract files
    with tempfile.TemporaryDirectory() as temp_dir:
        # Extract the zip file
        with zipfile.ZipFile(zip_file.name, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Recursively get list of all .txt files in all directories and lemmatize the text
        txt_files = []
        word_counts = []
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.endswith('.txt'):
                    file_path = os.path.join(root, file)
                    txt_files.append(os.path.basename(file_path))  # Only the file name
                    
                    # Read and lemmatize text
                    with open(file_path, 'r', encoding='utf-8') as f:
                        text = f.read()
                        word_count = len(text.split())  # Split text by spaces to count words
                        word_counts.append(word_count)

                        # Lemmatize the text and store in lemmatized_corpus
                        lemmatized_text = lemmatize_text(text.lower())
                        lemmatized_corpus[os.path.basename(file_path)] = lemmatized_text
        
        # Create a DataFrame with document names and word counts
        df = pd.DataFrame({"Nom du document": txt_files, "N. mots": word_counts})
        
        return df

# Function to search for keywords in the lemmatized corpus (without lemmatizing keywords)
def process_zip_and_search(keywords_text):
    global lemmatized_corpus, keywords  # Use the lemmatized texts stored at corpus upload
    keywords = [keyword.strip().lower() for keyword in keywords_text.strip().split("\n") if keyword.strip()]
    
    # Prepare a dictionary to store the results (initialize with Document Name and empty results)
    results = {doc_name: {keyword: "" for keyword in keywords} for doc_name in lemmatized_corpus.keys()}
    
    # Search for keyword frequencies in each lemmatized text file
    for doc_name, lemmatized_text in lemmatized_corpus.items():
        for keyword in keywords:
            keyword_count = lemmatized_text.count(keyword)  # Count occurrences of the keyword in lemmatized text
            if keyword_count > 0:
                results[doc_name][keyword] = keyword_count
    
    # Convert the results dictionary to a DataFrame
    df_keywords = pd.DataFrame(results).T  # Transpose to have files as rows and keywords as columns
    
    # Reset index to make the document names a column
    df_keywords.reset_index(inplace=True)
    
    # Rename the first column to 'Nom du document'
    df_keywords.rename(columns={"index": "Nom du document"}, inplace=True)
    
    # Replace 0 frequencies with empty strings
    df_keywords.replace(0, "", inplace=True)
    
    return df_keywords

# Function to display the lemmatized text with highlighted keywords
def display_lemmatized_text(doc_name):
    global lemmatized_corpus, keywords
    lemmatized_text = lemmatized_corpus.get(doc_name, "")
    
    # Escape HTML characters for safe display
    lemmatized_text = escape(lemmatized_text)
    
    # Highlight keywords by wrapping them in a <mark> tag
    for keyword in keywords:
        lemmatized_text = lemmatized_text.replace(keyword, f"<mark>{keyword}</mark>")
    
    return lemmatized_text

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
    gr.Markdown("# Recherche simple par mots-clés avec lemmatisation")  # This line adds the title

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
        result_table = gr.DataFrame(label="Résultats", col_count=(1, "dynamic"), interactive=False, max_height=600)  # Disable renaming/editing

    # Create an HTML component to display the lemmatized text with highlighted keywords
    lemmatized_display = gr.HTML()

    # Button to trigger the Excel export
    with gr.Row():
        export_button = gr.Button("Exporter vers Excel (.xlsx)")
        download_link = gr.File(label="Télécharger le fichier")

    # Action to display document names and lemmatized text upon ZIP upload
    zip_file_input.change(fn=process_zip_initial, inputs=zip_file_input, outputs=result_table)
    
    # Action to update the table with keywords and results
    search_button.click(fn=process_zip_and_search, inputs=keywords_input, outputs=result_table)
    
    # Function to update the lemmatized text display with highlighted keywords
    def open_lemmatized_text(doc_name):
        highlighted_text = display_lemmatized_text(doc_name)
        lemmatized_display.update(highlighted_text)

    # Create dynamic buttons for each document name in the result table to trigger the text display
    result_table.select(fn=open_lemmatized_text, inputs="index", outputs=lemmatized_display)

    # Action to export the results to Excel
    export_button.click(fn=export_to_excel, inputs=result_table, outputs=download_link)

# Launch the app
demo.launch()
