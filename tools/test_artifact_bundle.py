import io
import os
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from artifact_bundle import pack, unpack


class ArtifactBundleTests(unittest.TestCase):
    def test_directory_and_globs_keep_expected_root(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'proj').mkdir()
            (root / 'proj' / 'listen_results_0.json').write_text('{}')
            (root / 'proj' / 'meta.json').write_text('{"synthetic":true}')
            with patch('artifact_bundle.Path.cwd', return_value=root), patch('artifact_bundle.glob.glob', return_value=[str(root/'proj')]):
                self.assertTrue(pack('proj',root/'bundle.tgz'))
            unpack(root/'bundle.tgz',root/'out')
            self.assertTrue((root/'out'/'meta.json').exists())
            self.assertFalse((root/'out'/'proj').exists())

    def test_traversal_and_links_are_rejected_before_any_extraction(self):
        for name, kind in [('../escape',tarfile.REGTYPE),('/absolute',tarfile.REGTYPE),('link',tarfile.SYMTYPE)]:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as d:
                source=Path(d)/'bad.tgz'
                with tarfile.open(source,'w:gz') as archive:
                    good=tarfile.TarInfo('good'); good.size=1
                    archive.addfile(good,io.BytesIO(b'x'))
                    bad=tarfile.TarInfo(name); bad.type=kind; bad.linkname='../escape'
                    archive.addfile(bad)
                with self.assertRaises(ValueError): unpack(source,Path(d)/'out')
                self.assertFalse((Path(d)/'out'/'good').exists())

    def test_missing_inputs_are_explicit(self):
        with tempfile.TemporaryDirectory() as d:
            with patch('artifact_bundle.glob.glob', return_value=[]):
                self.assertFalse(pack('missing',Path(d)/'x.tgz'))


if __name__ == '__main__':
    unittest.main()
