
class Content(object):
    def __init__(self):
        self.content = ''
        self.font = None
        self.fontsize = None
        self.should_display = True

    def set_content(self, content):
        self.content = content

    def to_string(self):
        return self.content

    def to_html(self):
        return self.content

    def to_markdown(self):
        return self.content


class Paragraph(Content):
    def __init__(self, content='', cls='', id=''):
        Content.__init__(self)
        self.content = content
        self.cls = cls
        self.id = id

    def to_html(self):
        return '<p id="{id}" class="{class}">{content}</p>'.format({
            'content': self.content,
            'class': self.cls,
            'id': self.id
        })


class Header(Content):
    def __init__(self, content='', level=1, cls='', id=''):
        Content.__init__(self)
        self.content = content
        self.level = level
        self.cls = cls
        self.id = id

    def to_html(self):
        return '<h{level} id="{id}" class="{class}">{content}</h{level}>'.format({
            'content': self.content,
            'level': self.level,
            'class': self.cls,
            'id': self.id
        })


class Image(Content):
    def __init__(self, src='', alt='', cls='', id=''):
        Content.__init__(self)
        self.src = src
        self.alt = alt
        self.cls = cls
        self.id = id

    def to_html(self):
        return '<img src="{src}" id="{id}" class="{class}" alt="{alt}">'.format({
            'src': self.src,
            'alt': self.alt,
            'class': self.cls,
            'id': self.id
        })

    def to_string(self):
        return '[IMAGE: ' + self.src + ' ]'


class Pre(Content):
    def __init__(self, content='', cls='', id=''):
        Content.__init__(self)
        self.content = content
        self.cls = cls
        self.id = id

    def to_html(self):
        return '<pre id="{id}" class="{class}">{content}</pre>'.format({
            'content': self.content,
            'class': self.cls,
            'id': self.id
        })

