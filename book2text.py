import os
import re
import csv
import sys
import subprocess
import argparse  # Import argparse for command-line parsing
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader
import ebooklib
from ebooklib import epub
import shutil

def epub_to_text(epub_path):
    book = epub.read_epub(epub_path)
    text = []
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            soup = BeautifulSoup(item.get_content(), 'html.parser')
            text.append(soup.get_text())
    return '\n'.join(text)

def html_to_text(html_path):
    with open(html_path, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'html.parser')
        return soup.get_text()

def pdf_to_text(pdf_path):
    reader = PdfReader(pdf_path)
    text = []
    for page in reader.pages:
        text.append(page.extract_text())
    return '\n'.join(text)

def natural_sort_key(s):
    """
    This function constructs a tuple of either integers (if the pattern matches digits)
    or the original elements (if not). This tuple can be used as a key for sorting.
    """
    return [int(text) if text.isdigit() else text.lower() for text in re.split('(\d+)', s)]

def process_files(directory, file_type):
    data = []
    files = sorted(os.listdir(directory), key=natural_sort_key)
    for filename in files:
        filepath = os.path.join(directory, filename)
        if file_type == 'html' and filename.endswith('.html'):
            text = html_to_text(filepath)
            title = os.path.splitext(filename)[0]
        elif file_type == 'epub':
            text = epub_to_text(filepath)
            book = epub.read_epub(filepath)
            title = book.get_metadata('DC', 'title')[0][0]
        elif file_type == 'pdf' and filename.endswith('.pdf'):
            text = pdf_to_text(filepath)
            title = os.path.splitext(filename)[0]
        else:
            continue

        text = text.replace('\t', ' ').strip().replace('\n', '\\n')
        char_count = len(text)
        if file_type == 'epub':
            book = epub.read_epub(filepath)
            title = book.get_metadata('DC', 'title')[0][0]
        else:
            title = os.path.splitext(filename)[0]
        data.append([filename, title, text, char_count])
    return data

def save_to_csv(data, output_file):
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Filename', 'Title', 'Text', 'Character Count'])
        writer.writerows(data)

def run_chunking_script(csv_file):
    # Construct the command to run the second script
    command = f"python chunking.py \"{csv_file}\""
    # Execute the command
    subprocess.run(command, shell=True, check=True)

def main(input_file, output_dir, output_csv):
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    file_type = os.path.splitext(input_file)[1][1:]
    if file_type == 'epub':
        result = subprocess.run(f"python epubsplit.py --split-by-section \"{input_file}\" --output-dir \"{output_dir}\"",
                                shell=True, text=True, stderr=subprocess.PIPE)
        if result.returncode != 0:
            print("Error detected while splitting EPUB. Attempting alternative method with epubunz.py.")
            subprocess.run(f"python epubunz.py \"{input_file}\"", shell=True)
            file_type = 'html'
    elif file_type == 'pdf':
        result = os.system(f"python3 pdf_splitter.py \"{input_file}\"")
    else:
        print("Unsupported file type. Please provide an EPUB or PDF file.")
        sys.exit(1)

    file_data = process_files(output_dir, file_type)
    save_to_csv(file_data, output_csv)
    print(f"CSV file created: {output_csv}")
    run_chunking_script(output_csv)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Convert books to text and process them.")
    parser.add_argument('input_file', type=str, help='Input file path (EPUB or PDF)')
    args = parser.parse_args()

    input_file = args.input_file
    file_name = os.path.splitext(os.path.basename(input_file))[0].replace(" ", "-")
    file_name = re.sub(r'[^\w\-_]', '', file_name)
    output_dir = f"out/{file_name}/"
    output_csv = f"out/{file_name}.csv"
    main(input_file, output_dir, output_csv)
