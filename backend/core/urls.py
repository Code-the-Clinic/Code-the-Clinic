from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('dashboard/admin/', views.faculty_dashboard_view, name='faculty_dashboard'),
    path('dashboard/student/', views.student_dashboard_view, name='student_dashboard'),
    path('dashboard/fetch_data/', views.fetch_data, name='fetch_data'),
]