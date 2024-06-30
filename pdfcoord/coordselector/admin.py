from django.contrib import admin
from .models import PDFDocument, Coordinate

# Define an admin class for the PDFDocument model
class PDFDocumentAdmin(admin.ModelAdmin):
    list_display = ('id', 'file', 'uploaded_at')  # Display these fields in the admin list view
    search_fields = ('file',)  # Add a search box for the 'file' field
    list_filter = ('uploaded_at',)  # Add a filter sidebar for the 'uploaded_at' field

# Define an admin class for the Coordinate model
# class CoordinateAdmin(admin.ModelAdmin):
#     list_display = ('id', 'document', 'page', 'x0', 'y0', 'x1', 'y1', 'keyword')  # Display these fields in the admin list view
#     search_fields = ('keyword',)  # Add a search box for the 'keyword' field
#     list_filter = ('document', 'page')  # Add a filter sidebar for the 'pdf_document' and 'page' fields

# Register the models with the admin site
admin.site.register(PDFDocument, PDFDocumentAdmin)
# admin.site.register(Coordinate, CoordinateAdmin)
