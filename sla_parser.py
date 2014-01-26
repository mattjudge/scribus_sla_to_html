

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
        #print 'New font: ', path, size
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


class Cursor(object):
    def __init__(self):
        self.x = 0
        self.y = 0
        self.max_x = 0


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
        if a.page < b.page: return -1
        if a.page > b.page: return 1
        #else same page continue
        if a.y < b.y: return -1
        if a.y > b.y: return 1
        #else same y continue
        if a.x < b.x: return -1
        if a.x > b.x: return 1
        return 0
    
    def toString(self):
        defaultStyle = self.document.find("./CHARSTYLE[@DefaultStyle='1']")
        addFont(defaultStyle.attrib['FONT'], defaultStyle.attrib['FONTSIZE'])
        default_font = defaultStyle.attrib['FONT']
        default_fontsize = defaultStyle.attrib['FONTSIZE']
        defaultParaStyle = self.document.find("./STYLE[@DefaultStyle='1']")
        default_linespace = defaultParaStyle.attrib['LINESP']

        self.layers = self.getElements('LAYERS')
        pageObjectTypes = {'2':Image, '4':TextFrame, None:PageObject}
        self.pdf = self.getElement('PDF')
        self.resolution = self.getFloatAttribute(self.pdf, 'Resolution')
        #self.masterpage = self.getElement('MASTERPAGE')
        self.pages = self.getElements('PAGE')

        self.pageObjects = []
        for el in self.getElements('PAGEOBJECT'):
            if el.attrib['PTYPE'] in pageObjectTypes:
                self.pageObjects.append(
                    pageObjectTypes[el.attrib['PTYPE']](el, default_font, default_fontsize, default_linespace)
                )
            else:
                self.pageObjects.append(
                    pageObjectTypes[None](el, default_font, default_fontsize, default_linespace)
                )

        print self.pageObjects[35].el.attrib['NEXTITEM']

        self.cursor = Cursor()
        self.output = ''
        sorted_pageobjects = sorted(self.pageObjects, cmp=self._compareHeights)
        for obj in sorted_pageobjects:
            self._outputObj(obj)

        items_not_rendered = 0
        for item in self.pageObjects:
            if not item.hasBeenOutput:
                items_not_rendered += 1
        print items_not_rendered, ' items not rendered out of ', len(self.pageObjects)
        return self.output

    def _checkForSkippedObjects(self):
        print self.cursor.x, self.cursor.y
        for obj in self.pageObjects:
            if not obj.hasBeenOutput and not obj.isBeingRendered:
                if obj.y <= self.cursor.y:
                    # object is higher than cursor
                    if obj.x <= self.cursor.max_x:
                        self._outputObj(obj)

    def _outputObj(self, obj):
        if not isinstance(obj, TextFrame):
            #self.output += 'cursor: ' + str(self.cursor.x) + '\t' + str(self.cursor.y) + '\n'
            #self.output += 'obj ps: ' + str(obj.x) + '\t' + str(obj.y) + '\n'
            self.output += obj.toString() #+ '\n'
        else:
            # is text frame
            while not obj.hasBeenOutput:
                #self.output += 'cursor: ' + str(self.cursor.x) + '\t' + str(self.cursor.y) + '\n'
                #self.output += 'obj ps: ' + str(obj.x) + '\t' + str(obj.y) + '\n'
                self.output += obj.getNextPara(self.cursor, self.pageObjects) + '\n'
                self._checkForSkippedObjects()


class PageObject(object):
    def __init__(self, el, default_font, default_fontsize, default_linespace):
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
        if 'LINESP' in self.el.attrib:
            self.linespace = self.el.attrib['LINESP']
        else:
            self.linespace = default_linespace

    def toString(self):
        return ''


