

import xml.etree.ElementTree as ET
from PIL import ImageFont

class Sla(object):
    def __init__(self, fname):
        self.tree = ET.parse(fname)
        self.root = self.tree.getroot()
        self.document = self.root.find('DOCUMENT') 
        
    def getElement(self, expr):
        return self.document.find(expr)
        
    def getElements(self, expr):
        return self.document.findall(expr)
    
    def getFloatAttribute(self, element, attr):
        return float(element.attrib[attr])
    
    def toString(self):
        global fonts
        fonts = []
        defaultStyle = self.document.find("./*[@DefaultStyle='1']")
        fonts.append(ImageFont.truetype('fonts/%s.ttf' %defaultStyle.attrib['FONT'] , defaultStyle.attrib['FONTSIZE']))
        
        self.pages = self.getElements('PAGE')
        self.layers = self.getElements('LAYERS')
        pageObjectTypes = {'2':Image, '4':TextFrame}
        self.pageObjects = [pageObjectTypes[el.attrib['PTYPE']](el)
                            for el in self.getElements('PAGEOBJECT')
                            if el.attrib['PTYPE'] in pageObjectTypes]
        self.pdf = self.getElement('PDF')
        self.resolution = self.getFloatAttribute(self.pdf, 'Resolution')
        for page in self.pages:
            pagen = page.attrib['NUM']
            

class PageObject(object):
    def __init__(self, el):
        self.x = el.attrib['XPOS']
        self.y = el.attrib['YPOS']
        self.hasBeenOutput = False
        self.items = []
        
class TextFrame(PageObject):
    def __init__(self, el):
        PageObject.__init__(self, el)
        textTypes = {'ITEXT':Text, 'para':Para, 'Tab':Tab}
        self.items = [textTypes[child.tag](child) for child in el if child.tag in textTypes]
        
class Image(PageObject):
    def __init__(self, el):
        PageObject.__init__(self, el)
        
class TextFrameItem(object):
    def __init__(self, el):
        self.el = el
        
class Text(TextFrameItem):
    def __init__(self, el):
        TextFrameItem.__init__(self, el)
        
    def toString(self):
        return self.el.attrib['CH']
    
    def __len__(self):
        if 'FONT' in self.el.attrib:
            font = self.el.attrib['FONT']
        if 'FONTSIZE' in self.el.attrib:
            fontSize = self.el.attrib['FONTSIZE']
        
class Para(TextFrameItem):
    def __init__(self, el):
        TextFrameItem.__init__(self, el)
        
    def toString(self):
        return '\n'
        
class Tab(TextFrameItem):
    def __init__(self, el):
        TextFrameItem.__init__(self, el)
        
    def toString(self):
        return '\t'
            
        
sla = Sla('eg.sla')
sla.toString()
#from PIL import ImageFont
#font = ImageFont.truetype('fonts/FreeSans.ttf' , 12)
#print font.getsize('Hello world')
        
