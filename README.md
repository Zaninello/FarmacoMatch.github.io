# FarmacoMatch.github.io

Site estático (frontend) de apresentação do projeto **FarmacoMatch**,
publicado via **GitHub Pages**.

URL final (após publicado): **https://farmacomatch.github.io/**

> Este repositório contém apenas o frontend de apresentação (HTML/CSS/JS puro,
> sem build). A aplicação principal (Streamlit + SQLite) é executada em um
> servidor separado e é referenciada por um link neste site.

---

## Estrutura

```
FarmacoMatch.github.io/
├── index.html          # Página única (landing)
├── assets/
│   ├── css/style.css    # Estilos
│   ├── js/main.js       # Menu mobile + reveal on scroll
│   ├── docs/Doc-Tecnica-FarmacoMatch.pdf
│   ├── docs/Codigo-Fonte-FarmacoMatch.pdf
│   └── img/             # (reservado para imagens)
├── tools/               # Scripts de build dos PDFs
├── .nojekyll            # Evita processamento Jekyll no Pages
└── README.md
```

---

## Como definir o link da aplicação

O botão "Abrir FarmacoMatch no servidor" aponta para a aplicação Streamlit
rodando em outro servidor. Para definir a URL:

1. Abra `index.html`.
2. Procure pelo comentário `LINK_APP`.
3. Substitua o atributo `href` (aparece em 2 pontos: botão do hero e botão
   principal da seção "Acessar aplicação") pela URL real, por exemplo:

```html
<a class="btn btn-primary btn-xl" href="https://meu-servidor.com/app" ...>
  Abrir FarmacoMatch no servidor →
</a>
```

Pronto — o site passará a abrir a aplicação ao clicar.

---

## Publicar no GitHub Pages

1. Crie (ou use) um repositório chamado exatamente
   `FarmacoMatch.github.io` (Nome do Owner = `FarmacoMatch`).
2. Faça commit e push dos arquivos para a branch `main`:

   ```bash
   git add .
   git commit -m "Site estático de apresentação do FarmacoMatch"
   git push origin main
   ```

3. No GitHub, abra **Settings → Pages**.
4. Em **Source**, escolha:
   - Branch: `main`
   - Folder: `/ (root)`
   - Salvar.
5. Aguarde 1–2 minutos. O site ficará disponível em:

   **https://farmacomatch.github.io**

> Como usamos HTML/CSS/JS puro (sem build), nenhuma action/CI é necessária.
> O arquivo `.nojekyll` garante que o Pages publique os arquivos sem processar
> com Jekyll.

---

## Pré-visualizar localmente

```bash
python3 -m http.server 8000
# abra http://localhost:8000
```

---

## Projeto referenciado

Aplicação FarmacoMatch (Streamlit + SQLite):
verificação de compatibilidade medicamentosa entre classes farmacológicas.

Projeto acadêmico — Unifil.