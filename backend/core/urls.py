from django.urls import path
from . import views

urlpatterns = [
    path('admin/', views.faculty_dashboard_view, name='faculty_dashboard'),
    path('student/', views.student_dashboard_view, name='student_dashboard'),
    path('fetch_data/', views.fetch_data, name='fetch_data'),
]