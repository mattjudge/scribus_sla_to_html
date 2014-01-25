

import xml.etree.ElementTree as ET
from PIL import ImageFont # using pillow, for windows

font_base_path = 'fonts/'
fonts = {}

def addFont(name, size, default_font=None, default_fontsize=None):
    path = font_base_path + name + '.ttf'
    path = path.replace(' ', '') # font files are typically in a format with spaces from the name removed
    size = int(size)
    try:
        font = (ImageFont.truetype(path, size))
        fonts[(name, size)] = font
        print 'New font: ', path, size
        return font
    except IOError:
        if (default_font and default_fontsize):
            print '! Failed to find font: ',  path, size, ' , using default instead'
            default_fontsize = int(default_fontsize)
            fonts[(name, size)] = fonts[(default_font, default_fontsize)]
            return fonts[(default_font, default_fontsize)]
        else:
            print '! Failed to find font: ',  path, size, ' , none supplied as default'



def getFont(name, size, default_font=None, default_fontsize=None):
    size = int(size)
    if (name, size) in fonts:
        return fonts[(name, size)]
    else:
        return addFont(name, size, default_font, default_fontsize)


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

    def _compareHeights(self, a, b):
        if a.page > b.page: return -1
        if a.page < b.page: return 1
        #else same page continue
        if a.y < b.y: return -1
        if a.y > b.y: return 1
        #else same y continue
        if a.x < b.x: return -1
        if a.x > b.x: return 1
        return 0

    def _sort_page_objects(self):
        self.pageObjects = sorted(self.pageObjects, cmp=self._compareHeights)
    
    def toString(self):
        global fonts
        fonts = {}
        defaultStyle = self.document.find("./CHARSTYLE[@DefaultStyle='1']")
        addFont(defaultStyle.attrib['FONT'], defaultStyle.attrib['FONTSIZE'])
        default_font = defaultStyle.attrib['FONT']
        default_fontsize = defaultStyle.attrib['FONTSIZE']
        self.layers = self.getElements('LAYERS')
        pageObjectTypes = {'2':Image, '4':TextFrame}
        self.pdf = self.getElement('PDF')
        self.resolution = self.getFloatAttribute(self.pdf, 'Resolution')
        #self.masterpage = self.getElement('MASTERPAGE')
        self.pages = self.getElements('PAGE')
        self.pageObjects = [pageObjectTypes[el.attrib['PTYPE']](el, default_font, default_fontsize)
                            for el in self.getElements('PAGEOBJECT')
                            if el.attrib['PTYPE'] in pageObjectTypes]
        self._sort_page_objects()
        self.output = ''
        for obj in self.pageObjects:
            self._outputObj(obj)

        for item in self.pageObjects:
            print type(item), item.hasBeenOutput
        return self.output

    def _checkForSkippedObjects(self, max_x):
        for obj in self.pageObjects:
            if not obj.hasBeenOutput and not obj.isBeingRendered:
                if obj.y < self.cursorpos[1]:
                    # object is higher than cursor
                    if obj.x < max_x:
                        self._outputObj(obj)


    def _outputObj(self, obj):
        if not isinstance(obj, TextFrame):
            self.output += obj.toString()
        else:
            # is text frame
            self.cursorpos = [0,0]
            while not obj.hasBeenOutput:
                self.output += obj.getNextPara()
                cursor_delta = obj.getCursorDelta()
                self.cursorpos[0] += cursor_delta[0]
                self.cursorpos[1] += cursor_delta[1]
                self._checkForSkippedObjects(obj.getMaxX())


            

