import zipfile
import xml.etree.ElementTree as ET

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

with open('docx_content_ot.txt', 'w', encoding='utf-8') as f:
    f.write('=== OT_1341_RAIZEN_MTO_Metalurgico_REV00.docx ===\n')
    f.write(read_docx('OT_1341_RAIZEN_MTO_Metalurgico_REV00.docx'))
print("Done")
