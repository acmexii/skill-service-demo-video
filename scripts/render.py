"""Render real recordings with synchronized zoom, focus masks, callouts and voice."""
import argparse, json, math, os, re, shutil, subprocess, wave
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def ffmpeg():
    found = os.environ.get('FFMPEG') or shutil.which('ffmpeg')
    if found:
        return found
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        raise RuntimeError('Install ffmpeg or set FFMPEG to its executable.') from None

def run(ff, args, capture=False):
    result = subprocess.run([ff, '-hide_banner', '-y'] + list(map(str, args)), capture_output=True, encoding='utf-8', errors='replace')
    if result.returncode:
        raise RuntimeError(result.stderr[-2500:])
    return result.stderr if capture else None

def duration(ff, filename):
    result = subprocess.run([ff, '-i', str(filename)], capture_output=True, encoding='utf-8', errors='replace')
    m = re.search(r'Duration: (\d+):(\d+):([\d.]+)', result.stderr)
    if not m:
        raise RuntimeError('Cannot read media duration: ' + str(filename))
    return int(m[1])*3600 + int(m[2])*60 + float(m[3])

def font(size):
    candidates = [os.environ.get('DEMO_FONT'), 'C:/Windows/Fonts/malgun.ttf', '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc']
    for file in candidates:
        if file and Path(file).is_file():
            return ImageFont.truetype(file, size)
    raise RuntimeError('Set DEMO_FONT to a font containing the narration language.')

def wrap(text, face, draw, limit=1580):
    lines, current = [], ''
    for char in text:
        if char == '\n':
            lines.append(current); current = ''; continue
        if draw.textlength(current+char, font=face) > limit:
            lines.append(current); current = char
        else:
            current += char
    if current:
        lines.append(current)
    if len(lines) > 2:
        raise RuntimeError('Caption/callout exceeds two lines; shorten the narration segment.')
    return lines

def stamp(t):
    ms = round(t*1000)
    return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'