class PageObject(object):
    def __init__(self, el, default_font, default_fontsize):
        self.el = el
        self.x = float(el.attrib['XPOS'])
        self.y = float(el.attrib['YPOS'])
        self.width = float(el.attrib['WIDTH'])
        self.height = float(el.attrib['HEIGHT'])
        self.page = int(el.attrib['OwnPage'])
        self.hasBeenOutput = False
        self.isBeingRendered = False
        self.items = []

        self.default_font = default_font
        self.default_fontsize = default_fontsize
        if 'FONT' in self.el.attrib:
            self.font = self.el.attrib['FONT']
        else:
            self.font = default_font
        if 'FONT' in self.el.attrib:
            self.fontsize = self.el.attrib['FONTSIZE']
        else:
            self.fontsize = default_fontsize

    def toString(self):
        return ''
        
class TextFrame(PageObject):
    def __init__(self, el, default_font, default_fontsize):
        PageObject.__init__(self, el, default_font, default_fontsize)
        self.coln = 1
        self.cols = int(el.attrib['COLUMNS'])
        self.colgap = float(el.attrib['COLGAP'])
        self.colwidth = self.width / self.cols

        self.cursorDelta = [0, 0]
        textTypes = {'ITEXT':Text, 'para':Para, 'Tab':Tab}
        self.items = [textTypes[child.tag](child, self.font, self.fontsize) for child in el if child.tag in textTypes]

        self.next_item_pos = 0

    def getMaxX(self):
        return self.x + (self.coln * self.colwidth) - (0.5 * self.colgap)

    def getNextPara(self):
        if self.isBeingRendered == False:
            self.isBeingRendered = True
        self.cursorDelta = [0, 0]
        text = ''
        for item in self.items[self.next_item_pos:]:
            textdelta, deltc = item.getStringData()
            text = text + textdelta
            self.cursorDelta[0] += self.cursorDelta[0] % self.colwidth
            self.cursorDelta[1] += deltc[1] * (int(self.cursorDelta[0] / self.colwidth))
            self.next_item_pos += 1
            if isinstance(item, Para):
                return text
        self.hasBeenOutput = True
        self.isBeingRendered = False
        return text

    def getCursorDelta(self):
        return self.cursorDelta



        
class Image(PageObject):
    def __init__(self, el, default_font, default_fontsize):
        PageObject.__init__(self, el, default_font, default_fontsize)

    def toString(self):
        if 'PFILE' in self.el.attrib:
            path = self.el.attrib['PFILE']
        else:
            path = '~~'
        self.hasBeenOutput = True
        return '[IMAGE: ' + path + ']'
        
class TextFrameItem(object):
    def __init__(self, el, default_font, default_fontsize):
        self.el = el

        self.default_font = default_font
        self.default_fontsize = default_fontsize
        if 'FONT' in self.el.attrib:
            self.font = self.el.attrib['FONT']
        else:
            self.font = default_font
        if 'FONTSIZE' in self.el.attrib:
            self.fontsize = self.el.attrib['FONTSIZE']
        else:
            self.fontsize = default_fontsize

    def toString(self):
        return ''

    def getRenderSize(self):
        font = getFont(self.font, self.fontsize, self.default_font, self.default_fontsize)
        return font.getsize(self.toString())

    def getStringData(self):
        return (self.toString(), self.getRenderSize())


class Text(TextFrameItem):
    def __init__(self, el, default_font, default_fontsize):
        TextFrameItem.__init__(self, el, default_font, default_fontsize)
        
    def toString(self):
        return self.el.attrib['CH']

        
class Para(TextFrameItem):
    def __init__(self, el, default_font, default_fontsize):
        TextFrameItem.__init__(self, el, default_font, default_fontsize)
        
    def toString(self):
        return '\n'


class Tab(TextFrameItem):
    def __init__(self, el, default_font, default_fontsize):
        TextFrameItem.__init__(self, el, default_font, default_fontsize)
        
    def toString(self):
        return '\t'
            
        
sla = Sla('eg.sla')

f = open('output.txt', 'w')
f.write(sla.toString())
f.close()

#from PIL import ImageFont
#font = ImageFont.truetype('fonts/FreeSans Regular.ttf', 12)
#print font.getsize('\t')
        