class TextFrame(PageObject):
    def __init__(self, el, default_font, default_fontsize, default_linespace):
        PageObject.__init__(self, el, default_font, default_fontsize, default_linespace)
        self.coln = 1
        self.cols = int(el.attrib['COLUMNS'])
        self.colgap = float(el.attrib['COLGAP'])
        self.colwidth = self.width / self.cols

        textTypes = {'ITEXT':Text, 'para':Para, 'Tab':Tab}
        self.items = [textTypes[child.tag](child, self.font, self.fontsize, self.linespace) for child in el if child.tag in textTypes]

        self.next_item_pos = 0
        self.isFirstLinkedFrame = True

    def getMaxX(self):
        return self.x + (self.coln * self.colwidth) - (0.5 * self.colgap)

    def getNextPara(self, cursor, pageobjects):
        if self.isBeingRendered == False:
            self.isBeingRendered = True

        text = ''
        last_rowheight = 0
        for item in self.items[self.next_item_pos:]:
            textdelta, deltc, blockelement = item.getStringData()
            text = text + textdelta
            print '\n##'
            print 'old cursor  ', cursor.x, cursor.y
            print 'got delta c ', deltc.x, deltc.y,
            if len(textdelta) < 20:
                print textdelta
            else:
                print textdelta[:18], textdelta[-18:]

            cursor.x += deltc.x
            if blockelement:
                cursor.y += deltc.y
                last_rowheight = deltc.y
                #cursor.x = self.x
            elif deltc.y > last_rowheight:
                cursor.y += (deltc.y - last_rowheight)
                last_rowheight = deltc.y

            max_x = self.x + (self.coln * self.colwidth) - (0.5 * self.colgap)
            max_y = self.y + self.height
            print 'cursor+deltc', cursor.x, '/', max_x, ':', cursor.y, '/', max_y

            while cursor.x > self.x + (self.coln * self.colwidth) - (0.5 * self.colgap):
                cursor.x -= self.colwidth
                cursor.y += deltc.y
                if cursor.y > self.y + self.height:
                    print 'new page needed!', self.el.attrib['NEXTITEM']
                while cursor.y > self.y + self.height:
                    if self.coln < self.cols:
                        cursor.y = self.y
                        self.coln += 1
                        text += '\n##~~ NEW COLUMN\n'
                    else:
                        # next page
                        #print 'attempting to move to next page (y > y_max)'
                        if 'NEXTITEM' in self.el.attrib:
                            if self.el.attrib['NEXTITEM'] != '' and self.el.attrib['NEXTITEM'] != '-1':
                                text += '\n##~~ NEXT PAGE ~~##\n'
                                self.hasBeenOutput = True
                                self.isBeingRendered = False
                                print 'moving to frame id', self.el.attrib['NEXTITEM']
                                old_x = self.x
                                old_y = self.y
                                old_height = self.height
                                print 'old..', old_x, old_y
                                self.el = pageobjects[int(self.el.attrib['NEXTITEM'])].el
                                self.x = float(self.el.attrib['XPOS'])
                                self.y = float(self.el.attrib['YPOS'])
                                self.width = float(self.el.attrib['WIDTH'])
                                self.height = float(self.el.attrib['HEIGHT'])
                                self.page = int(self.el.attrib['OwnPage'])

                                self.coln = 1
                                self.cols = int(self.el.attrib['COLUMNS'])
                                self.colgap = float(self.el.attrib['COLGAP'])
                                self.colwidth = self.width / self.cols

                                self.hasBeenOutput = False
                                self.isBeingRendered = True

                                print self.x, self.y, self.el.attrib['YPOS']
                                cursor.x = cursor.x - old_x + self.x
                                cursor.y = cursor.y - (old_y + old_height) + self.y
                                print 'new..', self.x, self.y
                            else:
                                break
                        else:
                            break


            max_x = self.x + (self.coln * self.colwidth) - (0.5 * self.colgap)
            cursor.max_x = max_x
            max_y = self.y + self.height
            print 'new cursor: ', cursor.x, '/', max_x, ':', cursor.y, '/', max_y

            self.next_item_pos += 1
            if isinstance(item, Para):
                return text
        self.hasBeenOutput = True
        self.isBeingRendered = False
        return text

        
class Image(PageObject):
    def __init__(self, el, default_font, default_fontsize, default_linespace):
        PageObject.__init__(self, el, default_font, default_fontsize, default_linespace)

    def toString(self):
        if 'PFILE' in self.el.attrib:
            path = self.el.attrib['PFILE']
        else:
            path = '~~'
        self.hasBeenOutput = True
        print '[IMAGE: ' + path + ']'
        return '[IMAGE: ' + path + ']'
        
class TextFrameItem(object):
    def __init__(self, el, default_font, default_fontsize, default_linespace):
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
        if 'LINESP' in self.el.attrib:
            self.linespace = self.el.attrib['LINESP']
        else:
            self.linespace = default_linespace

    def isBlockElement(self):
        return False

    def toString(self):
        return ''

    def getRenderSize(self):
        font = getFont(self.font, self.fontsize, self.default_font, self.default_fontsize)
        cursor = Cursor()
        renderarea = font.getsize(self.toString())
        cursor.x = renderarea[0]
        cursor.y = int(self.linespace)
        #cursor.y = renderarea[1]
        return cursor

    def getStringData(self):
        return (self.toString(), self.getRenderSize(), self.isBlockElement())


class Text(TextFrameItem):
    def __init__(self, el, default_font, default_fontsize, default_linespace):
        TextFrameItem.__init__(self, el, default_font, default_fontsize, default_linespace)
        
    def toString(self):
        return self.el.attrib['CH']

        
class Para(TextFrameItem):
    def __init__(self, el, default_font, default_fontsize, default_linespace):
        TextFrameItem.__init__(self, el, default_font, default_fontsize, default_linespace)
        
    def toString(self):
        return '\n'

    def isBlockElement(self):
        return True


class Tab(TextFrameItem):
    def __init__(self, el, default_font, default_fontsize, default_linespace):
        TextFrameItem.__init__(self, el, default_font, default_fontsize, default_linespace)
        
    def toString(self):
        return '\t'
            
        
sla = Sla('eg.sla')

f = open('output.txt', 'w')
f.write(sla.toString())
f.close()

#from PIL import ImageFont
#font = ImageFont.truetype('fonts/FreeSansRegular.ttf', 12)
#print font.getsize('\n')
#print font.getsize('\n\n')

