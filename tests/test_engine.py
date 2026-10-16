from __future__ import annotations
import hashlib
from pathlib import Path
import subprocess
import threading

import pytest
from PIL import Image

from engine import (Options, convert, probe, validate_output, PRESET_MAP,
                    classify, compatibility, resolve_output)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

@pytest.fixture(scope='module')
def sample_mp4(tmp_path_factory):
    root=tmp_path_factory.mktemp('media')
    p=root/"90's Jhankar - test.mp4"
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y',
                    '-f','lavfi','-i','testsrc2=size=160x120:rate=15',
                    '-f','lavfi','-i','sine=frequency=440:sample_rate=44100',
                    '-t','2.5','-c:v','libx264','-preset','ultrafast','-pix_fmt','yuv420p',
                    '-c:a','aac','-b:a','96k',str(p)],check=True)
    return p


def test_classify_compatibility(sample_mp4):
    assert classify(sample_mp4)=='video'
    assert compatibility(sample_mp4,PRESET_MAP['M4A - AAC (smart copy)'])
    assert not compatibility(sample_mp4,PRESET_MAP['JPEG - Quality controlled'])


def test_audio_copy_repair_and_source_untouched(sample_mp4,tmp_path):
    saved=digest(sample_mp4)
    dest=tmp_path/'Converted'
    pr=PRESET_MAP['M4A - AAC (smart copy)']
    progress=[]
    r=convert(sample_mp4,dest,pr,Options(decode_check=True),lambda x,y: progress.append(x))
    assert r.status=='done',r.detail
    assert r.output and r.output.exists()
    assert probe(r.output)['streams'][0]['codec_name']=='aac'
    assert progress[-1]==100
    assert convert(sample_mp4,dest,pr,Options(decode_check=True)).status=='skipped'
    r.output.write_bytes(b'')
    assert convert(sample_mp4,dest,pr).status=='done'
    assert validate_output(r.output,pr,2.5,True)
    r.output.write_bytes(b'broken')
    assert convert(sample_mp4,dest,pr).status=='done'
    assert digest(sample_mp4)==saved
    assert len(list(dest.iterdir()))==1


def test_mp3_and_flac(sample_mp4,tmp_path):
    for preset in ('MP3 - 320 kbps','FLAC - Lossless'):
        r=convert(sample_mp4,tmp_path,preset)
        assert r.status=='done',r.detail
        assert r.output.stat().st_size>0


def test_video_scale_rotate_trim_speed(sample_mp4,tmp_path):
    opt=Options(video_width=128,video_height=72,rotate_video=90,trim_start=0.5,trim_end=2.0,
                media_speed=1.5,quality=30,video_speed='ultrafast')
    r=convert(sample_mp4,tmp_path,'MP4 - H.264 + AAC',opt)
    assert r.status=='done',r.detail
    video=next(s for s in probe(r.output)['streams'] if s.get('codec_type')=='video')
    assert (video['width'],video['height'])==(72,96)
    assert validate_output(r.output,PRESET_MAP['MP4 - H.264 + AAC'],1.0)


def test_video_remux_reject_filters(sample_mp4,tmp_path):
    opt=Options(video_width=128)
    r=convert(sample_mp4,tmp_path,'MP4 - Remux / Stream copy',opt)
    assert r.status=='failed'
    assert 'incompatible' in r.detail.lower()
    assert not list(tmp_path.glob('*.mp4'))


def test_gif_from_video(sample_mp4,tmp_path):
    r=convert(sample_mp4,tmp_path,'Animated GIF - Video to GIF',Options(trim_end=1.0))
    assert r.status=='done',r.detail
    with Image.open(r.output) as im:
        assert im.n_frames >= 4


def test_image_formats_alpha_and_animated(tmp_path):
    png=tmp_path/'alpha.png'
    im=Image.new('RGBA',(100,80),(0,0,0,0))
    im.putpixel((0,0),(255,0,0,255))
    im.save(png)
    dest=tmp_path/'Converted'
    opt=Options(image_width=50,image_height=50,image_quality=85)
    jpg=convert(png,dest,'JPEG - Quality controlled',opt)
    assert jpg.status=='done',jpg.detail
    with Image.open(jpg.output) as new:
        assert new.size==(50,40)
        assert new.mode=='RGB'
        assert all(x>=245 for x in new.getpixel((45,35)))
    webp=convert(png,dest,'WebP - Quality controlled',opt)
    assert webp.status=='done',webp.detail
    with Image.open(webp.output) as new:
        assert new.size==(50,40)
    frames=[Image.new('RGB',(24,24),color) for color in ('red','blue','green')]
    src=tmp_path/'animated.gif'
    frames[0].save(src,format='GIF',save_all=True,append_images=frames[1:],duration=120,loop=0)
    converted=convert(src,dest,'WebP - Quality controlled')
    assert converted.status=='done',converted.detail
    with Image.open(converted.output) as animation:
        assert animation.n_frames==3


def test_source_not_overwritten(tmp_path):
    from PIL import Image
    src=tmp_path/'same.png'
    Image.new('RGB',(40,40),'blue').save(src)
    original=digest(src)
    r=convert(src,tmp_path,'PNG - Lossless',Options(collision='overwrite'))
    assert r.status=='failed'
    assert digest(src)==original


def test_output_rename_and_cancel(sample_mp4,tmp_path):
    r=convert(sample_mp4,tmp_path,'M4A - AAC (smart copy)',Options(collision='rename'))
    assert r.status=='done',r.detail
    new=convert(sample_mp4,tmp_path,'M4A - AAC (smart copy)',Options(collision='rename'))
    assert new.status=='done'
    assert new.output != r.output
    cancel=threading.Event();cancel.set()
    third=convert(sample_mp4,tmp_path,'MP3 - 320 kbps',cancel=cancel)
    assert third.status=='cancelled'
    assert not (tmp_path/(sample_mp4.stem+'.mp3')).exists()


def test_bad_input_options(sample_mp4,tmp_path):
    bad=convert(sample_mp4,tmp_path,'M4A - AAC (smart copy)',Options(trim_start=3,trim_end=4))
    assert bad.status=='failed'
    bad=convert(sample_mp4,tmp_path,'MP4 - H.264 + AAC',Options(video_width=127))
    assert bad.status=='failed'


def test_custom_stem(sample_mp4,tmp_path):
    r=convert(sample_mp4,tmp_path,'M4A - AAC (smart copy)',output_stem='Song [mp4]')
    assert r.status=='done',r.detail
    assert r.output.name=='Song [mp4].m4a'
    r=convert(sample_mp4,tmp_path,'M4A - AAC (smart copy)',output_stem='../bad')
    assert r.status=='failed'
