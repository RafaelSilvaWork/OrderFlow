---
name: Bug report
title: "[BUG] "
description: Reporte de problema
labels: bug
body:
  - type: textarea
    id: description
    attributes:
      label: Descrição
      description: Descreva o problema encontrado.
    validations:
      required: true
  - type: textarea
    id: steps
    attributes:
      label: Passos para reproduzir
      description: Liste os passos para reproduzir o comportamento.
    validations:
      required: true
  - type: textarea
    id: expected
    attributes:
      label: Comportamento esperado
      description: Explique o que deveria acontecer.
    validations:
      required: true
