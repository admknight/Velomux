"""Draw a static design concept; not the running Qt GUI or user data."""
from PIL import Image,ImageDraw,ImageFont
from pathlib import Path

root=Path(__file__).resolve().parent
W,H=1600,960
im=Image.new('RGB',(W,H),'#090E19')
d=ImageDraw.Draw(im)
REG='/usr/share/fonts/opentype/inter/Inter-Regular.otf'
MED='/usr/share/fonts/opentype/inter/Inter-Medium.otf'
SEMI='/usr/share/fonts/opentype/inter/Inter-SemiBold.otf'
BOLD='/usr/share/fonts/opentype/inter/Inter-Bold.otf'
EXTRA='/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf'
def font(size,weight=REG):return ImageFont.truetype(weight,size)
F11=font(11,SEMI); F12=font(12,SEMI); F13=font(13); F14=font(14); F16=font(16,SEMI); F18=font(18,BOLD); F22=font(22,BOLD); F26=font(26,EXTRA); F36=font(36,EXTRA)
FG='#F0F4FA'; MUTED='#98ABC5'; BORDER='#283750'; PANEL='#111A2C'; PURPLE='#9B93FF'; MINT='#4ADEBA'
def text(x,y,t,f=F14,fill=FG):d.text((x,y),t,font=f,fill=fill,stroke_width=0)
def rr(x0,y0,x1,y1,r,fill,outline=None,width=1):d.rounded_rectangle((x0,y0,x1,y1),radius=r,fill=fill,outline=outline,width=width)
def line(x0,y0,x1,y1,color='#27374F',width=1):d.line((x0,y0,x1,y1),fill=color,width=width)
def btn(x,y,w,h,label,primary=False):
    rr(x,y,x+w,y+h,10,'#8980FF' if primary else '#1B2940','#9D95FF' if primary else '#30405A')
    ft=font(13,SEMI)
    box=d.textbbox((0,0),label,font=ft)
    tw=box[2]-box[0];th=box[3]-box[1]
    text(x+(w-tw)/2,y+(h-th)/2-3,label,ft,'#13172F' if primary else '#E6EDFA')

# sidebar
rr(0,0,237,959,0,'#0E1727')
line(237,0,237,960,'#26354C')
rr(22,24,71,73,14,PURPLE)
text(37,29,'V',font(32,EXTRA),'#111528')
text(83,27,'VELOMUX',font(15,BOLD),'#B8B0FF')
text(83,49,'MEDIA CONVERTER',font(11,SEMI))
text(28,140,'WORKSPACE',F11,'#71859D')
for y,s,caption,active in [(177,'▦','Converter',True),(229,'▤','Activity',False),(281,'↻','Update Center',False),(333,'ⓘ','About',False)]:
    if active:
        rr(18,y-4,218,y+42,12,'#292951')
        rr(18,y-4,22,y+42,2,PURPLE)
    ico='#CEC7FF' if active else '#91A5BF'
    if caption=='Converter':
        for ox in (0,11):
            for oy in (0,11):rr(37+ox,y+9+oy,45+ox,y+17+oy,2,ico)
    elif caption=='Activity':
        for oy in (9,16,23):line(37,y+oy,56,y+oy,ico,2)
    elif caption=='Update Center':
        d.arc((36,y+8,56,y+29),30,310,fill=ico,width=3)
        d.polygon([(52,y+7),(60,y+13),(51,y+15)],fill=ico)
    else:
        d.ellipse((37,y+8,57,y+28),outline=ico,width=2)
        text(45,y+10,'i',F13,ico)
    text(75,y+7,caption,font(15,SEMI),'#EAE6FF' if active else '#A6B7CE')
text(28,789,'BUILT FOR EVERYONE',F11,'#8A9DB4')
text(28,815,'Open-source ambition.',F13,'#90A1B9')
text(28,836,'Offline-first by design.',F13,'#90A1B9')
text(28,857,'Powerful FFmpeg inside.',F13,'#90A1B9')
rr(28,893,192,929,9,'#162137','#34445C')
text(40,904,'PREVIEW · 0.2.1',F11,'#A9BAD0')

# top title
text(270,29,'Your media. Your format.',F36,FG)
text(270,84,'Powerful conversion, simple controls, fully local.',font(15),MUTED)
rr(1314,42,1557,86,12,'#152D2B','#294B44')
d.ellipse((1329,57,1338,66),fill=MINT)
text(1351,55,'Bundled FFmpeg ready',font(13,SEMI),'#7BECBD')

# metrics
metrics=[('MEDIA IN QUEUE','3',PURPLE),('COMPLETED','0',MINT),('READY TO CONVERT','3','#F0BC75')]
for i,(label,num,col) in enumerate(metrics):
    x=270+i*431
    rr(x,130,x+414,239,15,PANEL,BORDER)
    text(x+23,149,label,F11,'#91A6C1')
    text(x+23,171,num,font(32,EXTRA),col)

# panels
LX,LY,LW,LH=270,259,831,641
RX,RW=1117,440
rr(LX,LY,LX+LW,LY+LH,17,PANEL,BORDER)
rr(RX,LY,RX+RW,LY+LH,17,PANEL,BORDER)
text(295,283,'Conversion workspace',F22)
# Drop panel gradient strip
x0,y0,x1,y1=293,327,1078,455
rr(x0,y0,x1,y1,14,'#20284C','#7176C0')
for y in range(y0+4,y1-4,4):
    z=(y-y0)/(y1-y0)
    d.line((x0+4,y,x1-4,y),fill=(int(30-7*z),int(39+8*z),int(77-18*z)),width=4)
