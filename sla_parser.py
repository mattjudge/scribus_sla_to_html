import xml.etree.ElementTree as ElementTree
from PIL import ImageFont  # using pillow, for windows
import parser_objects

font_base_path = 'fonts/'
fonts = {}


def add_font(name, size, default_font=None, default_fontsize=None):
    path = font_base_path + name + '.ttf'
    path = path.replace(' ', '')  # font files are typically in a format with spaces from the name removed
    size = int(size)
    try:
        font = (ImageFont.truetype(path, size))
        fonts[(name, size)] = font
        #print 'New font: ', path, size
        return font
    except IOError:
        if default_font and default_fontsize:
            print '! Failed to find font: ', path, size, ' , using default instead'
            default_fontsize = int(default_fontsize)
            fonts[(name, size)] = fonts[(default_font, default_fontsize)]
            return fonts[(default_font, default_fontsize)]
        else:
            print '! Failed to find font: ', path, size, ' , none supplied as default'


def get_font(name, size, default_font=None, default_fontsize=None):
    size = int(size)
    if (name, size) in fonts:
        return fonts[(name, size)]
    else:
        return add_font(name, size, default_font, default_fontsize)


class Cursor(object):
    def __init__(self):
        self.x = 0
        self.y = 0
        self.max_x = 0


class Sla(object):
    def __init__(self, fname):
        self.tree = ElementTree.parse(fname)
        self.root = self.tree.getroot()
        self.document = self.root.find('DOCUMENT')
        self.layers = None
        self.pdf = None
        self.resolution = None
        self.pages = None
        self.cursor = None
        self.page_objects = []
        self.output = ''

    def get_element(self, expr):
        return self.document.find(expr)

    def get_elements(self, expr):
        return self.document.findall(expr)

    @staticmethod
    def _compare_heights(a, b):
        if a.page < b.page: return -1
        if a.page > b.page: return 1
        #else same page continue
        if a.y < b.y: return -1
        if a.y > b.y: return 1
        #else same y continue
        if a.x < b.x: return -1
        if a.x > b.x: return 1
        return 0

    def get_output(self):
        default_style = self.document.find("./CHARSTYLE[@DefaultStyle='1']")
        add_font(default_style.attrib['FONT'], default_style.attrib['FONTSIZE'])
        default_font = default_style.attrib['FONT']
        default_fontsize = default_style.attrib['FONTSIZE']
        default_para_style = self.document.find("./STYLE[@DefaultStyle='1']")
        default_linespace = default_para_style.attrib['LINESP']

        self.layers = self.get_elements('LAYERS')
        page_object_types = {'2': Image, '4': TextFrame, None: PageObject}
        self.pdf = self.get_element('PDF')
        self.resolution = float(self.pdf.attrib['Resolution'])
        #self.masterpage = self.getElement('MASTERPAGE')
        self.pages = self.get_elements('PAGE')

        self.page_objects = []
        for el in self.get_elements('PAGEOBJECT'):
            if el.attrib['PTYPE'] in page_object_types:
                self.page_objects.append(
                    page_object_types[el.attrib['PTYPE']](el, default_font, default_fontsize, default_linespace)
                )
            else:
                self.page_objects.append(
                    page_object_types[None](el, default_font, default_fontsize, default_linespace)
                )

        print self.page_objects[35].el.attrib['NEXTITEM']

        self.cursor = Cursor()
        self.output = []
        sorted_page_objects = sorted(self.page_objects, cmp=self._compare_heights)
        for obj in sorted_page_objects:
            self._output_object(obj)

        items_not_rendered = 0
        for item in self.page_objects:
            if not item.has_been_rendered:
                items_not_rendered += 1
        print items_not_rendered, ' items not rendered out of ', len(self.page_objects)
        return self.output

    def _check_for_skipped_objects(self):
        print self.cursor.x, self.cursor.y
        for obj in self.page_objects:
            if not obj.has_been_rendered and not obj.is_being_rendered:
                if obj.y <= self.cursor.y:
                    # object is higher than cursor
                    if obj.x <= self.cursor.max_x:
                        self._output_object(obj)

    def _output_object(self, obj):
        if not isinstance(obj, TextFrame):
            #self.output += 'cursor: ' + str(self.cursor.x) + '\t' + str(self.cursor.y) + '\n'
            #self.output += 'obj ps: ' + str(obj.x) + '\t' + str(obj.y) + '\n'
            self.output.append(obj.get_output())  # + '\n'
        else:
            # is text frame
            while not obj.has_been_rendered:
                #self.output += 'cursor: ' + str(self.cursor.x) + '\t' + str(self.cursor.y) + '\n'
                #self.output += 'obj ps: ' + str(obj.x) + '\t' + str(obj.y) + '\n'
                self.output.append(obj.get_next_para(self.cursor, self.page_objects))
                self._check_for_skipped_objects()


