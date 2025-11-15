import os
import ast
import requests
from bs4 import BeautifulSoup

def scrape_paragraphs(url):
    # Fetch the webpage content
    response = requests.get(url)
    
    # Check if the request was successful
    if response.status_code == 200:
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all <p> tags
        paragraphs = soup.find_all('p')
        
        # Extract text from each paragraph
        text_list = [p.get_text() for p in paragraphs]
        
        return text_list
    else:
        # If the request was not successful, print an error message
        print("Failed to fetch the webpage:", response.status_code)
        return None
    

def write_list_to_file(lst, filename):
    try:
        # Open the file in write mode
        with open(filename, 'w') as file:
            # Write each item from the list to the file
            for item in lst:
                file.write(str(item) + '\n')
        print("List contents written to", filename)
    except Exception as e:
        print("Error:", e)

def generate_filename(base_name, extension, index):
    #Generate a filename recursively.
    filename = f"{base_name}_{index}.{extension}"
    if os.path.exists(filename):
        return generate_filename(base_name, extension, index + 1)
    return filename


file = open("../data/no_pdf_list_div3.txt", 'r')
link_contents = file.read()
link_list = ast.literal_eval(link_contents)
file.close()

base_name = "link"
extension = "txt"

for i in range(0,len(link_list)):
    url = link_list[i]
    print(url)
    paragraphs = scrape_paragraphs(url)
    index =+ 1
    generated_txt = generate_filename(base_name, extension, index)
    write_list_to_file(paragraphs, generated_txt)