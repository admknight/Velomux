"""Command line companion (also useful for automated batch jobs)."""
import argparse
import sys
from pathlib import Path
from engine import PRESETS, PRESET_MAP, SUPPORTED_SUFFIXES, Options, convert

def main():
    parser=argparse.ArgumentParser(description='Velomux batch conversion')
    parser.add_argument('input',type=Path,help='Input file or folder')
    parser.add_argument('--list-presets',action='store_true',help='List available presets and exit')
    parser.add_argument('--preset',help='Preset name (quoted as shown by --list-presets)')
    parser.add_argument('--output',type=Path,help='Output directory (default: source/Converted)')
    parser.add_argument('--recursive',action='store_true',help='Include subfolders')
    parser.add_argument('--collision',choices=['repair','overwrite','skip','rename'],default='repair')
    parser.add_argument('--full-decode',action='store_true',help='Slow deep validation')
    parser.add_argument('--trim-start',type=float,default=0)
    parser.add_argument('--trim-end',type=float,default=0)
    parser.add_argument('--speed',type=float,default=1.0)
    parser.add_argument('--quality',type=int,default=23,help='Video CRF')
    parser.add_argument('--image-quality',type=int,default=90)
    parser.add_argument('--normalize',action='store_true',help='Audio loudness normalization')
    args=parser.parse_args()
    if args.list_presets:
        for p in PRESETS:print(f'{p.group:<6} | {p.name}')
        return 0
    if not args.preset or args.preset not in PRESET_MAP:
        parser.error('Choose a valid --preset; use --list-presets to see options.')
    inputpath=args.input.expanduser()
    if inputpath.is_file(): files=[inputpath]
    elif inputpath.is_dir():
        files=(inputpath.rglob('*') if args.recursive else inputpath.iterdir())
        files=[p for p in files if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES
               and 'converted' not in (segment.lower() for segment in p.relative_to(inputpath).parts[:-1])]
    else:
        parser.error('Input does not exist.')
    opt=Options(collision=args.collision,decode_check=args.full_decode,trim_start=args.trim_start,
                trim_end=args.trim_end,media_speed=args.speed,quality=args.quality,
                image_quality=args.image_quality,audio_normalize=args.normalize)
    failed=0
    for i,path in enumerate(files,1):
        folder=args.output or path.parent/'Converted'
        print(f'[{i}/{len(files)}] {path.name} -> {args.preset}',flush=True)
        result=convert(path,folder,args.preset,opt)
        print(f'  {result.status.upper()}: {result.output or result.detail}',flush=True)
        if result.status=='failed':failed+=1
    print(f'Finished: {len(files)} file(s), {failed} failed')
    return 1 if failed else 0

if __name__ == '__main__':sys.exit(main())
