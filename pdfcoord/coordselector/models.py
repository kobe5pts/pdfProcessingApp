from django.db import models

class PDFDocument(models.Model):
    file = models.FileField(upload_to='pdfs/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

# class Coordinate(models.Model):
#     pdf_document = models.ForeignKey(PDFDocument, related_name='coordinates', on_delete=models.CASCADE, null=True)
#     page = models.IntegerField()
#     x0 = models.FloatField()
#     y0 = models.FloatField()
#     x1 = models.FloatField()
#     y1 = models.FloatField()
#     keyword = models.CharField(max_length=100)
class Coordinate(models.Model):
    document = models.ForeignKey(PDFDocument, on_delete=models.CASCADE, related_name='coordinates')
    page = models.IntegerField()
    x0 = models.FloatField()
    y0 = models.FloatField()
    x1 = models.FloatField()
    y1 = models.FloatField()
    keyword = models.CharField(max_length=100)
