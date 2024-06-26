from django.contrib import admin
from .models import PDFDocument

# Define an admin class for the PDFDocument model (optional, for customization)
class PDFDocumentAdmin(admin.ModelAdmin):
    list_display = ('id', 'file', 'uploaded_at')  # Display these fields in the admin list view
    search_fields = ('file',)  # Add a search box for the 'file' field
    list_filter = ('uploaded_at',)  # Add a filter sidebar for the 'uploaded_at' field

# Register the model with the admin site
admin.site.register(PDFDocument, PDFDocumentAdmin)
