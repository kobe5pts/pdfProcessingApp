
from django.db import models
from .custom_storages import UploadsStorage

class PDFDocument(models.Model):
    file = models.FileField(storage=UploadsStorage(), upload_to='')
    uploaded_at = models.DateTimeField(auto_now_add=True)

class Coordinate(models.Model):
    document = models.ForeignKey(PDFDocument, on_delete=models.CASCADE, related_name='coordinates')
    page = models.IntegerField()
    x0 = models.FloatField()
    y0 = models.FloatField()
    x1 = models.FloatField()
    y1 = models.FloatField()
    keyword = models.CharField(max_length=100)
