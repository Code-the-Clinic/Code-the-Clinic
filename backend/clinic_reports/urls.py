from django.urls import path
from . import views

urlpatterns = [
    path('', views.form_view, name='form'),
    path('api/submit/', views.submit_report, name='submit_report'),
    path('api/pie1/', views.pie_chart_by_sport, name='pie_chart_by_sport'),
]
