from django.db import models
from django.conf import settings # Importante para vincular ao médico (User)
from patients.models import Patient

class FichaAtendimento(models.Model):
    class Status(models.TextChoices):
        # FLUXO TV 01 (Recepção/Triagem)
        CHEGADA = "CHEGADA", "Aguardando Triagem"
        CHAMADO_TRIAGEM = "CHAMADO_TRIAGEM", "Chamado para Triagem"
        EM_TRIAGEM = "EM_TRIAGEM", "Em Triagem"
        
        # ESTADO INTERMEDIÁRIO (Onde o Segundo PC atua)
        TRIADO = "TRIADO", "Aguardando Encaminhamento Médico"
        
        # FLUXO TV 02 (Corredor/Consultórios)
        AGUARDANDO_MEDICO = "AGUARDANDO_MEDICO", "Aguardando Médico"
        CHAMADO_MEDICO = "CHAMADO_MEDICO", "Chamado para Médico"
        EM_ATENDIMENTO = "EM_ATENDIMENTO", "Em Atendimento Médico"
        
        FINALIZADO = "FINALIZADO", "Finalizado"
        CANCELADO = "CANCELADO", "Cancelado"

    class Prioridade(models.TextChoices):
        VERMELHO = "VERMELHO", "Emergência"
        LARANJA = "LARANJA", "Muito Urgente"
        AMARELO = "AMARELO", "Urgente"
        VERDE = "VERDE", "Pouco Urgente"
        AZUL = "AZUL", "Não Urgente"

    codigo = models.CharField(max_length=10, unique=True)
    paciente = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="fichas")
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.CHEGADA)
    prioridade = models.CharField(max_length=10, choices=Prioridade.choices, null=True, blank=True)
    
    # Campo para o 'Segundo PC' definir o médico destino
    medico_atendente = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="atendimentos_medicos"
    )

    # Onde o painel diz para o paciente ir (Ex: Sala 01, Consultório 05)
    local_atendimento = models.CharField(max_length=50, null=True, blank=True) 

    # --- DADOS DA TRIAGEM (O "Papel Digital") ---
    pa_sistolica = models.IntegerField("Pressão Sistólica", null=True, blank=True)
    pa_diastolica = models.IntegerField("Pressão Diastólica", null=True, blank=True)
    temperatura = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    frequencia_cardiaca = models.IntegerField(null=True, blank=True)
    observacoes_triagem = models.TextField(null=True, blank=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    chamado_em = models.DateTimeField(null=True, blank=True)
    finalizado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Ficha de Atendimento"
        verbose_name_plural = "Fichas de Atendimento"
        ordering = ['-prioridade', 'criado_em'] # Prioridade Manchester nativa no banco

    def __str__(self):
        return f"{self.codigo} - {self.paciente.nome}"