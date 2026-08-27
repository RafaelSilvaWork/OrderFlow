# Arquitetura do projeto

## Visão geral
O projeto é uma aplicação desktop em Python com interface PyQt6 para automação de processos da plataforma Coupa.

## Estrutura principal
- main.py: ponto de entrada da aplicação e montagem da janela principal.
- modules/: contém widgets, serviços e utilidades da aplicação.
  - ui_*.py: widgets da interface gráfica.
  - services/: camada de domínio para regras de negócio e operações reutilizáveis.
  - config.py: configuração centralizada e helpers de criptografia.
  - logger.py: logging padronizado.

## Padrões adotados
- Widgets devem permanecer enxutos e delegar regras de negócio para services.
- Operações críticas devem registrar logs em vez de depender de prints silenciosos.
- Testes devem cobrir comportamento de negócio e fluxos principais.

## Fluxos principais
1. Extração de dados da Aba 1.
2. Encadeamento automático entre abas para download, PDF, renomeação e e-mail.
3. Persistência de perfis e dados sensíveis via configuração criptografada.

## Evolução recomendada
- continuar separando UI e regra de negócio;
- expandir testes de integração;
- adicionar mais verificações estáticas e CI automática.
