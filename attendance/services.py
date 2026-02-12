from __future__ import annotations
from dataclasses import dataclass
from django.db import transaction, models
from django.utils import timezone
from .models import FichaAtendimento
from patients.models import Patient

@dataclass(frozen=True)
class CriarFichaResult:
    ficha: FichaAtendimento
    paciente_criado: bool

# --- GERAÇÃO DE CÓDIGO ---
def _proximo_codigo() -> str:
    hoje = timezone.now().date()
    prefixo = "A"
    ultimo = (
        FichaAtendimento.objects
        .filter(criado_em__date=hoje, codigo__startswith=prefixo)
        .order_by("-codigo").first()
    )
    if not ultimo:
        return f"{prefixo}001"
    try:
        numero = int(ultimo.codigo[1:])
    except ValueError:
        numero = 0
    return f"{prefixo}{numero + 1:03d}"

# --- RECEPÇÃO ---
@transaction.atomic
def criar_ficha_por_cpf(*, nome, cpf, telefone="", nome_mae="", data_nascimento=None) -> CriarFichaResult:
    paciente, criado = Patient.objects.get_or_create(
        cpf=cpf,
        defaults={
            "nome": nome, "telefone": telefone, 
            "nome_mae": nome_mae, "data_nascimento": data_nascimento
        }
    )
    if not criado:
        # Atualização rápida se já existir
        Patient.objects.filter(id=paciente.id).update(nome=nome, telefone=telefone)

    ficha = FichaAtendimento.objects.create(
        codigo=_proximo_codigo(),
        paciente=paciente,
        status=FichaAtendimento.Status.CHEGADA,
    )
    return CriarFichaResult(ficha=ficha, paciente_criado=criado)

# --- TRIAGEM (Ação do Enfermeiro) ---

@transaction.atomic
def chamar_para_triagem(ficha_id: int) -> FichaAtendimento:
    """Aciona a TV 01 e move o paciente para dentro da sala de triagem."""
    ficha = FichaAtendimento.objects.select_for_update().get(id=ficha_id)
    ficha.status = FichaAtendimento.Status.CHAMADO_TRIAGEM
    ficha.chamado_em = timezone.now()
    ficha.save()
    # TODO: Disparar sinal para TV 01 via Channels
    return ficha

@transaction.atomic
def finalizar_triagem(ficha_id: int, dados_triagem: dict) -> FichaAtendimento:
    """Enfermeiro salva sinais vitais e libera o paciente para o corredor."""
    ficha = FichaAtendimento.objects.select_for_update().get(id=ficha_id)
    
    # Atualiza dados clínicos (substituindo o papel)
    ficha.prioridade = dados_triagem.get('prioridade')
    ficha.pa_sistolica = dados_triagem.get('pa_sistolica')
    ficha.pa_diastolica = dados_triagem.get('pa_diastolica')
    ficha.temperatura = dados_triagem.get('temperatura')
    ficha.frequencia_cardiaca = dados_triagem.get('frequencia_cardiaca')
    ficha.observacoes_triagem = dados_triagem.get('observacoes_triagem')
    
    # Sai da TV 01 e vai para a lista do Segundo PC
    ficha.status = FichaAtendimento.Status.TRIADO 
    ficha.save()
    return ficha

# --- LANÇAMENTO (O 'Segundo PC' do Corredor) ---

@transaction.atomic
def rotear_para_medico(ficha_id: int, medico_id: int, local: str) -> FichaAtendimento:
    """Define para qual médico e sala o paciente irá (TV 02)."""
    ficha = FichaAtendimento.objects.select_for_update().get(id=ficha_id)
    ficha.medico_atendente_id = medico_id
    ficha.local_atendimento = local
    ficha.status = FichaAtendimento.Status.AGUARDANDO_MEDICO
    ficha.save()
    return ficha

# --- MÉDICO (Consultório) ---

@transaction.atomic
def chamar_para_medico(ficha_id: int) -> FichaAtendimento:
    """Médico chama o paciente do corredor. Aciona a TV 02."""
    ficha = FichaAtendimento.objects.select_for_update().get(id=ficha_id)
    ficha.status = FichaAtendimento.Status.CHAMADO_MEDICO
    ficha.chamado_em = timezone.now()
    ficha.save()
    # TODO: Disparar sinal para TV 02 via Channels
    return ficha