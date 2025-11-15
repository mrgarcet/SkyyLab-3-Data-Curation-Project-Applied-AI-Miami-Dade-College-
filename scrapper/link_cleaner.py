# import important libraries, import os currently not in use
import os
import ast

# Cleans each link by removing everything after #
def clean_links(url):
    # Find the index of the "#" character
    index = url.find('#')
    
    # If "#" is found, remove everything after it
    if index != -1:
        url = url[:index]
    
    return url

# Removes duplicates from the cleaned list
def create_list_without_duplicates(lst):
    cleaned_links_set = []

    for i in lst:
        if i not in cleaned_links_set:
            cleaned_links_set.append(i)

    return cleaned_links_set

def append_list_to_file(lst, filename):
    try:
        # Open the file in append mode
        with open(filename, 'a') as file:
            # Write each item from the list to the file
            for item in lst:
                file.write(str(item) + '\n')
        print("List contents appended to", filename)
    except Exception as e:
        print("Error:", e)


cleaned_links_list = []

## Loads file processed_mdc_links.txt
file = open("../data/processed_mdc_links.txt", 'r')
link_contents = file.read()
link_list = ast.literal_eval(link_contents)
file.close()


for n in range(0,len(link_list)):
    # Writes the final unique list to cleaned_links_set.txt
    cleaned_links_list.append(clean_links(link_list[n]))

append_list_to_file(create_list_without_duplicates(cleaned_links_list), "../data/cleaned_links_set.txt")