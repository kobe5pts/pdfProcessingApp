from django import forms

class UploadPDFForm(forms.Form):
    pdf_file = forms.FileField(label='Select PDF file', help_text='Please upload a PDF file')
    new_keyword = forms.CharField(label='Enter New Keyword', required=False)
    saved_keyword = forms.CharField(label='Select Previously Saved Keyword', required=False)
    action = forms.ChoiceField(choices=(('upload', 'Upload'), ('process', 'Process PDF')))
