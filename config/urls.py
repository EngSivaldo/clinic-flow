from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render # Importamos o render para a home

# Criamos uma view simples diretamente aqui para a Home
def home_view(request):
    return render(request, 'home.html')

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Rota da Página Inicial (Raiz)
    path('', home_view, name='home'),
    
    # Inclui as rotas do seu app de atendimento
    path('', include('attendance.urls')), 
]