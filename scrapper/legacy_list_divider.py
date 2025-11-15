import ast

with open("../data/legacy_no_pdf_list.txt", "r") as file:
    links_list = ast.literal_eval(file.read())

division_1 = []
division_2 = []
division_3 = []

for i in range(0,996):
    division_1.append(links_list[0])
    links_list = links_list[1:]

with open("../data/legacy_no_pdf_list_div1.txt", "w") as file:
    no_pdf_list_div1 = str(division_1)
    file.write(no_pdf_list_div1)

for i in range(0,996):
    division_2.append(links_list[0])
    links_list = links_list[1:]

with open("../data/legacy_no_pdf_list_div2.txt", "w") as file:
    no_pdf_list_div2 = str(division_2)
    file.write(no_pdf_list_div2)

for i in range(0,len(links_list)):
    division_3.append(links_list[0])
    links_list = links_list[1:]

with open("../data/legacy_no_pdf_list_div3.txt", "w") as file:
    no_pdf_list_div3 = str(division_3)
    file.write(no_pdf_list_div3)

print(len(division_1))
print(len(division_2))
print(len(division_3))
print(len(links_list))