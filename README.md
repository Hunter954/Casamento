# Wedding Moments - Flask

MVP mobile-first para site de casamento com painel administrativo.

## Recursos do MVP

- Home 100% mobile-first com hero romântico, contador para o casamento e visual delicado.
- Configuração total pelo admin: nomes do casal, frase, data do casamento, local, horário, mapa, banner, tema e mensagem final.
- RSVP / confirmar presença.
- Mural de recados com moderação opcional.
- Lista de presentes com integração preparada para Mercado Pago.
- Registro de pagamentos recebidos via webhook.
- Campanhas de WhatsApp com controle de envio para não repetir destinatários.
- Upload de imagens para hero, banner e galeria.
- Estrutura pronta para Railway + GitHub.

## Rodando localmente

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate  # Windows
pip install -r requirements.txt
cp .env.example .env
python seed.py
flask db init
flask db migrate -m "init"
flask db upgrade
python seed.py
flask run
```

Acesse:

- Site público: `http://127.0.0.1:5000/`
- Admin: `http://127.0.0.1:5000/admin/login`

Credenciais padrão:

- Email: `admin@casamento.com`
- Senha: `123456`

## Deploy no Railway

1. Suba o projeto para o GitHub.
2. Crie um projeto no Railway apontando para o repositório.
3. Adicione as variáveis do `.env.example`.
4. Use Postgres em produção e configure `DATABASE_URL`.
5. Para arquivos persistentes, monte um volume e aponte `UPLOAD_DIR` se quiser personalizar.

## Mercado Pago

O projeto já possui:

- criação de preferência dinâmica por presente
- retorno dos dados do comprador
- endpoint de webhook para atualizar pagamentos

Você só precisa preencher `MERCADO_PAGO_ACCESS_TOKEN`.

## WhatsApp

O módulo de campanha está preparado para controlar envios e evitar duplicidade por campanha.
Atualmente o disparo real está em modo seguro/local. Você pode conectar uma API externa depois
(Z-API, UltraMsg, Gupshup, Twilio, etc.) editando `app/services/whatsapp.py`.

## IA para mensagens carinhosas

O botão “gerar mensagem” usa um gerador local elegante para já funcionar sem API paga.
Se quiser uma V2 com IA real, deixe `OPENAI_API_KEY` configurada e substitua a função em
`app/services/message_ai.py`.
