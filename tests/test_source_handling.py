import tempfile
from gzip import GzipFile
from unittest import TestCase

from testfixtures import LogCapture

from simpleais import *

fragmented_message_type_8 = ['!AIVDM,3,1,3,A,85NoHR1KfI99t:BHBI3sWpAoS7VHRblW8McQtR3lsFR,0*5A',
                             '!AIVDM,3,2,3,A,ApU6wWmdIeJG7p1uUhk8Tp@SVV6D=sTKh1O4fBvUcaN,0*5E',
                             '!AIVDM,3,3,3,A,j;lM8vfK0,2*34']
message_type_1 = '!ABVDM,1,1,,A,15NaEPPP01oR`R6CC?<j@gvr0<1C,0*1F'

newline = bytes("\n", "ascii")


class TestSourceHandling(TestCase):
    def test_file_source_by_line(self):
        with tempfile.NamedTemporaryFile() as file:
            self.write_sample_data(file)

            sentences = list(lines_from_source(file.name))
            self.assertEqual(5, len(sentences))

    def test_file_source_by_fragment(self):
        with LogCapture() as logs:
            with tempfile.NamedTemporaryFile() as file:
                self.write_sample_data(file)

                fragments = list(fragments_from_source(file.name, log_errors=True))
                self.assertEqual(4, len(fragments))
            logs.check(('root', 'WARNING', 'skipped: "garbage data"'))

    def test_file_source_by_sentence(self):
        with LogCapture() as logs:
            with tempfile.NamedTemporaryFile() as file:
                self.write_sample_data(file)

                sentences = sentences_from_source(file.name, log_errors=True)
                self.assertEqual(8, sentences.__next__().type_id())
                self.assertEqual(1, sentences.__next__().type_id())
                self.assertRaises(StopIteration, sentences.__next__)
            logs.check(('root', 'WARNING', 'skipped: "garbage data"'))

    def test_gzip_source_by_sentence(self):
        with LogCapture() as logs:
            with tempfile.NamedTemporaryFile(suffix='.gz', delete=False) as file:
                self.write_sample_data(file, compress=True)
                file.close()

                sentences = sentences_from_source(file.name, log_errors=True)
                self.assertEqual(8, sentences.__next__().type_id())
                self.assertEqual(1, sentences.__next__().type_id())
                self.assertRaises(StopIteration, sentences.__next__)
                os.unlink(file.name)

            logs.check(('root', 'WARNING', 'skipped: "garbage data"'))

    def test_io_source_by_sentence(self):
        with LogCapture() as logs:
            with tempfile.NamedTemporaryFile() as file:
                self.write_sample_data(file)
                with open(file.name, 'rt') as io:
                    sentences = sentences_from_source(io, log_errors=True)
                    self.assertEqual(8, sentences.__next__().type_id())
                    self.assertEqual(1, sentences.__next__().type_id())
                    self.assertRaises(StopIteration, sentences.__next__)
            logs.check(('root', 'WARNING', 'skipped: "garbage data"'))

    # TODO: figure out how to test serial and url sources effectively

    def write_sample_data(self, file, compress=False):
        if compress:
            file = GzipFile(mode='w', fileobj=file)
        for line in fragmented_message_type_8:
            file.write(bytes(line, "ascii"))
            file.write(newline)
        file.write(bytes("garbage data", "ascii"))
        file.write(newline)
        file.write(bytes(message_type_1, "ascii"))
        file.write(newline)
        file.flush()
