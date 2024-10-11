import gradio as gr
import zipfile
import os
import tempfile
import pandas as pd
import spacy
import subprocess

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

# Global variables to store the corpus
raw_corpus = {}  # To store raw texts
lemmatized_corpus = {}  # To store lemmatized texts
initial_df = pd.DataFrame()

# Function to process the zip file, lemmatize text, get document names, and calculate word counts
def process_zip_initial(zip_file):
    global raw_corpus, lemmatized_corpus, initial_df  # To store the raw texts, lemmatized texts, and DataFrame
    raw_corpus = {}
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
                    
                    # Read the text
                    with open(file_path, 'r', encoding='utf-8') as f:
                        text = f.read()
                        word_count = len(text.split())  # Split text by spaces to count words
                        word_counts.append(word_count)

                        # Store raw text in raw_corpus
                        raw_corpus[os.path.basename(file_path)] = text.lower()

                        # Lemmatize the text and store in lemmatized_corpus
                        lemmatized_text = lemmatize_text(text.lower())
                        lemmatized_corpus[os.path.basename(file_path)] = lemmatized_text
        
        # Create a DataFrame with document names and word counts
        initial_df = pd.DataFrame({"Nom du document": txt_files, "N. mots": word_counts})
        
        return initial_df

# Function to search for keywords in the selected corpus (raw or lemmatized)
def process_zip_and_search(keywords_text, search_mode):
    global raw_corpus, lemmatized_corpus, initial_df  # Use the texts stored at corpus upload and initial DataFrame

    # Read the keywords (no lemmatization of keywords)
    keywords = [keyword.strip().lower() for keyword in keywords_text.strip().split("\n") if keyword.strip()]

    if not keywords:
        # If no keywords are provided, return the initial DataFrame (without the keyword columns)
        return initial_df

    # Select the appropriate corpus based on the search mode
    corpus = lemmatized_corpus if search_mode == "Lemmes" else raw_corpus

    # Prepare a dictionary to store the results (initialize with Document Name and empty results)
    results = {doc_name: {keyword: "" for keyword in keywords} for doc_name in corpus.keys()}

    # Search for keyword frequencies in each text file
    for doc_name, text in corpus.items():
        for keyword in keywords:
            keyword_count = text.count(keyword)  # Count occurrences of each keyword
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

    # Merge the initial DataFrame with the keyword search results
    final_df = pd.merge(initial_df, df_keywords, on="Nom du document", how="left")

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
    gr.Markdown("# Recherche simple par mots-clés avec lemmatisation")  # This line adds the title

    with gr.Row():
        # File upload and initial table with document names
        zip_file_input = gr.File(label="Téléversez votre dossier .zip contenant les fichiers texte (format .txt)")
    
    with gr.Row():
        # Textbox for entering keywords
        keywords_input = gr.Textbox(label="Entrez les mots clés (un par ligne, peuvent contenir plus d'un mot)", placeholder="mots-clés...", lines=10)
    
    with gr.Row():
        # Switch button to select between raw tokens and lemmatized search
        search_mode = gr.Radio(label="Choisissez le type de recherche", choices=["Mots", "Lemmes"], value="Lemmes")

    with gr.Row():
        # Button to trigger keyword search
        search_button = gr.Button("Recherche")
    
    # Output the final results table after the search button
    with gr.Row():
        result_table = gr.DataFrame(label="Résultats", col_count=(1, "dynamic"), interactive=False)  # Disable renaming/editing
    
    # Button to trigger the Excel export
    with gr.Row():
        export_button = gr.Button("Exporter vers Excel (.xlsx)")
        download_link = gr.File(label="Télécharger le fichier")

    # Action to display document names and lemmatized text upon ZIP upload
    zip_file_input.change(fn=process_zip_initial, inputs=zip_file_input, outputs=result_table)
    
    # Action to update the table with keywords and results based on the selected search mode
    search_button.click(fn=process_zip_and_search, inputs=[keywords_input, search_mode], outputs=result_table)
    
    # Action to export the results to Excel
    export_button.click(fn=export_to_excel, inputs=result_table, outputs=download_link)

# Launch the app
demo.launch()