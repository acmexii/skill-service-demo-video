"""Read credentials from explicit project-root .env; never print secret values."""
import argparse, base64, hashlib, json, os, re, urllib.error, urllib.request
from pathlib import Path

def read_env(root):
    env_file = Path(root).resolve() / '.env'
    if not env_file.is_file():
        raise RuntimeError('Project root .env missing; pass --root explicitly.')
    values = {}
    for line in env_file.read_text(encoding='utf-8-sig').splitlines():
        match = re.match(r'^\s*(?:export\s+)?([A-Za-z_][A-Za-z_0-9]*)\s*=\s*(.*?)\s*$', line)
        if not match:
            continue
        name, value = match.groups()
        if len(value) >= 2 and value[0] in '\"\'' and value[-1] == value[0]:
            value = value[1:-1]
        else:
            value = re.split(r'\s+#', value, maxsplit=1)[0].strip()
        values[name] = value
    key = values.get('ELEVENLABS_API_KEY', '').strip()
    voice = (values.get('ELEVENLABS_VOICE_ID') or values.get('VOICE_ID') or '').strip()
    if not key or not voice:
        raise RuntimeError('Root .env requires ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID or VOICE_ID.')
    if not re.fullmatch(r'[A-Za-z0-9_-]+', voice):
        raise RuntimeError('Voice ID format invalid; remove surrounding URL or trailing punctuation.')
    return key, voice

def generate(root, text_file, prefix):
    key, voice = read_env(root)
    text = Path(text_file).read_text(encoding='utf-8-sig').strip()
    if not 1 <= len(text) <= 5000:
        raise RuntimeError('Narration must contain 1 to 5000 characters.')
    prefix = Path(prefix).resolve()
    audio = prefix.with_suffix('.mp3')
    alignment = prefix.with_suffix('.alignment.json')
    fingerprint = hashlib.sha256(text.encode()).hexdigest()
    if audio.exists() and alignment.exists():
        meta = json.loads(alignment.read_text(encoding='utf-8'))
        if meta.get('voice_id') == voice and meta.get('text_sha256') == fingerprint:
            print('Reusing matching narration and voice.')
            return
        raise RuntimeError('Existing audio differs from narration or voice; use a new output prefix.')
    if audio.exists() or alignment.exists():
        raise RuntimeError('Partial output exists; inspect it before generating again.')
    body = {'text': text, 'model_id': 'eleven_multilingual_v2', 'voice_settings': {'stability': .5, 'similarity_boost': .75, 'style': .1, 'use_speaker_boost': True}}
    request = urllib.request.Request(f'https://api.elevenlabs.io/v1/text-to-speech/{voice}/with-timestamps?output_format=mp3_44100_128', data=json.dumps(body).encode(), headers={'xi-api-key': key, 'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            data = json.load(response)
    except urllib.error.HTTPError as error:
        raise RuntimeError(f'ElevenLabs HTTP {error.code}; no automatic retry, no voice substitution.') from None
    except urllib.error.URLError:
        raise RuntimeError('ElevenLabs connection failed; no automatic retry.') from None
    timing = data.get('alignment') or data.get('normalized_alignment')
    if not timing or not timing.get('characters'):
        raise RuntimeError('Missing character timing; do not resubmit automatically.')
    raw = base64.b64decode(data['audio_base64'], validate=True)
    if not raw:
        raise RuntimeError('Empty audio result.')
    prefix.parent.mkdir(parents=True, exist_ok=True)
    audio.write_bytes(raw)
    alignment.write_text(json.dumps({'voice_id': voice, 'text_sha256': fingerprint, 'model_id': body['model_id'], 'alignment': timing}, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Saved narration and character timing.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--text-file', type=Path)
    parser.add_argument('--out-prefix', type=Path)
    args = parser.parse_args()
    try:
        if args.check:
            read_env(args.root)
            print('Root .env credential and voice configured; offline check only.')
        elif args.text_file and args.out_prefix:
            generate(args.root, args.text_file, args.out_prefix)
        else:
            parser.error('--text-file and --out-prefix required for synthesis')
    except (RuntimeError, OSError, ValueError, KeyError) as error:
        parser.exit(1, str(error) + '\n')
