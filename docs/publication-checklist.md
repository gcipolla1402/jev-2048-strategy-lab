# Checklist de publicação

Use este documento antes de criar o repositório público `jev-2048-strategy-lab`.

## Código e funcionamento

- [x] Backend, frontend, motor 2048, integração JEV, estratégias, benchmarks e persistência revisados no código.
- [x] Suíte local executada sem chamadas reais ao JEV: 27 testes aprovados em 11/11/2026.
- [x] TypeScript e build Vite aprovados em 11/11/2026.
- [x] Resultados locais estão excluídos pelo `.gitignore`.
- [ ] Repetir `python -m pytest` e `npm run build` imediatamente antes da publicação.
- [ ] Fazer uma última execução manual da interface em modo manual.
- [ ] Se desejado, validar o JEV com uma chamada conscientemente autorizada e sem registrar a chave.

## Segurança e privacidade

- [x] `.env`, variantes locais, ambientes virtuais, dependências, builds, caches, logs, temporários, certificados e credenciais estão cobertos pelo `.gitignore`.
- [x] `.env.example` usa uma chave fictícia e contém apenas nomes de configuração necessários.
- [x] Varredura local por padrões de segredo concluída sem exibir valores; foram encontradas somente referências esperadas no código e na documentação.
- [x] Certificados encontrados pertencem ao `.venv`, que está ignorado.
- [ ] Confirmar com `git status --ignored` que `.env`, `.venv`, `node_modules`, `dist` e `apps/backend/data/results.json` não serão adicionados.
- [ ] Depois de criar o repositório, executar um scanner de segredos sobre os arquivos preparados e sobre cada commit.
- [ ] Se algum segredo entrar em um commit, revogar a credencial antes de reescrever o histórico.

## Autoria e direitos

- [ ] Confirmar que todo o código e todo material visual podem ser publicados por Gabriel Cipolla Rocca.
- [ ] Confirmar que não há código, documentação, nomes internos ou dados pertencentes à GFT, clientes ou outros empregadores.
- [ ] Escolher uma licença somente após confirmar a titularidade e a política aplicável. Nenhuma licença foi adicionada automaticamente.
- [ ] Revisar os termos e licenças das dependências antes da publicação.

## Apresentação

- [x] README em português brasileiro com arquitetura, execução, testes, limitações e contato.
- [x] Diagrama Mermaid criado a partir da arquitetura presente no código.
- [ ] Capturar as quatro imagens reais descritas em `docs/screenshots/README.md`.
- [ ] Revisar textos e imagens para remover IDs de partidas, seeds ou dados que não devam ser públicos.
- [ ] Definir descrição, tópicos e imagem social do repositório no GitHub.

## GitHub

- [ ] Criar o repositório público somente após concluir os itens humanos acima.
- [ ] Conferir todos os arquivos preparados antes do primeiro `git add`.
- [ ] Verificar o diff staged antes do primeiro commit.
- [ ] Ativar proteção contra push de segredos e alertas de dependências, se disponíveis.
- [ ] Conferir a renderização do Mermaid e os links do README no GitHub.

## Estado da auditoria Git

Em 11/11/2026, `C:\Projetos\demo2048` não continha um repositório Git. Por isso, não havia histórico local para investigar e nenhum comando `git init`, `git add`, `git commit` ou `git push` foi executado. A auditoria do histórico deve ser refeita se arquivos `.git` forem introduzidos depois desta revisão.
