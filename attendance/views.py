from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db.models import Case, When, Value, IntegerField

from .forms import RecepcaoGerarSenhaForm
from .services import (
    criar_ficha_por_cpf, chamar_para_triagem, 
    finalizar_triagem, rotear_para_medico, chamar_para_medico,
    finalizar_atendimento_medico
)
from .models import FichaAtendimento

User = get_user_model()

# --- 1. RECEPÇÃO ---
# --- RECEPÇÃO ---
def recepcao_gerar_senha(request):
    senha_gerada = None
    if request.method == "POST":
        form = RecepcaoGerarSenhaForm(request.POST)
        if form.is_valid():
            # A service deve salvar o status como FichaAtendimento.Status.CHEGADA
            result = criar_ficha_por_cpf(**form.cleaned_data)
            senha_gerada = result.ficha.codigo
            messages.success(request, f"Senha {senha_gerada} gerada!")
            form = RecepcaoGerarSenhaForm()
    else:
        form = RecepcaoGerarSenhaForm()
    return render(request, "attendance/recepcao_gerar_senha.html", {"form": form, "senha_gerada": senha_gerada})

# --- TRIAGEM (A parte que não estava funcionando) ---
def triagem_lista(request):
    # BUSCA O STATUS 'CHEGADA' (O mesmo que a recepção cria)
    aguardando = FichaAtendimento.objects.filter(
        status=FichaAtendimento.Status.CHEGADA
    ).order_by('criado_em')
    
    # BUSCA QUEM ESTÁ SENDO CHAMADO AGORA
    em_triagem = FichaAtendimento.objects.filter(
        status__in=[FichaAtendimento.Status.CHAMADO_TRIAGEM, FichaAtendimento.Status.EM_TRIAGEM]
    ).order_by('-chamado_em')

    return render(request, "attendance/triagem_lista.html", {
        "aguardando": aguardando, 
        "em_triagem": em_triagem
    })
def triagem_chamar(request, ficha_id):
    """Aciona o chamado visual/sonoro na TV 01."""
    chamar_para_triagem(ficha_id)
    return redirect('attendance:triagem_lista')

@login_required
def triagem_finalizar(request, ficha_id):
    ficha = get_object_or_404(FichaAtendimento, id=ficha_id)

    if request.method == "POST":
        # Pegando os dados que vêm do seu HTML
        ficha.pa_sistolica = request.POST.get('pa_sistolica')
        ficha.pa_diastolica = request.POST.get('pa_diastolica')
        ficha.temperatura = request.POST.get('temperatura')
        ficha.frequencia_cardiaca = request.POST.get('frequencia_cardiaca')
        ficha.observacoes_triagem = request.POST.get('observacoes_triagem')
        ficha.prioridade = request.POST.get('prioridade')
        
        # Muda o status para TRIADO para ele aparecer na tela de LANÇAMENTO
        ficha.status = FichaAtendimento.Status.TRIADO
        ficha.triado_em = timezone.now()
        ficha.triado_por = request.user
        
        ficha.save()
        
        messages.success(request, f"Triagem de {ficha.paciente.nome} finalizada com sucesso!")
        return redirect('attendance:triagem_lista')

    return render(request, "attendance/triagem_form.html", {"ficha": ficha})

# --- 3. LANÇAMENTO (Roteamento Corredor) ---
def triagem_lista(request):
    """Garante a exibição de quem acabou de chegar."""
    # O segredo é usar exatamente o Status.CHEGADA
    aguardando = FichaAtendimento.objects.filter(
        status=FichaAtendimento.Status.CHEGADA
    ).order_by('criado_em')
    
    # DEBUG: Ver no terminal quantos pacientes o Django está encontrando
    print(f"DEBUG: Pacientes aguardando triagem: {aguardando.count()}")
    
    em_triagem = FichaAtendimento.objects.filter(
        status__in=[FichaAtendimento.Status.CHAMADO_TRIAGEM, FichaAtendimento.Status.EM_TRIAGEM]
    ).order_by('-chamado_em')
    
    return render(request, "attendance/triagem_lista.html", {
        "aguardando": aguardando, 
        "em_triagem": em_triagem
    })

@require_http_methods(["POST"])
def lancamento_rotear(request, ficha_id):
    """Envia o paciente para a porta de um consultório específico."""
    medico_id = request.POST.get('medico_id')
    local = request.POST.get('local') # O valor que vem do formulário
    
    if not medico_id or not local:
        messages.error(request, "Selecione o médico e a sala.")
        return redirect('attendance:lancamento_lista')

    ficha = get_object_or_404(FichaAtendimento, id=ficha_id)
    medico = get_object_or_404(User, id=medico_id)

    # AJUSTE NOS NOMES DOS CAMPOS (Conforme seu models.py)
    ficha.medico_atendente = medico
    ficha.local_atendimento = local # No model é 'local_atendimento'
    ficha.status = FichaAtendimento.Status.CHAMADO_MEDICO
    ficha.chamado_em = timezone.now()
    ficha.save()

    messages.success(request, f"Paciente {ficha.paciente.nome} encaminhado!")
    return redirect('attendance:lancamento_lista')

