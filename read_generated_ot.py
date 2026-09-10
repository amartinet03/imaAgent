import zipfile
import xml.etree.ElementTree as ET
import os
import shutil

def read_docx(path):
    try:
        z = zipfile.ZipFile(path)
        xml_content = z.read('word/document.xml')
        tree = ET.XML(xml_content)
        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        paragraphs = []
        for p in tree.iterfind('.//w:p', ns):
            texts = [node.text for node in p.iterfind('.//w:t', ns) if node.text]
            if texts:
                paragraphs.append(''.join(texts))
            else:
                paragraphs.append('') # empty line for formatting
        return '\n'.join(paragraphs)
    except Exception as e:
        return str(e)

try:
    shutil.copy2('OUTPUT_Oferta_Tecnica_IMA.docx', 'temp_OUTPUT.docx')
    with open('generated_ot_text.txt', 'w', encoding='utf-8') as f:
        f.write('=== OUTPUT_Oferta_Tecnica_IMA.docx ===\n')
        f.write(read_docx('temp_OUTPUT.docx'))
    print("Done")
except Exception as e:
    print(f"Error copying: {e}")
