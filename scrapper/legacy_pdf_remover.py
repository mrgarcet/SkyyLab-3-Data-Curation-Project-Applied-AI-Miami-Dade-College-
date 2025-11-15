import ast

with open ("../data/cleaned_links_set.txt", 'r') as file:
    list_contents = file.read()
    links_list = ast.literal_eval(list_contents)

new_clean = []
for i in links_list:
        if ".pdf" not in i:
              new_clean.append(i)
print(len(new_clean))

with open("../data/no_pdf_list.txt", 'w') as file:
      no_pdf_list = str(new_clean)
      file.write(no_pdf_list)

            

        



