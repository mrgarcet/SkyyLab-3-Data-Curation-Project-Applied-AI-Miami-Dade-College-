import os
import ast

def clean_links(url):
    # Find the index of the "#" character
    index = url.find('#')
    
    # If "#" is found, remove everything after it
    if index != -1:
        url = url[:index]
    
    return url

def create_list_without_duplicates(lst):
    cleaned_links_set = []

    for i in lst:
        if i not in cleaned_links_set:
            cleaned_links_set.append(i)

    return cleaned_links_set

def append_list_to_file(lst, filename):
    #turn list to string
    list_turned_into_string = str(lst)
    try:
        # Open the file in append mode
        with open(filename, 'a') as file:
            # Write each item from the list to the file
            file.write(list_turned_into_string)
        print("List contents appended to", filename)
    except Exception as e:
        print("Error:", e)


cleaned_links_list = []

file = open("../data/legacy_processed_mdc_links.txt", 'r')
link_contents = file.read()
link_list = ast.literal_eval(link_contents)
file.close()


for n in range(0,len(link_list)):
    cleaned_links_list.append(clean_links(link_list[n]))

append_list_to_file(create_list_without_duplicates(cleaned_links_list),
                    "../data/legacy_cleaned_links_set.txt")