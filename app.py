"""Velomux - offline Windows desktop conversion interface."""
from __future__ import annotations

import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from dataclasses import dataclass

from engine import (PRESETS, PRESET_MAP, SUPPORTED_SUFFIXES, Options, classify,
                    compatibility, convert, describe, list_encoders,
                    validate_options, which_tools)

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    BASE_TK = TkinterDnD.Tk
    DRAG_DROP = True
except ImportError:
    BASE_TK = tk.Tk
    DRAG_DROP = False

APP_NAME = 'Velomux'
VERSION = '0.1.0'
BG = '#101824'
PANEL = '#172333'
PANEL2 = '#1c2b3e'
FG = '#f4f7fd'
SOFT = '#aab9cc'
ACCENT = '#31b8ad'
ACCENT2 = '#58d4cb'
DANGER = '#f17f77'
BORDER = '#293b50'

@dataclass
class Entry:
    source: Path
    preset: str
    state: str = 'Waiting'
    percent: float = 0
    output: str = ''

class MediaStudio(BASE_TK):
    def __init__(self):
        super().__init__()
        self.title(f'{APP_NAME}  |  v{VERSION}')
        self.geometry('1450x885')
        self.minsize(1080,725)
        self.configure(bg=BG)
        self.entries: dict[str,Entry] = {}
        self.seen: set[str] = set()
        self.counter=0
        self.events: queue.Queue = queue.Queue()
        self.cancel = threading.Event()
        self.worker: threading.Thread | None = None
        self.running=False
        self.total_running=0
        self.completed_running=0
        self._closing=False
        self.category_var=tk.StringVar(value='Audio')
        self.preset_var=tk.StringVar(value='M4A - AAC (smart copy)')
        self.output_var=tk.StringVar(value=str(Path.home()/'Downloads'/'Converted'))
        self.source_output_var=tk.BooleanVar(value=True)
        self.recursive_var=tk.BooleanVar(value=True)
        self.collision_var=tk.StringVar(value='Repair incomplete; skip verified')
        self.metadata_var=tk.BooleanVar(value=True)
        self.full_verify_var=tk.BooleanVar(value=False)
        self.video_crf=tk.StringVar(value='23')
        self.video_preset=tk.StringVar(value='medium')
        self.video_w=tk.StringVar(value='')
        self.video_h=tk.StringVar(value='')
        self.video_fps=tk.StringVar(value='')
        self.video_rotate=tk.StringVar(value='0')
        self.deinterlace=tk.BooleanVar(value=False)
        self.mute=tk.BooleanVar(value=False)
        self.audio_bitrate=tk.StringVar(value='')
        self.audio_sample_rate=tk.StringVar(value='')
        self.audio_channels=tk.StringVar(value='Source')
        self.audio_normalize=tk.BooleanVar(value=False)
        self.audio_gain=tk.StringVar(value='0')
        self.img_w=tk.StringVar(value='')
        self.img_h=tk.StringVar(value='')
        self.img_q=tk.StringVar(value='90')
        self.img_rotate=tk.StringVar(value='0')
        self.img_flip=tk.StringVar(value='none')
        self.grayscale=tk.BooleanVar(value=False)
        self.trim_start=tk.StringVar(value='')
        self.trim_end=tk.StringVar(value='')
        self.media_speed=tk.StringVar(value='1.0')
        self.summary=tk.StringVar(value='Ready  |  Drop files, browse for files, or add a folder.')
        self.overall=tk.DoubleVar(value=0)
        self._style()
        self._build()
        self._update_presets()
        self.protocol('WM_DELETE_WINDOW', self.close_app)
        self.after(100,self._pump_events)
        self.after(300,self._status_tools)

    def _style(self):
        style=ttk.Style(self)
        style.theme_use('clam')
        style.configure('.', background=BG, foreground=FG, font=('Segoe UI',10))
        style.configure('TFrame', background=BG)
        style.configure('Panel.TFrame', background=PANEL)
        style.configure('TLabel', background=BG, foreground=FG)
        style.configure('Panel.TLabel', background=PANEL, foreground=FG)
        style.configure('Hint.TLabel', background=PANEL, foreground=SOFT, font=('Segoe UI',9))
        style.configure('TButton', background=PANEL2, foreground=FG, padding=(12,9), bordercolor=BORDER, relief='flat')
        style.map('TButton', background=[('active','#2a4057'),('disabled','#182636')],foreground=[('disabled','#66788d')])
        style.configure('Accent.TButton', background=ACCENT, foreground='#061b22', padding=(14,10), font=('Segoe UI',10,'bold'))
        style.map('Accent.TButton', background=[('active',ACCENT2),('disabled','#235550')])
        style.configure('TCombobox', fieldbackground=PANEL2, background=PANEL2, foreground=FG,
                        arrowcolor=ACCENT, bordercolor=BORDER, padding=5)
        style.map('TCombobox', fieldbackground=[('readonly',PANEL2)], foreground=[('readonly',FG)])
        style.configure('TEntry', fieldbackground=PANEL2, foreground=FG, insertcolor=FG, bordercolor=BORDER,padding=6)
        style.configure('TCheckbutton', background=PANEL, foreground=FG)
        style.map('TCheckbutton', background=[('active',PANEL)], foreground=[('disabled',SOFT)])
        style.configure('TRadiobutton', background=PANEL,foreground=FG)
        style.configure('TNotebook', background=PANEL, borderwidth=0)
        style.configure('TNotebook.Tab', background='#1b2b3d', foreground=SOFT, padding=(10,7))
        style.map('TNotebook.Tab',background=[('selected',ACCENT)],foreground=[('selected','#061d22')])
        style.configure('Treeview',background=PANEL,foreground=FG,fieldbackground=PANEL, borderwidth=0,
                        rowheight=31,font=('Segoe UI',9))
        style.map('Treeview',background=[('selected','#235c69')], foreground=[('selected','#ffffff')])
        style.configure('Treeview.Heading',background=PANEL2,foreground=FG, font=('Segoe UI',9,'bold'), padding=7)
        style.configure('TProgressbar',troughcolor=PANEL2,background=ACCENT,borderwidth=0)
        style.configure('Vertical.TScrollbar',background=PANEL2,troughcolor=PANEL)

    def _build(self):
        header=tk.Frame(self,bg=BG,padx=22,pady=16)
        header.pack(fill='x')
        tit=tk.Frame(header,bg=BG);tit.pack(side='left')
        tk.Label(tit,text='VELOMUX',bg=BG,fg=ACCENT,font=('Segoe UI',11,'bold')).pack(anchor='w')
        tk.Label(tit,text='MEDIA CONVERTER',bg=BG,fg=FG,font=('Segoe UI',23,'bold')).pack(anchor='w')
        tk.Label(header,text='OFFLINE  /  VIDEO  /  AUDIO  /  IMAGES',bg=BG,fg=SOFT,font=('Segoe UI',9)).pack(side='right',anchor='s')
        body=tk.PanedWindow(self,orient='horizontal',bg=BG,sashwidth=8,sashrelief='flat',bd=0)
        body.pack(fill='both',expand=True,padx=16,pady=(0,8))
        left=ttk.Frame(body,style='Panel.TFrame',padding=14)
        right=ttk.Frame(body,style='Panel.TFrame',padding=14)
        body.add(left,stretch='always',minsize=525,width=980)
        body.add(right,stretch='never',minsize=340,width=435)
        self._build_queue(left)
        self._build_settings(right)
        footer=tk.Frame(self,bg=BG,padx=20,pady=12)
        footer.pack(fill='x')
        ttk.Label(footer,textvariable=self.summary,font=('Segoe UI',10)).pack(side='left',fill='x',expand=True)
        self.engine_status=tk.Label(footer,text='Checking FFmpeg...',bg=BG,fg=SOFT,font=('Segoe UI',9))
        self.engine_status.pack(side='right')

    def _build_queue(self,parent):
        head=ttk.Frame(parent,style='Panel.TFrame')
        head.pack(fill='x',pady=(0,10))
        ttk.Label(head,text='Conversion queue',style='Panel.TLabel',font=('Segoe UI',16,'bold')).pack(side='left')
        ttk.Label(head,text='Original files are never modified',style='Hint.TLabel').pack(side='right')
        btn=ttk.Frame(parent,style='Panel.TFrame');btn.pack(fill='x',pady=(0,11))
        self.add_btn=ttk.Button(btn,text='+ Add files',command=self.add_files,style='Accent.TButton')
        self.add_btn.pack(side='left',padx=(0,6))
        self.folder_btn=ttk.Button(btn,text='Add folder',command=self.add_folder)
        self.folder_btn.pack(side='left',padx=(0,6))
        self.remove_btn=ttk.Button(btn,text='Remove selected',command=self.remove_selected)
        self.remove_btn.pack(side='left',padx=(0,6))
        self.clear_btn=ttk.Button(btn,text='Clear queue',command=self.clear_queue)
        self.clear_btn.pack(side='left')
        ttk.Checkbutton(btn,text='Include subfolders',variable=self.recursive_var).pack(side='right')
        tree_frame=ttk.Frame(parent,style='Panel.TFrame');tree_frame.pack(fill='both',expand=True)
        columns=('filename','kind','preset','status','progress')
        self.tree=ttk.Treeview(tree_frame,columns=columns,show='headings',selectmode='extended')
        for key,title,width,anchor,stretch in (
            ('filename','FILE',320,'w',True),('kind','TYPE',70,'center',False),
            ('preset','OUTPUT / PRESET',220,'w',True),('status','STATUS',105,'center',False),
            ('progress','DONE',65,'center',False)):
            self.tree.heading(key,text=title)
            self.tree.column(key,width=width,minwidth=55,anchor=anchor,stretch=stretch)
        sy=ttk.Scrollbar(tree_frame,orient='vertical',command=self.tree.yview)
        sx=ttk.Scrollbar(tree_frame,orient='horizontal',command=self.tree.xview)
        self.tree.configure(yscrollcommand=sy.set,xscrollcommand=sx.set)
        self.tree.grid(row=0,column=0,sticky='nsew');sy.grid(row=0,column=1,sticky='ns');sx.grid(row=1,column=0,sticky='ew')
        tree_frame.rowconfigure(0,weight=1);tree_frame.columnconfigure(0,weight=1)
        self.tree.bind('<<TreeviewSelect>>',self.show_media_info)
        self.tree.bind('<Double-1>',self.open_result)
        if DRAG_DROP:
            try:
                self.tree.drop_target_register(DND_FILES)
                self.tree.dnd_bind('<<Drop>>',self._drop)
            except Exception: pass
        else:
            ttk.Label(parent,text='Tip: Install tkinterdnd2 to enable drag-and-drop. Add Files and Add Folder work without it.',
                      style='Hint.TLabel').pack(anchor='w',pady=(6,0))
        progress_frame=ttk.Frame(parent,style='Panel.TFrame');progress_frame.pack(fill='x',pady=(13,10))
        ttk.Label(progress_frame,text='Batch progress',style='Panel.TLabel',font=('Segoe UI',10,'bold')).pack(anchor='w')
        self.progress_bar=ttk.Progressbar(progress_frame,variable=self.overall,maximum=100)
        self.progress_bar.pack(fill='x',pady=(5,8))
        actions=ttk.Frame(progress_frame,style='Panel.TFrame');actions.pack(fill='x')
        self.start_btn=ttk.Button(actions,text='Start conversion',command=self.start_conversion,style='Accent.TButton')
        self.start_btn.pack(side='left',padx=(0,8))
        self.stop_btn=ttk.Button(actions,text='Cancel current batch',command=self.stop_conversion,state='disabled')
        self.stop_btn.pack(side='left',padx=(0,8))
        ttk.Button(actions,text='Open destination',command=self.open_destination).pack(side='right')
        ttk.Label(parent,text='Activity log',style='Panel.TLabel',font=('Segoe UI',10,'bold')).pack(anchor='w',pady=(7,3))
        frame=tk.Frame(parent,bg=PANEL)
        frame.pack(fill='both',expand=False)
        self.log=tk.Text(frame,height=7,bg='#0f1c2a',fg=SOFT,insertbackground=FG,
                         font=('Consolas',9),relief='flat',wrap='word',state='disabled')
        sb=ttk.Scrollbar(frame,orient='vertical',command=self.log.yview)
        self.log.configure(yscrollcommand=sb.set)
        self.log.pack(side='left',fill='both',expand=True);sb.pack(side='right',fill='y')
        self._log('Ready. Add files or folders, choose presets and click Start conversion.')

    def _build_settings(self,parent):
        ttk.Label(parent,text='Conversion settings',style='Panel.TLabel',font=('Segoe UI',16,'bold')).pack(anchor='w')
        ttk.Label(parent,text='Presets may be assigned to selected files.',style='Hint.TLabel').pack(anchor='w',pady=(3,12))
        self._setting_label(parent,'FORMAT FAMILY')
        cat=ttk.Combobox(parent,textvariable=self.category_var,values=('Video','Audio','Image'),state='readonly')
        cat.pack(fill='x',pady=(2,8));cat.bind('<<ComboboxSelected>>',lambda _e:self._update_presets())
        self._setting_label(parent,'OUTPUT PRESET')
        self.profile_combo=ttk.Combobox(parent,textvariable=self.preset_var,state='readonly')
        self.profile_combo.pack(fill='x',pady=(2,7))
        self.apply_btn=ttk.Button(parent,text='Apply preset to selected files',command=self.apply_preset)
        self.apply_btn.pack(fill='x',pady=(0,12))
        nb=ttk.Notebook(parent)
        nb.pack(fill='both',expand=True)
        general=self._tab(nb,'General')
        video=self._tab(nb,'Video')
        audio=self._tab(nb,'Audio')
        images=self._tab(nb,'Images')
        timing=self._tab(nb,'Trim / Speed')
        self._build_general(general)
        self._build_video(video)
        self._build_audio(audio)
        self._build_images(images)
        self._build_timing(timing)
        ttk.Label(parent,text='SELECTED MEDIA INSPECTOR',style='Hint.TLabel',font=('Segoe UI',9,'bold')).pack(anchor='w',pady=(13,5))
        self.inspector=tk.Text(parent,height=7,bg='#0f1c2a',fg=SOFT,insertbackground=FG,
                               font=('Consolas',9),wrap='word',relief='flat')
        self.inspector.pack(fill='both',expand=False)
        self._inspector_text('Select a file in the queue to inspect its format, codec, duration and dimensions.')

    def _tab(self,nb,title):
        outer=ttk.Frame(nb,style='Panel.TFrame',padding=(13,14))
        nb.add(outer,text=title)
        return outer

    def _setting_label(self,parent,text):
        ttk.Label(parent,text=text,style='Hint.TLabel',font=('Segoe UI',9,'bold')).pack(anchor='w')

    def _row(self,parent,label,var,values=None):
        row=ttk.Frame(parent,style='Panel.TFrame');row.pack(fill='x',pady=4)
        ttk.Label(row,text=label,style='Panel.TLabel',width=18).pack(side='left')
        if values is not None:
            element=ttk.Combobox(row,textvariable=var,values=values,state='readonly')
        else:element=ttk.Entry(row,textvariable=var)
        element.pack(side='right',fill='x',expand=True)
        return element

    def _build_general(self,f):
        ttk.Checkbutton(f,text='Save beside input in a Converted folder',variable=self.source_output_var).pack(anchor='w',pady=(0,9))
        ttk.Label(f,text='Custom destination',style='Hint.TLabel').pack(anchor='w')
        line=ttk.Frame(f,style='Panel.TFrame');line.pack(fill='x',pady=(3,7))
        ttk.Entry(line,textvariable=self.output_var).pack(side='left',fill='x',expand=True)
        ttk.Button(line,text='...',width=4,command=self.browse_output).pack(side='right',padx=(4,0))
        self._setting_label(f,'EXISTING FILE POLICY')
        ttk.Combobox(f,textvariable=self.collision_var,state='readonly',values=(
            'Repair incomplete; skip verified','Always replace','Skip anything existing','Create numbered copy'
        )).pack(fill='x',pady=(4,9))
        ttk.Checkbutton(f,text='Preserve metadata when supported',variable=self.metadata_var).pack(anchor='w',pady=3)
        ttk.Checkbutton(f,text='Full media decode check (slower)',variable=self.full_verify_var).pack(anchor='w',pady=3)
        ttk.Label(f,text='Safe replace: output is staged, validated, then moved into place.',
                  style='Hint.TLabel',wraplength=310).pack(anchor='w',pady=(11,0))

    def _build_video(self,f):
        self._row(f,'CRF / Quality',self.video_crf)
        self._row(f,'Encoding speed',self.video_preset,('ultrafast','superfast','veryfast','faster','fast','medium','slow','slower','veryslow'))
        self._row(f,'Max width (even)',self.video_w)
        self._row(f,'Max height (even)',self.video_h)
        self._row(f,'Frame rate (fps)',self.video_fps)
        self._row(f,'Rotate clockwise',self.video_rotate,('0','90','180','270'))
        ttk.Checkbutton(f,text='Deinterlace video (yadif)',variable=self.deinterlace).pack(anchor='w',pady=5)
        ttk.Checkbutton(f,text='Remove audio from video',variable=self.mute).pack(anchor='w',pady=5)
        ttk.Label(f,text='CRF: lower number = higher quality / larger file. Remux profiles do not re-encode.',
                  style='Hint.TLabel',wraplength=305).pack(anchor='w',pady=(10,0))

    def _build_audio(self,f):
        self._row(f,'Bitrate kbps*',self.audio_bitrate)
        self._row(f,'Sample rate Hz',self.audio_sample_rate)
        self._row(f,'Channels',self.audio_channels,('Source','Mono','Stereo','5.1','7.1'))
        self._row(f,'Gain dB',self.audio_gain)
        ttk.Checkbutton(f,text='Loudness normalization (-16 LUFS target)',variable=self.audio_normalize).pack(anchor='w',pady=8)
        ttk.Label(f,text='* Blank uses preset bitrate. AAC smart copy preserves the original track when no processing is selected, even if bitrate is overridden.',
                  style='Hint.TLabel',wraplength=305).pack(anchor='w',pady=(10,0))

    def _build_images(self,f):
        self._row(f,'Max width px',self.img_w)
        self._row(f,'Max height px',self.img_h)
        self._row(f,'Quality (1-100)',self.img_q)
        self._row(f,'Rotate clockwise',self.img_rotate,('0','90','180','270'))
        self._row(f,'Flip',self.img_flip,('none','horizontal','vertical'))
        ttk.Checkbutton(f,text='Convert to grayscale',variable=self.grayscale).pack(anchor='w',pady=9)
        ttk.Label(f,text='Image resize preserves aspect ratio. Transparent pixels become white when saving JPEG/BMP. Animated GIF/WebP is retained for compatible output formats.',
                  style='Hint.TLabel',wraplength=305).pack(anchor='w',pady=(10,0))

    def _build_timing(self,f):
        self._row(f,'Start at (seconds)',self.trim_start)
        self._row(f,'End at (seconds)',self.trim_end)
        self._row(f,'Playback speed',self.media_speed,('0.5','0.75','1.0','1.25','1.5','2.0'))
        ttk.Label(f,text='Start/end are positions in the ORIGINAL media. Leave both blank to process the whole file.',
                  style='Hint.TLabel',wraplength=305).pack(anchor='w',pady=(12,0))
        ttk.Label(f,text='Speed change requires re-encoding. Remux profiles cannot apply filters or speed adjustments.',
                  style='Hint.TLabel',wraplength=305).pack(anchor='w',pady=(12,0))

    def _status_tools(self):
        a,b=which_tools()
        if a and b:
            available=list_encoders()
            self.engine_status.configure(text=f'FFmpeg detected  /  {len(available)} encoders  /  Pillow ready',fg=ACCENT)
        else:
            self.engine_status.configure(text='FFmpeg / ffprobe missing from PATH  /  Image tools still work',fg=DANGER)

    def _update_presets(self):
        family=self.category_var.get().lower()
        values=[p.name for p in PRESETS if p.group == family]
        self.profile_combo['values']=values
        if self.preset_var.get() not in values:
            self.preset_var.set(values[0] if values else '')

    def _append_paths(self, paths):
        if self.running: return
        added=0
        chosen=PRESET_MAP.get(self.preset_var.get())
        for path in paths:
            path=Path(path).expanduser()
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES: continue
            key=os.path.normcase(os.path.abspath(str(path)))
            if key in self.seen: continue
            kind=classify(path)
            preset=chosen if chosen and compatibility(path,chosen) else next(
                (p for p in PRESETS if p.group == kind),PRESETS[0])
            self.counter+=1
            iid=str(self.counter)
            self.entries[iid]=Entry(path.resolve(),preset.name)
            self.seen.add(key)
            self._refresh(iid)
            added+=1
        self.summary.set(f'{len(self.entries)} file(s) queued. {added} new file(s) added.')
        self._log(f'Added {added} file(s).')

    def add_files(self):
        selected=filedialog.askopenfilenames(title='Choose media files',filetypes=[
            ('Media (video, audio, images)',' '.join('*'+s for s in sorted(SUPPORTED_SUFFIXES))),
            ('All files','*.*')])
        self._append_paths(selected)

    def add_folder(self):
        folder=filedialog.askdirectory(title='Choose media folder')
        if folder: self._scan_folder(Path(folder))

    def _scan_folder(self,folder):
        if self.recursive_var.get():
            paths=(p for p in folder.rglob('*') if not any(
                a.lower() == 'converted' for a in p.relative_to(folder).parts[:-1]))
        else: paths=folder.iterdir()
        self._append_paths(paths)

    def _drop(self,event):
        if self.running: return
        try:
            values=self.tk.splitlist(event.data)
            paths=[]
            for item in values:
                p=Path(item)
                if p.is_dir():
                    if self.recursive_var.get():
                        paths.extend(q for q in p.rglob('*') if 'converted' not in (s.lower() for s in q.relative_to(p).parts[:-1]))
                    else: paths.extend(p.iterdir())
                else: paths.append(p)
            self._append_paths(paths)
        except Exception as exc:
            self._log('Drag and drop error: '+str(exc))

    def apply_preset(self):
        preset=PRESET_MAP.get(self.preset_var.get())
        selected=self.tree.selection()
        if not selected:
            messagebox.showinfo('Select files','Select one or more queued files first.')
            return
        changed=0
        for iid in selected:
            row=self.entries[iid]
            if compatibility(row.source,preset):
                row.preset=preset.name
                row.state='Waiting';row.percent=0;row.output=''
                self._refresh(iid)
                changed+=1
            else:
                self._log(f'Ignored incompatible preset for {row.source.name}.')
        self._log(f'Applied {preset.name} to {changed} file(s).')

    def _refresh(self,iid):
        row=self.entries[iid]
        values=(row.source.name,classify(row.source).title(),row.preset,row.state,f'{row.percent:.0f}%')
        if self.tree.exists(iid):self.tree.item(iid,values=values)
        else:self.tree.insert('', 'end',iid=iid,values=values)

    def remove_selected(self):
        for iid in self.tree.selection():
            row=self.entries.pop(iid,None)
            if row:
                self.seen.discard(os.path.normcase(os.path.abspath(str(row.source))))
            self.tree.delete(iid)
        self.summary.set(f'{len(self.entries)} file(s) queued.')

    def clear_queue(self):
        for iid in list(self.entries): self.tree.delete(iid)
        self.entries.clear();self.seen.clear();self.overall.set(0)
        self.summary.set('Queue cleared.')
        self._inspector_text('Select a file in the queue to inspect its media details.')

    def show_media_info(self,_event=None):
        selected=self.tree.selection()
        if not selected: return
        row=self.entries.get(selected[0])
        if not row:return
        try: content=describe(row.source)
        except Exception as exc: content='Cannot inspect: '+str(exc)
        content+='\n\nPreset: '+row.preset
        if row.output:content+='\nOutput: '+row.output
        self._inspector_text(content)

    def _inspector_text(self,txt):
        self.inspector.configure(state='normal')
        self.inspector.delete('1.0','end');self.inspector.insert('1.0',txt)
        self.inspector.configure(state='disabled')

    def _log(self,message):
        self.log.configure(state='normal')
        self.log.insert('end',message+'\n')
        self.log.see('end')
        self.log.configure(state='disabled')

    def browse_output(self):
        folder=filedialog.askdirectory(title='Choose output directory')
        if folder: self.output_var.set(folder);self.source_output_var.set(False)

    def _gather_options(self):
        def intvar(v,zero=0):return int(v.get().strip()) if v.get().strip() else zero
        def floatvar(v,zero=0.0):return float(v.get().strip()) if v.get().strip() else zero
        collision={'Repair incomplete; skip verified':'repair','Always replace':'overwrite',
                   'Skip anything existing':'skip','Create numbered copy':'rename'}[self.collision_var.get()]
        channels={'Source':0,'Mono':1,'Stereo':2,'5.1':6,'7.1':8}[self.audio_channels.get()]
        opt=Options(collision=collision,quality=intvar(self.video_crf),video_speed=self.video_preset.get(),
             video_width=intvar(self.video_w),video_height=intvar(self.video_h),fps=floatvar(self.video_fps),
             rotate_video=intvar(self.video_rotate),deinterlace=self.deinterlace.get(),mute_video=self.mute.get(),
             trim_start=floatvar(self.trim_start),trim_end=floatvar(self.trim_end),
             audio_bitrate=intvar(self.audio_bitrate),audio_sample_rate=intvar(self.audio_sample_rate),
             audio_channels=channels,audio_normalize=self.audio_normalize.get(),
             audio_gain_db=floatvar(self.audio_gain),media_speed=floatvar(self.media_speed,1.0),
             image_width=intvar(self.img_w),image_height=intvar(self.img_h),image_quality=intvar(self.img_q),
             rotate_image=intvar(self.img_rotate),flip_image=self.img_flip.get(),grayscale=self.grayscale.get(),
             keep_metadata=self.metadata_var.get(),decode_check=self.full_verify_var.get())
        validate_options(opt)
        return opt

    def _toggle_buttons(self,running):
        self.running=running
        for btn in (self.add_btn,self.folder_btn,self.remove_btn,self.clear_btn,self.apply_btn):
            btn.configure(state='disabled' if running else 'normal')
        self.start_btn.configure(state='disabled' if running else 'normal')
        self.stop_btn.configure(state='normal' if running else 'disabled')

    def start_conversion(self):
        if self.running:return
        if not self.entries:
            messagebox.showinfo('Queue empty','Add at least one media file to convert.')
            return
        try:
            opt=self._gather_options()
            out=Path(self.output_var.get()).expanduser()
            if not self.source_output_var.get() and not str(self.output_var.get()).strip():
                raise ValueError('Please choose an output directory.')
        except Exception as exc:
            messagebox.showerror('Invalid settings',str(exc));return
        waiting=[]
        planned=set()
        for iid,entry in self.entries.items():
            source=entry.source
            dest=source.parent/'Converted' if self.source_output_var.get() else out
            ext=PRESET_MAP[entry.preset].ext
            stem=source.stem
            key=os.path.normcase(os.path.abspath(str(dest/(stem+ext))))
            if key in planned:
                stem=f'{stem} [{source.suffix.lstrip(chr(46)).lower()}]'
                key=os.path.normcase(os.path.abspath(str(dest/(stem+ext))))
                number=2
                while key in planned:
                    stem=f'{source.stem} [{source.suffix.lstrip(chr(46)).lower()}] {number}'
                    key=os.path.normcase(os.path.abspath(str(dest/(stem+ext))))
                    number+=1
                self._log(f'Output name collision avoided: {source.name} => {stem+ext}')
            planned.add(key)
            waiting.append((iid,source,entry.preset,stem))
        # Preflight external dependency checks (image-only batches do not need ffmpeg).
        if any(PRESET_MAP[preset].group != 'image' for _,_,preset,_ in waiting):
            a,b=which_tools()
            if not a or not b:
                messagebox.showerror('Missing FFmpeg','Install FFmpeg and ffprobe and add their directory to Windows PATH.')
                return
        self.cancel=threading.Event()
        self.overall.set(0)
        self.completed_running=0
        self.total_running=len(waiting)
        for iid,_,_,_ in waiting:
            self.entries[iid].state='Waiting'
            self.entries[iid].percent=0
            self._refresh(iid)
        self._toggle_buttons(True)
        per_source=self.source_output_var.get()
        def work():
            for count,(iid,source,preset_name,stem) in enumerate(waiting):
                if self.cancel.is_set():
                    self.events.put(('status',iid,'Cancelled',0,'','Not started'))
                    continue
                dest=source.parent/'Converted' if per_source else out
                self.events.put(('status',iid,'Running',0,'',''))
                def progress(val,detail, iid=iid,count=count):
                    self.events.put(('progress',iid,float(val),str(detail),count))
                result=convert(source,dest,preset_name,opt,progress,self.cancel,output_stem=stem)
                self.events.put(('status',iid,result.status.title(),100 if result.status == 'done' else 0,
                                 str(result.output or ''),result.detail))
                self.events.put(('batch_progress',count+1))
            self.events.put(('finished',))
        self.worker=threading.Thread(target=work,daemon=True)
        self.worker.start()
        self._log(f'Started {len(waiting)} conversions. Collision rule: {opt.collision}.')

    def stop_conversion(self):
        if self.running:
            self.cancel.set()
            self.summary.set('Cancelling active conversion; preserving original and existing output...')
            self._log('Cancellation requested.')
            self.stop_btn.configure(state='disabled')

    def _pump_events(self):
        try:
            for _ in range(250):
                message=self.events.get_nowait()
                event=message[0]
                if event=='status':
                    _,iid,state,percent,out,detail=message
                    row=self.entries.get(iid)
                    if row:
                        row.state=state
                        row.percent=percent
                        if out:row.output=out
                        self._refresh(iid)
                        self._log(f'[{state.upper()}] {row.source.name}: {detail}')
                elif event=='progress':
                    _,iid,percent,detail,count=message
                    row=self.entries.get(iid)
                    if row:
                        row.percent=percent
                        self._refresh(iid)
                        self.summary.set(f'{count+1}/{self.total_running} | {row.source.name} | {percent:.0f}% | {detail}')
                        self.overall.set((count+percent/100)*100/max(1,self.total_running))
                elif event=='batch_progress':
                    self.completed_running=message[1]
                    self.overall.set(self.completed_running*100/max(1,self.total_running))
                elif event=='finished':
                    self._toggle_buttons(False)
                    counts={}
                    for row in self.entries.values():counts[row.state]=counts.get(row.state,0)+1
                    self.summary.set('Finished  |  '+', '.join(f'{status}: {n}' for status,n in counts.items()))
                    self._log('Batch finished. '+self.summary.get())
        except queue.Empty:pass
        if self._closing and not self.running and (not self.worker or not self.worker.is_alive()):
            self.destroy();return
        self.after(100,self._pump_events)

    def open_result(self,_event=None):
        selected=self.tree.selection()
        if not selected: return
        row=self.entries.get(selected[0]);target=Path(row.output) if row and row.output else None
        if target and target.is_file():
            self._open_path(target)

    def open_destination(self):
        selected=self.tree.selection()
        if selected and (entry:=self.entries.get(selected[0])):
            dest=Path(entry.output).parent if entry.output else entry.source.parent/'Converted' if self.source_output_var.get() else Path(self.output_var.get())
        else:
            dest=Path(self.output_var.get())
            if self.source_output_var.get() and self.entries:dest=next(iter(self.entries.values())).source.parent/'Converted'
        dest.mkdir(parents=True,exist_ok=True)
        self._open_path(dest)

    def _open_path(self,path):
        try:
            if sys.platform=='win32':os.startfile(str(path))
            elif sys.platform=='darwin':subprocess.Popen(['open',str(path)])
            else:subprocess.Popen(['xdg-open',str(path)])
        except Exception as exc:messagebox.showerror('Cannot open',str(exc))

    def close_app(self):
        if not self.running:
            self.destroy();return
        if messagebox.askyesno('Cancel and exit?',
            'A conversion is running. Cancel it and exit once the active process stops?\nOriginal and existing output files will be preserved.'):
            self._closing=True
            self.stop_conversion()

if __name__ == '__main__':
    MediaStudio().mainloop()