class PageObject(object):
    def __init__(self, el, default_font, default_fontsize, default_linespace):
        self.el = el
        self.x = float(el.attrib['XPOS'])
        self.y = float(el.attrib['YPOS'])
        self.width = float(el.attrib['WIDTH'])
        self.height = float(el.attrib['HEIGHT'])
        self.page = int(el.attrib['OwnPage'])
        self.has_been_rendered = False
        self.is_being_rendered = False
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

    def to_string(self):
        return ''

    def get_output(self):
        obj = parser_objects.Content()
        obj.set_content(self.to_string())
        return obj


class TextFrame(PageObject):
    def __init__(self, el, default_font, default_fontsize, default_linespace):
        PageObject.__init__(self, el, default_font, default_fontsize, default_linespace)
        self.coln = 1
        self.cols = int(el.attrib['COLUMNS'])
        self.colgap = float(el.attrib['COLGAP'])
        self.colwidth = self.width / self.cols

        text_types = {'ITEXT': Text, 'para': Para, 'Tab': Tab}
        self.items = [text_types[child.tag](child, self.font, self.fontsize, self.linespace)
                      for child in el
                      if child.tag in text_types]

        self.next_item_pos = 0
        self.is_first_linked_frame = True

    def get_max_x(self):
        return self.x + (self.coln * self.colwidth) - (0.5 * self.colgap)

    def _get_next_para_text(self, cursor, pageobjects):
        if not self.is_being_rendered:
            self.is_being_rendered = True

        text = ''
        last_row_height = 0
        for item in self.items[self.next_item_pos:]:
            delta_text, delta_cursor, is_block_element = item.get_string_data()
            text = text + delta_text
            print '\n##'
            print 'old cursor  ', cursor.x, cursor.y
            print 'got delta c ', delta_cursor.x, delta_cursor.y,
            if len(delta_text) < 20:
                print delta_text
            else:
                print delta_text[:18], delta_text[-18:]

            cursor.x += delta_cursor.x
            if is_block_element:
                cursor.y += delta_cursor.y
                last_row_height = delta_cursor.y
                #cursor.x = self.x
            elif delta_cursor.y > last_row_height:
                cursor.y += (delta_cursor.y - last_row_height)
                last_row_height = delta_cursor.y

            max_x = self.x + (self.coln * self.colwidth) - (0.5 * self.colgap)
            max_y = self.y + self.height
            print 'cursor+deltc', cursor.x, '/', max_x, ':', cursor.y, '/', max_y

            while cursor.x > self.x + (self.coln * self.colwidth) - (0.5 * self.colgap):
                cursor.x -= self.colwidth
                cursor.y += delta_cursor.y
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
                                self.has_been_rendered = True
                                self.is_being_rendered = False
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

                                self.has_been_rendered = False
                                self.is_being_rendered = True

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
        self.has_been_rendered = True
        self.is_being_rendered = False
        return text

    def get_next_para(self, cursor, pageobjects):
        return parser_objects.Paragraph(content=self._get_next_para_text(cursor, pageobjects))


class Image(PageObject):
    def __init__(self, el, default_font, default_fontsize, default_linespace):
        PageObject.__init__(self, el, default_font, default_fontsize, default_linespace)

    def to_string(self):
        if 'PFILE' in self.el.attrib:
            path = self.el.attrib['PFILE']
        else:
            path = '~~'
        self.has_been_rendered = True
        print '[IMAGE: ' + path + ']'
        return path

    def get_output(self):
        return parser_objects.Image(src=self.to_string())


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

    def is_block_element(self):
        return False

    def to_string(self):
        return ''

    def get_render_size(self):
        font = get_font(self.font, self.fontsize, self.default_font, self.default_fontsize)
        cursor = Cursor()
        render_area = font.getsize(self.to_string())
        cursor.x = render_area[0]
        cursor.y = int(self.linespace)
        #cursor.y = render_area[1]
        return cursor

    def get_string_data(self):
        return self.to_string(), self.get_render_size(), self.is_block_element()

    def get_output(self):
        obj = parser_objects.Content()
        obj.set_content(self.to_string())
        return obj


class Text(TextFrameItem):
    def __init__(self, el, default_font, default_fontsize, default_linespace):
        TextFrameItem.__init__(self, el, default_font, default_fontsize, default_linespace)

    def to_string(self):
        return self.el.attrib['CH']


class Para(TextFrameItem):
    def __init__(self, el, default_font, default_fontsize, default_linespace):
        TextFrameItem.__init__(self, el, default_font, default_fontsize, default_linespace)

    def to_string(self):
        return '\n'

    def is_block_element(self):
        return True


class Tab(TextFrameItem):
    def __init__(self, el, default_font, default_fontsize, default_linespace):
        TextFrameItem.__init__(self, el, default_font, default_fontsize, default_linespace)

    def to_string(self):
        return '\t'


