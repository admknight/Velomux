"""Generate Velomux mark; icon is designed for both dark UI and Windows."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
S = 1024
background = Image.new('RGBA', (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(background)
d.rounded_rectangle((20,20,S-20,S-20), radius=230, fill=(16,22,40,255))
# Soft coloured light, clipped to the rounded-square silhouette.
glow = Image.new('RGBA', (S,S), (0,0,0,0))
g = ImageDraw.Draw(glow)
g.ellipse((30,-160,760,590),fill=(100,75,255,125))
g.ellipse((440,380,1140,1100), fill=(26,232,196,104))
glow=glow.filter(ImageFilter.GaussianBlur(185))
mask=Image.new('L',(S,S),0)
ImageDraw.Draw(mask).rounded_rectangle((20,20,S-20,S-20),radius=230,fill=255)
glow.putalpha(Image.composite(glow.getchannel('A'),Image.new('L',(S,S),0),mask))
background=Image.alpha_composite(background,glow)
# Sharp, bidirectional V mark: two interlocking wings with a small gap.
mark=Image.new('RGBA',(S,S),(0,0,0,0))
m=ImageDraw.Draw(mark)
# Main lavender wing
m.polygon([(170,275),(317,275),(516,625),(441,751)],fill=(153,145,255,255))
m.polygon([(174,274),(318,274),(347,325),(205,325)],fill=(183,177,255,255))
# Cyan forward wing
m.polygon([(707,273),(851,273),(570,746),(502,623)], fill=(62,224,193,255))
m.polygon([(706,273),(853,273),(823,326),(677,326)],fill=(127,245,221,255))
# Thin luminous core at the joining tip
m.polygon([(441,751),(510,634),(570,746),(509,845)],fill=(238,246,255,255))
background=Image.alpha_composite(background,mark)
# Crisp border silhouette
b=ImageDraw.Draw(background)
b.rounded_rectangle((22,22,S-22,S-22), radius=224, outline=(176,184,255,38),width=3)
main=background.convert('RGBA')
main.resize((512,512),Image.Resampling.LANCZOS).save(HERE/'velomux.png',optimize=True)
main.save(HERE/'velomux.ico',format='ICO',sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
print('Generated velomux.png and velomux.ico')
