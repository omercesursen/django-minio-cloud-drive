from django.contrib import admin
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from files.views import RegisterView, FileListCreateView, FileDetailView, FileShareView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/register/', RegisterView.as_view(), name='register'),
    path('api/login/', TokenObtainPairView.as_view(), name='login'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    path('api/files/', FileListCreateView.as_view(), name='file-list-create'),
    path('api/files/<int:pk>/', FileDetailView.as_view(), name='file-detail'),

    
    path('api/files/<int:pk>/share/', FileShareView.as_view(), name='file-share'),
]