def render(recording, out, requested=None):
    ff = ffmpeg(); out = Path(out).resolve(); out.mkdir(parents=True, exist_ok=True)
    meta = json.loads(Path(recording).read_text(encoding='utf-8-sig'))
    root = Path(recording).resolve().parent
    scenes = meta['scenes']; clips = []; audio_files = []; subs = []; cursor = 0
    storyboard = []
    for idx, scene in enumerate(scenes):
        parts = scene['parts']; raw_length = sum(x['end']-x['start'] for x in parts)
        length = float(scene.get('duration', raw_length))
        if length <= 0 or length < raw_length - .08:
            raise RuntimeError('Scene duration cannot speed up recorded interaction; shorten actions or rerecord.')
        assembled=[]
        for part_index, part in enumerate(parts):
            src=Path(part['file']); src=src if src.is_absolute() else root/src
            offset=max(0,duration(ff,src)-part['pageElapsed'])
            partfile=out/f'part-{idx}-{part_index}.mp4'
            run(ff,['-ss',offset+part['start'],'-i',src,'-t',part['end']-part['start'],'-vf','fps=30,setsar=1','-an','-c:v','libx264','-preset','fast','-crf','18',partfile])
            assembled.append(partfile)
        listing=out/f'parts-{idx}.txt'
        listing.write_text(''.join("file '"+str(p).replace('\\','/').replace("'","'\\''")+"'\n" for p in assembled),encoding='utf-8')
        raw=out/f'scene-{idx}-raw.mp4'
        run(ff,['-f','concat','-safe','0','-i',listing,'-c','copy',raw])
        focus=scene.get('focus'); zoom=float(scene.get('zoom',1)); zoom_start=float(scene.get('zoomStart',max(0,raw_length-float(scene.get('holdMs',1800))/1000)))
        zoom_end=float(scene.get('zoomEnd',length))
        if not 1 <= zoom <= 1.6 or zoom_start<0 or zoom_end>length or zoom_end<=zoom_start:
            raise RuntimeError('Invalid zoom interval or magnitude.')
        if zoom>1 and not focus:
            raise RuntimeError('Zoom requires recorded focusSelector.')
        image=Image.new('RGBA',(1920,1080),(0,0,0,0)); draw=ImageDraw.Draw(image);union=None
        if focus:
            box=[focus['x']*1920,focus['y']*1080,(focus['x']+focus['w'])*1920,(focus['y']+focus['h'])*1080]
            union=list(box)
            if scene.get('spotlight',True):
                draw.rectangle((0,0,1920,1080),fill=(0,0,0,105));draw.rounded_rectangle(box,radius=12,fill=(0,0,0,0))
                draw.rounded_rectangle(box,radius=12,outline='#9060e3',width=4)
            if scene.get('callout'):
                # Choose the larger free horizontal region; fail rather than hide UI.
                free_right=1920-box[2];free_left=box[0]
                width=min(650,max(free_left,free_right)-60)
                if width<300: raise RuntimeError('No room for callout outside focus; choose another focus or omit callout.')
                x=box[2]+30 if free_right>=free_left else 30
                y=max(80,min(700,(box[1]+box[3])/2-55));face=font(30)
                lines=wrap(scene['callout'],face,draw,width-40);h=30+len(lines)*44
                draw.rounded_rectangle((x,y,x+width,y+h),radius=14,fill='#7950c5')
                start=(box[2],(box[1]+box[3])/2) if free_right>=free_left else (box[0],(box[1]+box[3])/2)
                target=(x,y+h/2) if free_right>=free_left else (x+width,y+h/2)
                draw.line([start,target],fill='#a073f4',width=4);draw.ellipse((start[0]-6,start[1]-6,start[0]+6,start[1]+6),fill='#a073f4')
                for n,line in enumerate(lines): draw.text((x+20,y+15+n*44),line,font=face,fill='white')
                union=[min(box[0],x),min(box[1],y),max(box[2],x+width),max(box[3],y+h)]
        mask=out/f'focus-{idx}.png';image.save(mask)
        # Overlay BEFORE crop/zoom so content, cursor, ring and callout transform together.
        ramp=min(.6,(zoom_end-zoom_start)/2)
        t='on/30';u=f'min(max(({t}-{zoom_start})/{ramp},0),1)';v=f'min(max(({zoom_end}-{t})/{ramp},0),1)'
        eased=f'({u}*{u}*(3-2*{u}))*({v}*{v}*(3-2*{v}))'
        z=f'1+({zoom}-1)*({eased})'
        if union and (union[2]-union[0]>1920/zoom-30 or union[3]-union[1]>1080/zoom-30):
            raise RuntimeError('Zoom would crop focus or callout; lower zoom, reduce focus, or reposition callout.')
        cx=((union[0]+union[2])/2/1920) if union else .5;cy=((union[1]+union[3])/2/1080) if union else .5
        filt=f"[0:v]fps=30,tpad=stop_mode=clone:stop_duration={length},trim=duration={length}[base];[base][1:v]overlay=0:0:enable='between(t,{zoom_start},{zoom_end})'[focus];[focus]scale=3840:2160,zoompan=z='{z}':x='max(0,min(iw-iw/zoom,iw*{cx}-iw/zoom/2))':y='max(0,min(ih-ih/zoom,ih*{cy}-ih/zoom/2))':d=1:s=1920x1080:fps=30,setsar=1[v]"
        visual=out/f'visual-{idx}.mp4'
        run(ff,['-i',raw,'-loop','1','-i',mask,'-filter_complex',filt,'-map','[v]','-t',length,'-an','-c:v','libx264','-preset','fast','-crf','18',visual])
        offset=float(scene.get('audio_offset',.45)); text=scene.get('narration','');audio=scene.get('audio_file');timing=scene.get('alignment_file')
        if text and not audio and not scene.get('silentPreview',False):
            raise RuntimeError('Narration audio missing; provide audio_file or explicitly set silentPreview for a mute draft.')
        audio_out=out/f'audio-{idx}.wav'
        if audio:
            src=Path(audio);src=src if src.is_absolute() else root/src
            if offset<0 or duration(ff,src)+offset>length-.15: raise RuntimeError('Narration does not fit scene; adjust text or duration.')
            run(ff,['-i',src,'-af',f'adelay={round(offset*1000)}:all=1,apad','-t',length,'-ar','48000','-ac','1',audio_out])
            if not timing: raise RuntimeError('Narrated scene requires character alignment file.')
            src=Path(timing);src=src if src.is_absolute() else root/src
            align=json.loads(src.read_text(encoding='utf-8'))['alignment']
            chars=''.join(align['characters'])
            if re.sub(r'\s+','',chars)!=re.sub(r'\s+','',text): raise RuntimeError('Alignment does not match scene narration.')
            start=offset+float(align['character_start_times_seconds'][0]);end=offset+max(align['character_end_times_seconds'])
        else:
            with wave.open(str(audio_out),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(48000);w.writeframes(b'\0\0'*round(length*48000))
            start,end=.2,length-.2
        cap=Image.new('RGBA',(1920,1080),(0,0,0,0));d=ImageDraw.Draw(cap)
        if text:
            face=font(42);lines=wrap(text,face,d);width=max(d.textlength(t,font=face) for t in lines);h=30+len(lines)*56;y=1026-h
            d.rounded_rectangle(((1920-width)/2-30,y,(1920+width)/2+30,1026),radius=15,fill=(20,20,24,238))
            for n,line in enumerate(lines):d.text(((1920-d.textlength(line,font=face))/2,y+12+n*56),line,font=face,fill='white')
            subs.append(f'{len(subs)+1}\n{stamp(cursor+start)} --> {stamp(cursor+end)}\n'+ '\n'.join(lines)+'\n')
        caption=out/f'caption-{idx}.png';cap.save(caption);clip=out/f'clip-{idx}.mp4'
        run(ff,['-i',visual,'-loop','1','-i',caption,'-filter_complex',f"[0:v][1:v]overlay=0:0:enable='between(t,{start},{end})'[v]",'-map','[v]','-t',length,'-an','-c:v','libx264','-preset','fast','-crf','18',clip])
        clips.append(clip);audio_files.append(audio_out);storyboard.append({**scene,'output_start':cursor,'output_duration':length,'caption_start':cursor+start,'caption_end':cursor+end});cursor+=length
    if requested is not None and abs(cursor-requested)>.04: raise RuntimeError('Scene durations do not match requested total.')
    for name,files in [('clips',clips),('audio',audio_files)]:
        (out/f'{name}.txt').write_text(''.join("file '"+str(f).replace('\\','/').replace("'","'\\''")+"'\n" for f in files),encoding='utf-8')
    run(ff,['-f','concat','-safe','0','-i',out/'clips.txt','-f','concat','-safe','0','-i',out/'audio.txt','-map','0:v','-map','1:a','-c:v','copy','-af','loudnorm=I=-16:TP=-1:LRA=11','-c:a','aac','-b:a','192k','-ar','48000','-t',cursor,'-movflags','+faststart',out/'final.mp4'])
    run(ff,['-v','error','-i',out/'final.mp4','-f','null','-'])
    (out/'captions.srt').write_text('\n'.join(subs),encoding='utf-8')
    (out/'storyboard.json').write_text(json.dumps(storyboard,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'narration.txt').write_text('\n\n'.join(s.get('narration','') for s in scenes),encoding='utf-8')
    for i,s in enumerate(storyboard):run(ff,['-ss',s['output_start']+s['output_duration']/2,'-i',out/'final.mp4','-frames:v','1',out/f'review-{i+1}.png'])
    print(json.dumps({'output':str(out/'final.mp4'),'seconds':duration(ff,out/'final.mp4'),'resolution':[1920,1080],'fps':30,'audio_review':'not performed by renderer'}))

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--recording',required=True);p.add_argument('--out',required=True);p.add_argument('--duration',type=float);a=p.parse_args()
    try:render(a.recording,a.out,a.duration)
    except (RuntimeError,ValueError,OSError,KeyError) as e:p.exit(1,str(e)+'\n')
