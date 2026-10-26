"""Offline credential routing and synthesis response tests; never calls a paid API."""
import base64, contextlib, io, json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import tts

class ConfigTests(unittest.TestCase):
    def test_explicit_root_and_voice_alias(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'.env').write_text('ELEVENLABS_API_KEY="local-test-value"\nVOICE_ID=LocalVoice42\n',encoding='utf-8')
            with patch.dict('os.environ',{'ELEVENLABS_API_KEY':'wrong-inherited-value','VOICE_ID':'WrongVoice'}):
                self.assertEqual(tts.read_env(root),('local-test-value','LocalVoice42'))
            (root/'.env').write_text('ELEVENLABS_API_KEY=local-test-value\n',encoding='utf-8')
            with self.assertRaises(RuntimeError):tts.read_env(root)

    def test_timestamp_response_and_matching_cache(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'.env').write_text('ELEVENLABS_API_KEY=local-test-value\nELEVENLABS_VOICE_ID=LocalVoice42\n',encoding='utf-8')
            text=root/'line.txt';text.write_text('문서',encoding='utf-8');prefix=root/'audio'/'scene'
            payload={'audio_base64':base64.b64encode(b'local fixture').decode(),'alignment':{'characters':['문','서'],'character_start_times_seconds':[0,.2],'character_end_times_seconds':[.2,.4]}}
            def response(req,timeout):
                self.assertIn('/LocalVoice42/with-timestamps',req.full_url)
                return io.BytesIO(json.dumps(payload).encode())
            output=io.StringIO()
            with contextlib.redirect_stdout(output),patch('urllib.request.urlopen',side_effect=response) as call:
                tts.generate(root,text,prefix);tts.generate(root,text,prefix)
                self.assertEqual(call.call_count,1)
            self.assertNotIn('local-test-value',output.getvalue())
            self.assertEqual(json.loads(prefix.with_suffix('.alignment.json').read_text())['voice_id'],'LocalVoice42')

if __name__=='__main__':unittest.main()
