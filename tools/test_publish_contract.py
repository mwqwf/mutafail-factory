from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class PublishContract(unittest.TestCase):
    def test_unavailable_related_video_field_is_not_assigned_to_owner(self):
        text = (ROOT/'tools/publish_youtube.py').read_text(encoding='utf-8')
        self.assertIn('قيد_واجهة_غير_متاح_API', text)
        self.assertIn('وُضع رابط الفيلم في وصف كل ريلز', text)
        self.assertNotIn('يتبقّى_يدويّاً', text)

if __name__ == '__main__': unittest.main()
