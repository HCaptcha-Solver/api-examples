# Exemplos da API HCaptcha Solver

[English](README.md) · [Documentação interativa em português](https://hcaptchasolver.org/?lang=pt-BR#/docs)

Exemplos em **Python, Node.js e cURL** para integrar a API. Este repositório contém clientes HTTP, um preparador de imagens e imagens didáticas. A resolução acontece no serviço hospedado; este código não executa um resolvedor local.

| Modo | O que você envia | O que recebe |
| --- | --- | --- |
| Chrome gerenciado | URL pública da página e `sitekey` do widget | ID da operação para consultar; token quando o widget o emitir |
| Imagens | Captura do desafio, pergunta, referências e áreas de interação | Cliques, seleção de células ou arrastes para aplicar no seu navegador |

## Preparação

Crie a conta em [hcaptchasolver.org](https://hcaptchasolver.org/), confirme o e-mail, adicione saldo e gere a chave. Habilite `images` e/ou `browser`; adicione `balance` para consultar o saldo e `feedback` para informar o resultado.

```bash
git clone https://github.com/HCaptcha-Solver/api-examples.git
cd api-examples
export HCAPTCHA_API_KEY='SUA_CHAVE'
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python python/example.py balance
```

Use Python 3.11+ ou Node.js 22+. O cliente HTTP Python só usa a biblioteca padrão. Pillow é necessário para preparar imagens. O cliente Node usa `fetch` nativo e não exige `npm install`.

No PowerShell, use `$env:HCAPTCHA_API_KEY = 'SUA_CHAVE'`, crie o ambiente com `py -m venv .venv` e execute `.\.venv\Scripts\python.exe` em lugar de `python`. Os exemplos leem as variáveis de ambiente; não carregam um arquivo `.env` automaticamente.

## `references` e `canvases`: qual é a diferença?

- **`image`**: captura principal do desafio, em PNG/JPEG convertido para Base64 puro, sem `data:image/...`.
- **`references`**: pequenas imagens de exemplo usadas para comparação. Envie `[]` ou omita quando não houver referência. O nome correto está no plural.
- **`canvases`**: retângulos que delimitam áreas de clique ou arraste dentro da captura principal. Cada um tem `x`, `y`, `width` e `height`. Não são imagens.
- **`tiles`**: nove retângulos das células de uma grade formada por elementos separados da página, em ordem de leitura. Uma grade desenhada dentro de um canvas usa `canvases`.

O [guia de coordenadas](docs/image-mode.md) e a [documentação interativa](https://hcaptchasolver.org/?lang=pt-BR#/docs) mostram como medir essas regiões.

Para aprender a gerar o JSON, use a ilustração sintética de 600 × 400 pixels. Este comando não acessa a API nem consome saldo:

```bash
python python/prepare_image_request.py fixtures/challenge.png \
  --question 'Click the object matching the example' \
  --canvas 30 80 540 280 \
  --reference fixtures/reference.png --output request.json
```

`--output` salva o JSON em UTF-8 também no Windows. Os comandos de várias linhas usam Bash/zsh; no PowerShell, coloque o comando do auxiliar em uma única linha. O auxiliar recebe o retângulo em pixels e converte para a escala da API: `{ "x": 50, "y": 200, "width": 900, "height": 700 }`. Omita `--reference` se não houver referência. Repita `--canvas` ou `--reference` quando necessário; para uma grade DOM, use nove argumentos `--tile`.

Em uma consulta real, substitua as imagens, a pergunta e os retângulos pelos da captura atual. As imagens de exemplo não são um CAPTCHA real e não geram token. Guarde capturas reais em `captures/`, ignorado pelo Git.

## Enviar uma consulta paga

Escolha um cliente. As chamadas de resolução abaixo consomem saldo:

```bash
REQUEST_ID=$(python -c 'import uuid; print(uuid.uuid4())')
python python/example.py image request.json --idempotency-key "$REQUEST_ID"
# Alternativa:
# node javascript/example.mjs image request.json --idempotency-key "$REQUEST_ID"
```

No PowerShell: `$requestId = [guid]::NewGuid().ToString()` e `--idempotency-key $requestId`.

Se a conexão cair sem confirmar a resposta, **repita o mesmo JSON com o mesmo ID**. Não gere outro JSON ou ID para essa retentativa. Um ID diferente pode iniciar outra operação paga. Os clientes não repetem POST automaticamente.

Leia `result.action` somente quando `status` for `ready`, `result_expired` for falso e `result` existir. O campo `id` é da operação no servidor; `result.challenge_id` identifica sua captura. Confirme também que o desafio ainda é o mesmo antes de aplicar a resposta. Os exemplos imprimem as ações, mas não clicam no seu navegador.

Se a espera terminar, use o ID já recebido:

```bash
python python/example.py get ID_DA_OPERACAO
# Ou: node javascript/example.mjs get ID_DA_OPERACAO
```

Para Chrome gerenciado:

```bash
REQUEST_ID=$(python -c 'import uuid; print(uuid.uuid4())')
python python/example.py browser \
  --url 'https://seu-site.example/formulario' \
  --sitekey 'SITEKEY_PUBLICA_DO_WIDGET' \
  --idempotency-key "$REQUEST_ID"
```

O `sitekey` é a chave pública do widget, não sua chave da nossa API. Este modo abre uma sessão nova, sem importar cookies ou executar um login personalizado. O cliente acompanha a operação até terminar. A emissão de `result.token` não confirma que o backend do site aceitou esse token.

## Cobrança, erros e testes

Uma resposta de ações pode ser cobrada mesmo que o widget a rejeite depois. Cada nova rodada pode exigir outra consulta paga; feedback não gera reembolso automático. Valores monetários são inteiros em milionésimos de USD: divida por `1.000.000`.

HTTP 200 pode conter `status: failed`: verifique `error`. Em 429, aguarde `Retry-After`. Em 409, confira se mudou o corpo usando o mesmo ID. Em 422, revise campos, Base64 e coordenadas. O [README em inglês](README.md#errors-and-limits) tem a tabela completa, limites e exemplos cURL.

Os testes abaixo usam respostas simuladas e imagens sintéticas, sem chamadas pagas:

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/*.test.mjs
```

Código sob licença [MIT](LICENSE). Use o serviço em sites e fluxos que você tem autorização para automatizar. HCaptcha Solver é um serviço independente, sem afiliação com o fornecedor do hCaptcha.