# --- 4. MÉDICO ---
def medico_atendimento(request):
    """Interface do Médico: Fila própria e atendimento atual."""
    # Filtra pacientes que foram designados para o médico logado
    fila_espera = FichaAtendimento.objects.filter(
        medico=request.user,
        status=FichaAtendimento.Status.AGUARDANDO_MEDICO
    ).order_by('-prioridade', 'criado_em')

    paciente_atendimento = FichaAtendimento.objects.filter(
        medico=request.user,
        status__in=[FichaAtendimento.Status.CHAMADO_MEDICO, FichaAtendimento.Status.EM_CONSULTA]
    ).first()

    return render(request, "attendance/medico_atendimento.html", {
        "fila_espera": fila_espera,
        "paciente_atendimento": paciente_atendimento
    })

def chamar_paciente_medico(request, ficha_id):
    """Médico chama o paciente do corredor (TV 02 toca som)."""
    chamar_para_medico(ficha_id) 
    return redirect('attendance:medico_atendimento')

def finalizar_atendimento(request, ficha_id):
    """Encerra a consulta e remove o paciente das TVs."""
    finalizar_atendimento_medico(ficha_id)
    messages.success(request, "Atendimento finalizado.")
    return redirect('attendance:medico_atendimento')

# --- 5. PAINÉIS (TVs) ---

def painel_recepcao(request):
    """TV 01 - Recepção e Triagem."""
    chamado = FichaAtendimento.objects.filter(
        status__in=[FichaAtendimento.Status.CHAMADO_TRIAGEM, FichaAtendimento.Status.EM_TRIAGEM]
    ).order_by('-chamado_em').first()
    
    proximos = FichaAtendimento.objects.filter(
        status=FichaAtendimento.Status.CHEGADA
    ).order_by('criado_em')[:5]
    
    return render(request, "attendance/painel_recepcao.html", {
        "atual": chamado, 
        "proximos": proximos
    })
    
def painel_medico(request):
    """TV 02 - Consultórios."""
    # O paciente que o médico ACABOU de chamar (Destaque na TV)
    chamado = FichaAtendimento.objects.filter(
        status=FichaAtendimento.Status.CHAMADO_MEDICO
    ).order_by('-chamado_em').first()
    
    # A fila que fica na lateral da TV (Quem já passou pela triagem)
    # Importante: Use o mesmo status que você definiu no triagem_finalizar
    fila_corredor = FichaAtendimento.objects.filter(
        status=FichaAtendimento.Status.TRIADO 
    ).order_by('-prioridade', 'criado_em')[:8]
    
    return render(request, "attendance/painel_medico.html", {
        "atual": chamado, 
        "fila": fila_corredor
    })

# --- 3. LANÇAMENTO (Corredor/Roteamento) ---

@login_required
def lancamento_lista(request):
    """
    Lista pacientes triados e processa o encaminhamento para o médico.
    """
    # 1. Se o atendente clicou em "Encaminhar" (POST)
    if request.method == "POST":
        ficha_id = request.POST.get('ficha_id')
        medico_id = request.POST.get('medico_id')
        
        ficha = get_object_or_404(FichaAtendimento, id=ficha_id)
        medico = get_object_or_404(User, id=medico_id)
        
        # Atualiza a ficha para aparecer na TV 02
        ficha.medico_atendente = medico
        ficha.status = FichaAtendimento.Status.CHAMADO_MEDICO
        ficha.chamado_em = timezone.now()
        ficha.save()
        
        messages.success(request, f"Paciente {ficha.paciente.nome} encaminhado ao Dr(a). {medico.first_name}")
        return redirect('attendance:lancamento_lista')

    # 2. Renderização da Lista (GET)
    triados = FichaAtendimento.objects.filter(
        status=FichaAtendimento.Status.TRIADO
    ).order_by('-prioridade', 'atualizado_em') # Ordena por urgência e tempo
    
    # Busca usuários no grupo 'Medicos'
    medicos = User.objects.filter(groups__name='Medicos')
    if not medicos.exists():
        medicos = User.objects.filter(is_staff=True) # Fallback para usuários da equipe
    
    return render(request, "attendance/lancamento_lista.html", {
        "triados": triados, 
        "medicos": medicos
    })

@require_http_methods(["POST"])
def lancamento_rotear(request, ficha_id):
    """Esta função você já deve ter, mas garanta que ela redireciona para a lista acima."""
    medico_id = request.POST.get('medico_id')
    local = request.POST.get('local')
    
    rotear_para_medico(ficha_id, medico_id, local)
    messages.success(request, "Paciente encaminhado ao consultório.")
    return redirect('attendance:lancamento_lista')

def tv_painel(request):
    # Pacientes chamados para TRIAGEM
    chamados_triagem = FichaAtendimento.objects.filter(
        status=FichaAtendimento.Status.CHAMADO_TRIAGEM
    ).order_by('-chamado_em')[:5]

    # Pacientes chamados para CONSULTA MÉDICA (Pós-triagem)
    chamados_medico = FichaAtendimento.objects.filter(
        status=FichaAtendimento.Status.CHAMADO_MEDICO 
    ).order_by('-chamado_em')[:5]

    return render(request, "attendance/tv_painel.html", {
        "chamados_triagem": chamados_triagem,
        "chamados_medico": chamados_medico,
    })