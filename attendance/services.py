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
    from django.utils import timezone
    hoje = timezone.now().date()
    prefixo = "A"
    
    # 1. Tenta pegar a última ficha de hoje
    ultima_hoje = FichaAtendimento.objects.filter(
        criado_em__date=hoje
    ).order_by('-id').first()

    if ultima_hoje:
        try:
            numero = int(ultima_hoje.codigo[1:])
            return f"{prefixo}{numero + 1:03d}"
        except (ValueError, IndexError):
            pass

    # 2. Se não achou ficha de hoje, vamos conferir a ÚLTIMA GERAL do banco
    # Isso evita o erro caso o fuso horário esteja desencontrado
    ultima_geral = FichaAtendimento.objects.order_by('-id').first()
    
    if ultima_geral:
        # Se a última ficha geral for de "hoje" (mesmo que o filtro de data falhou)
        # extraímos o número dela e somamos 1
        if ultima_geral.codigo.startswith(prefixo):
            try:
                # Verificamos se a data de criação da última é igual a hoje
                # Se for o mesmo dia, incrementamos. Se for outro dia, resetamos para 001.
                if ultima_geral.criado_em.date() == hoje:
                    numero = int(ultima_geral.codigo[1:])
                    return f"{prefixo}{numero + 1:03d}"
            except:
                pass

    # 3. Se chegou aqui, ou é o primeiro do dia ou o banco está vazio
    return f"{prefixo}001"

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
        Patient.objects.filter(id=paciente.id).update(nome=nome, telefone=telefone)

    ficha = FichaAtendimento.objects.create(
        codigo=_proximo_codigo(),
        paciente=paciente,
        status=FichaAtendimento.Status.CHEGADA,
    )
    # AJUSTE AQUI: era 'creado', o correto é 'criado'
    return CriarFichaResult(ficha=ficha, paciente_criado=criado)
# --- TRIAGEM ---

@transaction.atomic
def chamar_para_triagem(ficha_id: int) -> FichaAtendimento:
    ficha = FichaAtendimento.objects.select_for_update().get(id=ficha_id)
    ficha.status = FichaAtendimento.Status.CHAMADO_TRIAGEM
    ficha.chamado_em = timezone.now()
    ficha.save()
    return ficha

@transaction.atomic
def finalizar_triagem(ficha_id: int, dados_triagem: dict) -> FichaAtendimento:
    """ESTA É A FUNÇÃO QUE ESTAVA FALTANDO"""
    ficha = FichaAtendimento.objects.select_for_update().get(id=ficha_id)
    
    ficha.prioridade = dados_triagem.get('prioridade')
    ficha.pa_sistolica = dados_triagem.get('pa_sistolica')
    ficha.pa_diastolica = dados_triagem.get('pa_diastolica')
    ficha.temperatura = dados_triagem.get('temperatura')
    ficha.frequencia_cardiaca = dados_triagem.get('frequencia_cardiaca')
    ficha.observacoes_triagem = dados_triagem.get('observacoes_triagem')
    
    ficha.status = FichaAtendimento.Status.TRIADO 
    ficha.save()
    return ficha

# --- LANÇAMENTO / ROTEAMENTO ---
@transaction.atomic
def rotear_para_medico(ficha_id: int, medico_id: int, local: str) -> FichaAtendimento:
    ficha = FichaAtendimento.objects.select_for_update().get(id=ficha_id)
    
    # NOMES CORRIGIDOS CONFORME SEU MODELS.PY:
    ficha.medico_atendente_id = medico_id # Usando _id para evitar busca extra no banco
    ficha.local_atendimento = local       # Nome exato no seu model
    
    ficha.status = FichaAtendimento.Status.CHAMADO_MEDICO
    ficha.chamado_em = timezone.now()
    ficha.save()
    return ficha

# --- MÉDICO ---

@transaction.atomic
def chamar_para_medico(ficha_id: int) -> FichaAtendimento:
    ficha = FichaAtendimento.objects.select_for_update().get(id=ficha_id)
    ficha.status = FichaAtendimento.Status.CHAMADO_MEDICO
    ficha.chamado_em = timezone.now()
    ficha.save()
    return ficha

@transaction.atomic
def finalizar_atendimento_medico(ficha_id: int) -> FichaAtendimento:
    ficha = FichaAtendimento.objects.select_for_update().get(id=ficha_id)
    ficha.status = FichaAtendimento.Status.FINALIZADO
    ficha.finalizado_em = timezone.now()
    ficha.save()
    return ficha