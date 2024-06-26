from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('upload_pdf/', views.upload_pdf, name='upload_pdf'),
    path('select_coords/<int:pdf_id>/', views.select_coords, name='select_coords'),
    path('select_coords/<int:pdf_id>/<int:page_number>/', views.select_coords, name='select_coords_page'),
    path('submit_coordinates/<int:pdf_id>/', views.submit_coordinates, name='submit_coordinates'),
]
