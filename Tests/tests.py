import os
import unittest
from io import BytesIO

import sys
import zlib

from PyPDF2 import PdfFileReader, PdfFileWriter
# Configure path environment
from PyPDF2.filters import decompress

TESTS_ROOT = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.dirname(TESTS_ROOT)
RESOURCE_ROOT = os.path.join(PROJECT_ROOT, 'Resources')

sys.path.append(PROJECT_ROOT)


class PdfReaderTestCases(unittest.TestCase):

    def test_PdfReaderFileLoad(self):
        '''
        Test loading and parsing of a file. Extract text of the file and compare to expected
        textual output. Expected outcome: file loads, text matches expected.
        '''

        with open(os.path.join(RESOURCE_ROOT, 'crazyones.pdf'), 'rb') as inputfile:
            # Load PDF file from file
            ipdf = PdfFileReader(inputfile)
            ipdf_p1 = ipdf.getPage(0)

            # Retrieve the text of the PDF
            pdftext_file = open(os.path.join(RESOURCE_ROOT, 'crazyones.txt'), 'rb')
            pdftext = pdftext_file.read()
            ipdf_p1_text = ipdf_p1.extractText().replace('\n', '')

            # Compare the text of the PDF to a known source
            self.assertEqual(ipdf_p1_text.encode('utf-8', errors='ignore'), pdftext,
                             msg='PDF extracted text differs from expected value.\n\nExpected:\n\n%r\n\nExtracted:\n\n%r\n\n'
                                 % (pdftext, ipdf_p1_text.encode('utf-8', errors='ignore')))


class AddJsTestCase(unittest.TestCase):

    def setUp(self):
        ipdf = PdfFileReader(os.path.join(RESOURCE_ROOT, 'crazyones.pdf'))
        self.pdf_file_writer = PdfFileWriter()
        self.pdf_file_writer.appendPagesFromReader(ipdf)

    def test_add(self):
        self.pdf_file_writer.addJS("this.print({bUI:true,bSilent:false,bShrinkToFit:true});")

        self.assertIn('/Names', self.pdf_file_writer._root_object,
                      "addJS should add a name catalog in the root object.")
        self.assertIn('/JavaScript', self.pdf_file_writer._root_object['/Names'],
                      "addJS should add a JavaScript name tree under the name catalog.")
        self.assertIn('/OpenAction', self.pdf_file_writer._root_object,
                      "addJS should add an OpenAction to the catalog.")

    def test_overwrite(self):
        self.pdf_file_writer.addJS("this.print({bUI:true,bSilent:false,bShrinkToFit:true});")
        first_js = self.get_javascript_name()

        self.pdf_file_writer.addJS("this.print({bUI:true,bSilent:false,bShrinkToFit:true});")
        second_js = self.get_javascript_name()

        self.assertNotEqual(first_js, second_js, "addJS should overwrite the previous script in the catalog.")

    def get_javascript_name(self):
        self.assertIn('/Names', self.pdf_file_writer._root_object)
        self.assertIn('/JavaScript', self.pdf_file_writer._root_object['/Names'])
        self.assertIn('/Names', self.pdf_file_writer._root_object['/Names']['/JavaScript'])
        return self.pdf_file_writer._root_object['/Names']['/JavaScript']['/Names'][0]


class TaillessZlibDataTestCase(unittest.TestCase):
    """
    Tests decompression of partial data.
    """
    test_value = b'x\x9c\xe2\n\xe4\x02\x00\x00\x00\xff\xff'
    test_output = b'\nQ\n'

    def test_zlib_success(self):
        self.assertEqual(self.test_output, zlib.decompressobj().decompress(self.test_value))

    def test_zlib_error(self):
        with self.assertRaises(Exception):
            zlib.decompress(self.test_value)

    def test_decompress_success(self):
        self.assertEqual(self.test_output, decompress(self.test_value))


class IndexRebuildTestCase(unittest.TestCase):
    """
    Tests parsing and building document index with invalid or missing xref table.
    """
    test_stream = b'%PDF-1.5\r\n%\xc7\xc8\xc9\xca\r\n' \
                  b'1 0 obj\r\n<</Title(title)/ModDate()>>\r\nendobj\r\n' \
                  b'2 0 obj\r\n<</Type/Catalog/Pages 3 0 R\r\nendobj\r\n' \
                  b'trailer\r\n<<\t/Size 22/Info 1 0 R/Root 2 0 R>>\r\n' \
                  b'startxref\r\n57460\r\n%%EOF\r\n'  # note invalid xref offset

    def test_build_index(self):
        input_stream = BytesIO(self.test_stream)
        ipdf = PdfFileReader(input_stream)

        self.assertIn(0, ipdf.xref)
        self.assertEqual(17, ipdf.xref[0][1])
        self.assertEqual(63, ipdf.xref[0][2])
