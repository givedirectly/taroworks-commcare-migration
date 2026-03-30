import xml.etree.ElementTree as ET

def element(name, attributes = {}, *, text = '', tail = '', contents = [], namespace = None):
    
    full_name = f'{namespace}:{name}' if namespace else name
    
    element = ET.Element(full_name, attributes)
    if text:
        element.text = text
    if tail:
        element.tail = tail
    element.extend(contents)
    
    return element