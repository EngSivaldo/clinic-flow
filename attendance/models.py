from django.db import models
from patients.models import Patient


class FichaAtendimento(models.Model):
    """
    Controla o fluxo completo do paciente dentro da unidade de saúde.
    """

    class Status(models.TextChoices):
        CHEGADA = "CHEGADA", "Aguardando Triagem"
        TRIAGEM = "TRIAGEM", "Em Triagem"
        AGUARDANDO_MEDICO = "AGUARDANDO_MEDICO", "Aguardando Médico"
        CHAMADO_MEDICO = "CHAMADO_MEDICO", "Chamado para Médico"
        EM_ATENDIMENTO = "EM_ATENDIMENTO", "Em Atendimento"
        FINALIZADO = "FINALIZADO", "Finalizado"
        CANCELADO = "CANCELADO", "Cancelado"

    class Prioridade(models.TextChoices):
        VERMELHO = "VERMELHO", "Emergência"
        LARANJA = "LARANJA", "Muito Urgente"
        AMARELO = "AMARELO", "Urgente"
        VERDE = "VERDE", "Pouco Urgente"
        AZUL = "AZUL", "Não Urgente"

    codigo = models.CharField(max_length=10, unique=True)

    paciente = models.ForeignKey(
        Patient,
        on_delete=models.PROTECT,
        related_name="fichas"
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.CHEGADA
    )

    prioridade = models.CharField(
        max_length=10,
        choices=Prioridade.choices,
        null=True,
        blank=True
    )

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    chamado_em = models.DateTimeField(null=True, blank=True)
    finalizado_em = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.codigo} - {self.paciente.nome}"

