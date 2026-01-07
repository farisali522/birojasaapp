import threading
from django.core.mail import EmailMessage
from django.conf import settings
from django.template.loader import get_template
from io import BytesIO
try: from xhtml2pdf import pisa
except ImportError: pisa = None

import os
from django.conf import settings
from django.contrib.staticfiles import finders

def link_callback(uri, rel):
    """
    Convert HTML URIs to absolute system paths so xhtml2pdf can verify resources
    """
    result = finders.find(uri)
    if result:
        if not isinstance(result, (list, tuple)):
            result = [result]
        result = list(os.path.realpath(path) for path in result)
        path = result[0]
    else:
        sUrl = settings.STATIC_URL        # Typically /static/
        sRoot = settings.STATIC_ROOT      # Typically /home/userX/project_static/
        mUrl = settings.MEDIA_URL         # Typically /media/
        mRoot = settings.MEDIA_ROOT       # Typically /home/userX/project_media/

        if uri.startswith(mUrl):
            path = os.path.join(mRoot, uri.replace(mUrl, ""))
        elif uri.startswith(sUrl):
            path = os.path.join(sRoot, uri.replace(sUrl, ""))
        else:
            return uri

    # make sure that file exists
    if not os.path.isfile(path):
            raise Exception(f'media URI must start with {sUrl} or {mUrl}')
    return path

# --- FUNGSI GENERATE PDF ---
def render_to_pdf(template_src, context_dict={}):
    """
    Mengubah Template HTML menjadi File PDF (Bytes)
    """
    if pisa is None:
        print("❌ ERROR: xhtml2pdf (pisa) is None. Library might not be installed correctly in this process.")
        return None

    try:
        template = get_template(template_src)
        html  = template.render(context_dict)
        result = BytesIO()
        
        # Konversi HTML ke PDF dengan link_callback
        pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result, link_callback=link_callback)
        
        if not pdf.err:
            return result.getvalue() # Mengembalikan file PDF mentah
        else:
            print(f"❌ PDF CONVERSION ERROR: {pdf.err}")
            return None
    except Exception as e:
        print(f"❌ PDF EXCEPTION: {str(e)}")
        return None

# --- CLASS EMAIL THREAD (DENGAN ATTACHMENT) ---
class EmailThread(threading.Thread):
    def __init__(self, subject, html_content, recipient_list, pdf_file=None, pdf_filename="invoice.pdf"):
        self.subject = subject
        self.recipient_list = recipient_list
        self.html_content = html_content
        self.pdf_file = pdf_file
        self.pdf_filename = pdf_filename
        threading.Thread.__init__(self)

    def run(self):
        try:
            # Kita pakai EmailMessage agar bisa attach file
            email = EmailMessage(
                subject=self.subject,
                body=self.html_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=self.recipient_list
            )
            email.content_subtype = "html" # Set isi email jadi HTML
            
            # Jika ada file PDF, lampirkan!
            if self.pdf_file:
                email.attach(self.pdf_filename, self.pdf_file, 'application/pdf')
            
            email.send()
            print(f"✅ Email + PDF terkirim ke {self.recipient_list}")
            
        except Exception as e:
            print(f"❌ Gagal kirim email: {e}")

# --- FUNGSI PEMICU UTAMA ---
def kirim_notifikasi_email(subjek, pesan_html, email_tujuan, pdf_data=None, pdf_name="dokumen.pdf"):
    """
    Helper praktis. Parameter pdf_data opsional.
    """
    if not isinstance(email_tujuan, list):
        email_tujuan = [email_tujuan]

    # Jalankan di background
    EmailThread(subjek, pesan_html, email_tujuan, pdf_data, pdf_name).start()