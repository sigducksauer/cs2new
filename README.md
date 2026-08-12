# CS2 Update Monitor

Monitor automático e seguro de atualizações oficiais do **Counter-Strike 2**.

O projeto consulta periodicamente a API pública da Steam e envia notificações para um canal do Discord via Webhook sempre que uma nova atualização é detectada.

---

## Características

- Monitoramento automático via GitHub Actions
- Fonte oficial: Steam News API
- Notificações limpas e formatadas no Discord
- Sistema de deduplicação (não repete a mesma notícia)
- Código robusto com retry e tratamento de erros
- Seguro: o Webhook fica apenas em Secrets do GitHub
- 100% gratuito em repositório público

---

## Como funciona

A cada 5 minutos o GitHub Actions executa o script `monitor.py`, que:

1. Consulta a API oficial de notícias da Steam (AppID 730)
2. Verifica se existe uma notícia nova
3. Filtra apenas atualizações relevantes
4. Envia um embed formatado para o Discord
5. Salva o ID da última notícia processada para evitar duplicatas

---

## Setup rápido

### 1. Fork ou clone este repositório

### 2. Configure o Secret do Discord

1. Vá em **Settings → Secrets and variables → Actions**
2. Clique em **New repository secret**
3. Name: `DISCORD_WEBHOOK`
4. Value: cole a URL completa do seu Webhook do Discord
5. Salve

> Como criar um Webhook no Discord:  
> Canal → Editar canal → Integrações → Webhooks → Novo Webhook → Copiar URL

### 3. Ative o workflow

O workflow já está configurado para rodar automaticamente.  
Você também pode disparar manualmente em **Actions → CS2 Update Monitor → Run workflow**.

---

## Arquivos principais

| Arquivo | Função |
|---------|--------|
| `monitor.py` | Lógica principal de monitoramento e envio |
| `.github/workflows/cs2-monitor.yml` | Agendamento e execução no GitHub Actions |
| `requirements.txt` | Dependências Python |
| `.gitignore` | Arquivos ignorados pelo Git |

---

## Personalização

Você pode alterar facilmente:

- Intervalo de verificação (arquivo do workflow)
- Palavras-chave de filtro de updates (`UPDATE_KEYWORDS` no `monitor.py`)
- Aparência do embed do Discord

---

## Segurança

- O Webhook **nunca** é exposto no código
- Nenhuma informação sensível é commitada
- Permissões mínimas no workflow (`contents: read`)
- Headers e timeouts configurados corretamente
- Sem dependências desnecessárias

---

## Aviso

Este projeto utiliza apenas a **API pública oficial da Steam**.  
Não realiza engenharia reversa, scraping agressivo ou qualquer atividade que viole os termos da Steam/Valve.

---

## Licença

MIT License — use como quiser.
