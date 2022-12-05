from django.urls import path

from . import views

# for reading static files
from django.conf import settings
from django.urls import include
from django.conf.urls.static import static

urlpatterns = [
    # path('', views.ListFlower.as_view()),
    path('', views.home, name='home'),

    path('flowers/', views.FlowerList.as_view(), name='flowers'),
    path('flowers/<slug:slug>', views.flower_detail, name='flower_detail'),

    path('bouquets/', views.bouquet_list, name='bouquets'),
    path('bouquets/<slug:slug>', views.bouquet_detail, name='bouquet_detail'),

    path('contacts', views.contacts, name='contacts'),


    # for api
    path('api/v1/flower-list/', views.FlowerListView.as_view()),
    path('api/v1/gallery-list/', views.FlowerGalleryView.as_view()),
    path('api/v1/flower-list/<int:pk>/', views.FlowerDetailView.as_view()),

]

# узнать, что такое as_view()