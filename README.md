# E-commerce Brasileiro — Dashboard de Insights

Projeto Django + Streamlit sobre o dataset Olist (e-commerce brasileiro, ~100 mil pedidos).

Trabalho acadêmico: **UNIVESP · PJI410 — A2026S2N1 · Grupo 14**

## Executar

Opção rápida (sobe os dois serviços juntos):

```bash
./run.sh
```

Ou manualmente — terminal 1, Streamlit (dashboard na porta 8501):

```bash
.venv/bin/streamlit run dashboard.py
```

Terminal 2 — Django (página web na porta 8001, a 8000 é usada pelo HPLIP do sistema):

```bash
.venv/bin/python manage.py runserver 8001
```

Acesse http://localhost:8001 — o dashboard Streamlit aparece embutido na página.

## Estrutura

- `dashboard.py` — aplicação Streamlit com os 3 insights (logística, satisfação vs. prazo, faturamento/pagamentos)
- `ecommerce/` — projeto Django (página com iframe do dashboard)
- `core/` — app com a view e o template
- `archive/` — dataset Olist ([Kaggle: olistbr/brazilian-ecommerce](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce))

## Validar os dados (sem abrir o app)

```bash
.venv/bin/python dashboard.py
```

Deve imprimir `OK: dataset carregado e insights validados`.
# univesp_data_analysis
