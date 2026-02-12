from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth import get_user_model

from .forms import RecepcaoGerarSenhaForm
from .services import (
    criar_ficha_por_cpf, chamar_para_triagem, 
    finalizar_triagem, rotear_para_medico, chamar_para_medico
)
from .models import FichaAtendimento

User = get_user_model()

# --- 1. RECEPÇÃO (Entrada) ---
@require_http_methods(["GET", "POST"])
def recepcao_gerar_senha(request):
    senha_gerada = None
    if request.method == "POST":
        form = RecepcaoGerarSenhaForm(request.POST)
        if form.is_valid():
            result = criar_ficha_por_cpf(**form.cleaned_data)
            senha_gerada = result.ficha.codigo
            messages.success(request, f"Senha {senha_gerada} gerada!")
            form = RecepcaoGerarSenhaForm()
    else:
        form = RecepcaoGerarSenhaForm()
    return render(request, "attendance/recepcao_gerar_senha.html", {"form": form, "senha_gerada": senha_gerada})

# --- 2. TRIAGEM (Enfermeiro) ---
def triagem_lista(request):
    """Fila de quem acabou de chegar (TV 01)."""
    aguardando = FichaAtendimento.objects.filter(status=FichaAtendimento.Status.CHEGADA).order_by('criado_em')
    em_triagem = FichaAtendimento.objects.filter(status__in=[FichaAtendimento.Status.CHAMADO_TRIAGEM, FichaAtendimento.Status.EM_TRIAGEM])
    return render(request, "attendance/triagem_lista.html", {"aguardando": aguardando, "em_triagem": em_triagem})

def triagem_chamar(request, ficha_id):
    """Ação do botão 'Chamar' no PC do Enfermeiro."""
    chamar_para_triagem(ficha_id)
    return redirect('attendance:triagem_lista')

@require_http_methods(["GET", "POST"])
def triagem_finalizar(request, ficha_id):
    """Tela onde o enfermeiro digita os sinais vitais (Mata o Papel)."""
    ficha = get_object_or_404(FichaAtendimento, id=ficha_id)
    if request.method == "POST":
        dados = {
            'prioridade': request.POST.get('prioridade'),
            'pa_sistolica': request.POST.get('pa_sistolica'),
            'pa_diastolica': request.POST.get('pa_diastolica'),
            'temperatura': request.POST.get('temperatura'),
            'frequencia_cardiaca': request.POST.get('frequencia_cardiaca'),
            'observacoes_triagem': request.POST.get('observacoes_triagem'),
        }
        finalizar_triagem(ficha_id, dados)
        messages.success(request, f"Triagem de {ficha.paciente.nome} finalizada.")
        return redirect('attendance:triagem_lista')
    return render(request, "attendance/triagem_form.html", {"ficha": ficha})

# --- 3. LANÇAMENTO (Segundo PC - O Roteador) ---
def lancamento_lista(request):
    """Exibe quem já foi triado e aguarda definição de médico."""
    triados = FichaAtendimento.objects.filter(status=FichaAtendimento.Status.TRIADO).order_by('-prioridade', 'criado_em')
    medicos = User.objects.filter(groups__name='Medicos') # Ajuste conforme seu sistema de perfis
    return render(request, "attendance/lancamento_lista.html", {"triados": triados, "medicos": medicos})

@require_http_methods(["POST"])
def lancamento_rotear(request, ficha_id):
    """Ação do Segundo PC: Define médico e consultório."""
    medico_id = request.POST.get('medico_id')
    local = request.POST.get('local') # Ex: "Consultório 02"
    rotear_para_medico(ficha_id, medico_id, local)
    return redirect('attendance:lancamento_lista')

# --- 4. PAINÉIS (TVs) ---

def painel_recepcao(request):
    """TV 01: Foco em Senhas e Salas de Triagem."""
    # Buscamos quem está sendo chamado ou quem está em atendimento (para não deixar a tela vazia)
    chamado = FichaAtendimento.objects.filter(
        status__in=[FichaAtendimento.Status.CHAMADO_TRIAGEM, FichaAtendimento.Status.EM_TRIAGEM]
    ).order_by('-chamado_em').first()
    
    # Próximas senhas que ainda não foram chamadas
    proximos = FichaAtendimento.objects.filter(
        status=FichaAtendimento.Status.CHEGADA
    ).order_by('criado_em')[:5]
    
    return render(request, "attendance/painel_recepcao.html", {
        "atual": chamado, 
        "proximos": proximos
    })

def painel_medico(request):
    """TV 02: Foco em Nomes e Consultórios Médicos."""
    # Buscamos o último chamado pelo médico
    chamado = FichaAtendimento.objects.filter(
        status=FichaAtendimento.Status.CHAMADO_MEDICO
    ).order_by('-chamado_em').first()
    
    # Fila de espera: quem já foi roteado para um médico mas ainda não foi chamado para entrar
    fila_corredor = FichaAtendimento.objects.filter(
        status=FichaAtendimento.Status.AGUARDANDO_MEDICO
    ).order_by('-prioridade', 'criado_em')[:8]
    
    return render(request, "attendance/painel_medico.html", {
        "atual": chamado, 
        "fila": fila_corredor
    })

def medico_atendimento(request):
    # Filtra pacientes que foram roteados especificamente para este médico e estão esperando
    fila_espera = FichaAtendimento.objects.filter(
        medico=request.user,
        status=FichaAtendimento.Status.AGUARDANDO_MEDICO
    ).order_by('-prioridade', 'criado_em')

    # Busca se já existe alguém em atendimento neste consultório
    paciente_atendimento = FichaAtendimento.objects.filter(
        medico=request.user,
        status__in=[FichaAtendimento.Status.CHAMADO_MEDICO, FichaAtendimento.Status.EM_CONSULTA]
    ).first()

    return render(request, "attendance/medico_atendimento.html", {
        "fila_espera": fila_espera,
        "paciente_atendimento": paciente_atendimento,
        "local_atual": "Consultório 01" # Isso pode vir de um perfil do usuário depois
    })

def chamar_paciente_medico(request, ficha_id):
    """Gatilha a chamada na TV 02"""
    ficha = get_object_or_404(FichaAtendimento, id=ficha_id)
    # Chama o serviço que muda o status e define o horário da chamada para o som tocar
    chamar_para_medico(ficha_id) 
    messages.success(request, f"Chamando {ficha.paciente.nome} no painel.")
    return redirect('attendance:medico_atendimento')