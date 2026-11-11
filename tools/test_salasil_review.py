import io, json, unittest, urllib.error
from unittest.mock import patch
import salasil_review as r

class Response(io.BytesIO):
    def __enter__(self):return self
    def __exit__(self,*a):self.close()

class Tests(unittest.TestCase):
    def test_no_keys(self):
        with self.assertRaises(r.ReviewError):r.Client([])
    def test_uses_one_key_and_caps_output(self):
        c=r.Client(['secret1','secret2'])
        obj={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'{"pass":true}'}]}}],'usageMetadata':{'totalTokenCount':5}}
        with patch.object(r.urllib.request,'urlopen',return_value=Response(json.dumps(obj).encode())) as f,patch.object(r.time,'sleep'):
            self.assertTrue(c.ask([{'text':'production'}])['pass'])
            req=f.call_args[0][0]
            self.assertEqual(req.headers['X-goog-api-key'],'secret1')
            self.assertNotIn('secret',req.full_url)
            self.assertEqual(json.loads(req.data)['generationConfig']['maxOutputTokens'],4096)
    def test_daily_quota_does_not_rotate_or_retry(self):
        c=r.Client(['a','b'])
        e=urllib.error.HTTPError('https://example',429,'limit',{},io.BytesIO(b'PerDay'))
        with patch.object(r.urllib.request,'urlopen',side_effect=e) as f,patch.object(r.time,'sleep'):
            with self.assertRaisesRegex(r.ReviewError,'daily_quota'):c.ask([])
            self.assertEqual(f.call_count,1)
    def test_cap_prevents_request(self):
        c=r.Client(['a']);c.calls=r.MAX_CALLS
        with patch.object(r.urllib.request,'urlopen') as f:
            with self.assertRaisesRegex(r.ReviewError,'call_cap'):c.ask([])
            f.assert_not_called()
    def test_missing_ids_fail(self):
        with self.assertRaises(r.ReviewError):r.check_rows({'results':[{'id':'a'}]},'results',['a','b'])
    def test_duplicate_ids_fail(self):
        with self.assertRaises(r.ReviewError):r.check_rows({'results':[{'id':'a'},{'id':'a'}]},'results',['a','b'])
    def test_incomplete_response_fails(self):
        c=r.Client(['a']);obj={'candidates':[{'finishReason':'MAX_TOKENS','content':{'parts':[{'text':'{}'}]}}]}
        with patch.object(r.urllib.request,'urlopen',return_value=Response(json.dumps(obj).encode())),patch.object(r.time,'sleep'):
            with self.assertRaisesRegex(r.ReviewError,'incomplete'):c.ask([])

if __name__=='__main__':unittest.main()