rr(x0+2,y0+2,x1-2,y1-2,12,None,'#5D67A6')
rr(420,358,478,420,14,'#3A376A')
text(435,364,'↓',font(35,SEMI),'#CBC5FF')
text(499,359,'Drop media here to convert',font(20,BOLD))
text(499,393,'Video  ·  Audio  ·  Images   |   Original files stay untouched',font(13), '#ABBADD')
# toolbar
btn(293,474,132,42,'+  Add files',True)
btn(433,474,133,42,'Add folder')
btn(574,474,158,42,'Remove selected')
btn(979,474,99,42,'Clear')
rr(293,527,1078,569,10,'#19263B','#30425D')
d.ellipse((308,539,320,551),outline='#8C9FB9',width=2)
line(318,549,326,558,'#8C9FB9',2)
text(337,538,'Search files in queue...',font(14),'#8C9FB9')
# table
rr(293,583,1078,764,12,'#121D30','#27364C')
rr(295,585,1076,628,9,'#1B293F')
headers=[('FILE',309),('TYPE',626),('SIZE',712),('TARGET',818),('STATUS',944)]
for txt,x in headers:text(x,599,txt,F11,'#98ABC7')
for j,(name,typ,size,target) in enumerate([('demo_movie.mp4','VIDEO','74.2 MB','MP4'),('sample_track_01.mp3','AUDIO','7.8 MB','M4A'),('sample_photo.png','IMAGE','2.3 MB','WEBP')]):
    y=629+j*44
    if j==1:rr(295,y,1076,y+44,1,'#162139')
    text(309,y+12,name,F13,FG);text(626,y+12,typ,F12,'#BAC6D7');text(712,y+12,size,F12,'#BAC6D7')
    rr(817,y+8,867,y+32,6,'#273A57')
    text(826,y+12,target,F11,'#B8C4D8')
    text(944,y+12,'Waiting',F12,'#F0BB7B')
    line(296,y+43,1076,y+43,'#27344C')
text(294,785,'BATCH PROGRESS',F11,'#9FB1C9');text(1053,785,'0%',F11,'#9FB1C9')
rr(294,813,1078,824,6,'#27374F')
btn(294,845,194,42,'▶   Start conversion',True)
btn(498,845,157,42,'■   Cancel batch')
btn(910,845,168,42,'Open destination')

# settings
text(1140,282,'Conversion settings',F22)
text(1140,316,'Choose a format. Fine-tune options when needed.',font(12),MUTED)
text(1140,344,'CONTROLS MODE',F11,'#8CA1B8')
rr(1140,367,1536,409,10,'#182338','#32415C')
rr(1342,371,1532,404,7,'#363A6D')
text(1191,378,'Quick mode',F13,'#90A4BE')
text(1389,378,'Advanced mode',F13,'#EAE6FF')
text(1140,424,'FORMAT FAMILY',F11,'#8CA1B8')
rr(1140,446,1536,488,9,'#18263C','#35445E');text(1153,458,'Audio',F13);text(1511,456,'⌄',font(16),'#A6B8CD')
text(1140,501,'OUTPUT PRESET',F11,'#8CA1B8')
rr(1140,523,1536,565,9,'#18263C','#35445E');text(1153,535,'M4A - AAC (smart copy)',F13);text(1511,533,'⌄',font(16),'#A6B8CD')
btn(1140,579,396,42,'Apply preset to selected files')
labels=['General','Video','Audio','Images','Trim']
for i,txt in enumerate(labels):text(1140+i*79,642,txt,F12,'#E9E3FF' if i==0 else '#8FA3BC')
line(1140,668,1536,668)
line(1140,667,1210,667,'#A49AFF',3)
rr(1140,682,1158,700,5,'#9C93FF')
text(1145,681,'✓',F13,'#16192B')
text(1170,683,'Use a Converted folder beside each input',F13,'#D5DDEF')
text(1140,713,'CUSTOM OUTPUT DIRECTORY',F11,'#8CA1B8')
rr(1140,736,1461,775,9,'#18263C','#35445E');text(1152,748,'C:\\Media\\Converted',F12,'#ABBAD0')
btn(1471,736,65,39,'Browse')
text(1140,786,'EXISTING FILE HANDLING',F11,'#8CA1B8')
rr(1140,807,1536,846,9,'#18263C','#35445E');text(1152,819,'Repair incomplete; skip verified',F12);text(1511,818,'⌄',F13,'#A6B8CD')
rr(1141,859,1158,877,5,'#9C93FF');text(1146,858,'✓',F13,'#16192B');text(1170,860,'Preserve metadata',F12,'#D5DDEF')
text(274,930,'3 files in demo queue  ·  Static UI concept (not a runtime screenshot)',font(12),'#8799B2')
text(1244,930,'PRIVATE BY DEFAULT',F11,'#8498B2')
badge=Image.open(root.parent/'assets'/'velomux.png').convert('RGBA').resize((49,49),Image.Resampling.LANCZOS)
im.paste(badge,(22,24),badge)
im.save(root/'qt-ui-concept.png',optimize=True)
print(root/'qt-ui-concept.png')
