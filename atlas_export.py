import fitz, os

workspace = "C:\\PGIS\\QGIS_atlas"
documents = []
for i in range(1, 76):
    if i == 57:
        continue
    element = workspace + "\\atlas" + str(i) + ".pdf"
    documents.append(element)

result = fitz.open()

for pdf in documents:
    with fitz.open(pdf) as mfile:
        result.insertPDF(mfile)
    
result.save(workspace + "\\atlas.pdf")

for pdf in documents:
    os.remove(pdf)