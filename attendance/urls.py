from django.urls import path
from . import views

app_name = "attendance"

urlpatterns = [
    # --- 1. ESTAÇÃO RECEPÇÃO ---
    path("recepcao/", views.recepcao_gerar_senha, name="recepcao_gerar_senha"),

    # --- 2. ESTAÇÃO TRIAGEM (Enfermeiro) ---
    path('triagem/', views.triagem_lista, name='triagem_lista'),
    path('triagem/chamar/<int:ficha_id>/', views.triagem_chamar, name='triagem_chamar'),
    path('triagem/finalizar/<int:ficha_id>/', views.triagem_finalizar, name='triagem_finalizar'),

    # --- 3. ESTAÇÃO LANÇAMENTO (Segundo PC - Corredor) ---
    path('lancamento/', views.lancamento_lista, name='lancamento_lista'),
    path('lancamento/rotear/<int:ficha_id>/', views.lancamento_rotear, name='lancamento_rotear'),

    # --- 4. PAINÉIS (TVS) ---
    # TV 01: Fica na Recepção/Triagem
    path('painel/recepcao/', views.painel_recepcao, name='painel_recepcao'),
    # TV 02: Fica no Corredor dos Consultórios
    path('painel/medico/', views.painel_medico, name='painel_medico'),
]