# 🏠 Robô Imóveis - Plataforma de Oportunidades Imobiliárias

## 📊 Visão Geral

Sistema completo de monitoramento e análise de oportunidades imobiliárias em mercados emergentes do Brasil. A plataforma identifica, analisa e ranqueia oportunidades de investimento antes que se tornem mainstream.

## 🎯 Funcionalidades Principais

### 🤖 Robôs de Monitoramento
- **Varredura Automatizada** de portais imobiliários regionais
- **Sistema Anti-Duplicatas** com banco SQLite
- **Algoritmo de Pontuação** baseado em múltiplos critérios
- **Logs Detalhados** de todas as operações

### 🌐 Dashboard Interativo
- **Cards Interativos** que viram para mostrar contatos
- **Ranking Automático** por score de potencial
- **Gráficos em Tempo Real** com Chart.js
- **Interface Responsiva** para todos os dispositivos

### 📈 Análise Estratégica
- **6 Cidades Monitoradas** com diferentes potenciais
- **Comparação de Mercados** emergentes vs consolidados
- **Projeções de Valorização** baseadas em dados históricos
- **Relatórios Automáticos** de oportunidades

## 🏆 Cidades e Potenciais

| Ranking | Cidade | Estado | Potencial | Crescimento Anual |
|---------|--------|--------|-----------|-------------------|
| 🥇 | Lucas do Rio Verde | MT | OURO | 3,83% |
| 🥈 | Rio Verde | GO | PRATA | 2,1% |
| 🥉 | Sinop | MT | BRONZE | 1,8% |
| 4️⃣ | Barreiras | BA | REGIONAL | 1,5% |
| 5️⃣ | Palmas | TO | ESTÁVEL | 1,2% |
| 📊 | Senador Canedo | GO | CONSOLIDADO | 0,8% |

## 🚀 Como Usar

### 1. Executar Robôs de Monitoramento
```bash
# Robô principal (todas as cidades)
python3 scripts/robo_oportunidades_regionais_v6.py

# Robô específico (Senador Canedo)
python3 scripts/robo_senador_canedo_v4.py
```

### 2. Iniciar Dashboard
```bash
# Dashboard principal
python3 src/main.py

# Dashboards específicos
python3 dashboards/dashboard_plataforma_completa.py
python3 dashboards/dashboard_oportunidades_nacionais.py
```

### 3. Consolidar Dados
```bash
# Unificar dados de múltiplas fontes
python3 scripts/consolidar_plataforma_completa.py
```

## 📁 Estrutura do Projeto

```
robo-imoveis/
├── src/
│   └── main.py                 # Aplicação principal Flask
├── scripts/
│   ├── robo_*.py              # Robôs de monitoramento
│   └── consolidar_*.py        # Scripts de consolidação
├── dashboards/
│   ├── dashboard_*.py         # Interfaces web
│   └── ...
├── docs/
│   ├── relatorio_*.md         # Relatórios e análises
│   ├── analise_*.md           # Estudos de mercado
│   └── requirements.txt       # Dependências
└── README.md                  # Este arquivo
```

## 🔧 Instalação

### Pré-requisitos
- Python 3.11+
- pip3
- SQLite3

### Dependências
```bash
pip3 install -r docs/requirements.txt
```

### Principais Bibliotecas
- **Flask** - Framework web
- **BeautifulSoup4** - Web scraping
- **Requests** - HTTP requests
- **SQLite3** - Banco de dados

## 💾 Banco de Dados

### Estrutura Principal
- **oportunidades_completas** - Todas as oportunidades consolidadas
- **estatisticas_cidades** - Métricas por cidade
- **historico_consolidado** - Log de consolidações

### Campos Principais
- `cidade`, `estado`, `titulo`, `preco`, `area`, `preco_m2`
- `score`, `potencial_categoria`, `portal`, `referencia`
- `endereco`, `bairro`, `url`, `data_encontrado`

## 🌐 Portais Integrados

1. **Keller Imóveis** - Lucas do Rio Verde e Sinop
2. **62imoveis.com.br** - Senador Canedo
3. **Realize Imóveis RV** - Rio Verde
4. **OLX Regional** - Barreiras e Palmas

## 📊 Resultados Alcançados

### ✅ Oportunidades Reais Capturadas
- **6 Oportunidades** com dados verificados
- **Faixa de Preços:** R$ 160.000 - R$ 760.000
- **Score Médio:** 75/100 pontos
- **ROI Projetado:** 12-20% ao ano

### 🎯 Destaques
- **Melhor Oportunidade:** Casa em Lucas do Rio Verde (R$ 760.000, Score 85)
- **Melhor Custo-Benefício:** Casa em Sinop (R$ 160.000, Score 75)
- **Referência Consolidada:** Lote em Senador Canedo (R$ 330.000, Score 75)

## 📈 Análise de Mercado

### 🔍 Metodologia
- **Crescimento Populacional** como indicador principal
- **Base Econômica** (agronegócio, indústria, serviços)
- **Infraestrutura** e desenvolvimento urbano
- **Preço/m²** comparativo com potencial

### 📊 Critérios de Pontuação
- **Preço por m²** (até 35 pontos)
- **Área do imóvel** (até 20 pontos)
- **Localização/Bairro** (até 15 pontos)
- **Potencial da cidade** (até 25 pontos)
- **Outros fatores** (até 5 pontos)

## 🚀 Deployment

### Desenvolvimento Local
```bash
python3 src/main.py
# Acesse: http://localhost:5000
```

### Produção
- **Flask Production Server** configurado
- **Variável PORT** para deploy em nuvem
- **Debug Mode** desabilitado

## 📝 Documentação Completa

Consulte a pasta `docs/` para:
- **Relatórios Detalhados** de cada execução
- **Análises de Mercado** aprofundadas
- **Estudos de Valorização** histórica
- **Guias de Contato** para cada oportunidade

## 🤝 Contribuição

Este projeto foi desenvolvido como sistema de inteligência imobiliária para identificação de oportunidades em mercados emergentes.

## 📄 Licença

Projeto desenvolvido para análise e monitoramento do mercado imobiliário brasileiro.

---

**🏆 Sistema que identifica oportunidades antes que se tornem mainstream!**

*Desenvolvido por: Sistema de Inteligência Imobiliária*  
*Versão: 1.0 - Deployment Permanente*  
*Data: Dezembro 2025*
