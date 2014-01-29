import sla_parser

sla = sla_parser.Sla('eg.sla')


with open('output.txt', 'w') as f:
    for item in sla.get_output():
        print item
        f.write(item.to_string())

print 'done.'

#from PIL import ImageFont
#font = ImageFont.truetype('fonts/FreeSansRegular.ttf', 12)
#print font.getsize('\n')
#print font.getsize('\n\n')