# C:\Users\flavi\vigilancia_sanitaria\sistema\urls.py

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # ESTA LINHA ABAIXO DEVE ESTAR REMOVIDA OU COMENTADA!
    # path('accounts/', include('django.contrib.auth.urls')),
    path('', include('empresa.urls')), # Ou 'core.urls' se seu app se chama 'core'
]