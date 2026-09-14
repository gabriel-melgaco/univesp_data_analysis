import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

ARQ = 'archive/'

PAGAMENTOS = {
    'credit_card': 'Cartão de Crédito',
    'boleto': 'Boleto',
    'voucher': 'Vale',
    'debit_card': 'Cartão de Débito',
    'not_defined': 'Não definido',
}


@st.cache_data
def load():
    d = {
        'orders': pd.read_csv(
            ARQ + 'olist_orders_dataset.csv',
            parse_dates=['order_purchase_timestamp', 'order_delivered_customer_date',
                         'order_estimated_delivery_date']),
        'items': pd.read_csv(ARQ + 'olist_order_items_dataset.csv'),
        'payments': pd.read_csv(ARQ + 'olist_order_payments_dataset.csv'),
        'reviews': pd.read_csv(ARQ + 'olist_order_reviews_dataset.csv'),
        'products': pd.read_csv(ARQ + 'olist_products_dataset.csv'),
        'translation': pd.read_csv(ARQ + 'product_category_name_translation.csv'),
        'customers': pd.read_csv(ARQ + 'olist_customers_dataset.csv'),
        'sellers': pd.read_csv(ARQ + 'olist_sellers_dataset.csv'),
        'geo': pd.read_csv(ARQ + 'olist_geolocation_dataset.csv'),
    }
    return d


def prep(d):
    geo = (d['geo'].groupby('geolocation_zip_code_prefix')[['geolocation_lat', 'geolocation_lng']]
           .mean().reset_index())
    geo.columns = ['zip', 'lat', 'lng']
    # descarta CEPs com coordenadas fora do territorio brasileiro
    geo = geo[geo['lat'].between(-34, 6) & geo['lng'].between(-75, -34)]

    # entrega: prazo real e atraso em relacao ao estimado
    orders = d['orders'].copy()
    orders['entrega_dias'] = (orders['order_delivered_customer_date']
                              - orders['order_purchase_timestamp']).dt.days
    orders['atraso_dias'] = (orders['order_delivered_customer_date']
                             - orders['order_estimated_delivery_date']).dt.days

    # mapa de clientes (cep -> estado)
    cust_map = (d['customers'].merge(geo.rename(columns={'zip': 'customer_zip_code_prefix'}),
                                     on='customer_zip_code_prefix', how='left')
                .groupby(['customer_zip_code_prefix', 'customer_state'])[['lat', 'lng']]
                .mean().reset_index())

    # distancia vendedor -> cliente por pedido
    ord_ = (orders[['order_id', 'customer_id', 'order_purchase_timestamp',
                    'entrega_dias', 'atraso_dias']]
            .merge(d['customers'][['customer_id', 'customer_zip_code_prefix']], on='customer_id')
            .merge(cust_map[['customer_zip_code_prefix', 'lat', 'lng']],
                   on='customer_zip_code_prefix', how='left')
            .rename(columns={'lat': 'c_lat', 'lng': 'c_lng'})
            .merge(d['items'][['order_id', 'seller_id', 'price']], on='order_id')
            .merge(d['sellers'][['seller_id', 'seller_zip_code_prefix']], on='seller_id')
            .merge(geo.rename(columns={'zip': 'seller_zip_code_prefix',
                                       'lat': 's_lat', 'lng': 's_lng'}),
                   on='seller_zip_code_prefix', how='left'))
    lat1, lat2 = np.radians(ord_['c_lat']), np.radians(ord_['s_lat'])
    a = (np.sin(np.radians(ord_['s_lat'] - ord_['c_lat']) / 2) ** 2
         + np.cos(lat1) * np.cos(lat2)
         * np.sin(np.radians(ord_['s_lng'] - ord_['c_lng']) / 2) ** 2)
    ord_['dist_km'] = 2 * 6371 * np.arcsin(np.sqrt(a))
    dist = ord_.dropna(subset=['dist_km', 'entrega_dias'])

    # satisfacao x atraso
    rev = d['reviews'].groupby('order_id')['review_score'].max().reset_index()
    sat = ord_.merge(rev, on='order_id').dropna(subset=['atraso_dias'])

    # faturamento mensal
    pay = d['payments'].merge(orders[['order_id', 'order_purchase_timestamp']], on='order_id')
    pay['mes'] = pay['order_purchase_timestamp'].dt.to_period('M').astype(str)
    rev_m = pay.groupby('mes', as_index=False)['payment_value'].sum()

    # categorias
    items = (d['items'].merge(d['products'][['product_id', 'product_category_name']],
                              on='product_id', how='left')
             .merge(d['translation'], on='product_category_name', how='left'))
    items['categoria'] = (items['product_category_name_english']
                          .fillna(items['product_category_name']))
    cat = (items.groupby('categoria', as_index=False)
           .agg(volume=('order_id', 'size'), faturamento=('price', 'sum')))

    # pagamentos
    pay_t = (d['payments'].groupby('payment_type', as_index=False)
             .agg(volume=('payment_value', 'count'), total=('payment_value', 'sum'),
                  parcelas_med=('payment_installments', 'mean')))
    pay_t['tipo'] = pay_t['payment_type'].map(PAGAMENTOS)

    # prazo medio de entrega por estado do cliente
    prazo_estado = (ord_.merge(d['customers'][['customer_id', 'customer_state']], on='customer_id')
                    .groupby('customer_state', as_index=False)['entrega_dias'].mean())

    return dict(orders=orders, cust_map=cust_map, dist=dist, sat=sat,
                rev_m=rev_m, cat=cat, pay_t=pay_t, prazo_estado=prazo_estado)


def main():
    st.set_page_config(page_title='E-commerce Brasileiro — Insights', layout='wide')
    st.title('📦 E-commerce Brasileiro — Dashboard de Insights')
    st.caption('Dataset Olist (~100 mil pedidos) · 2016–2018 · '
               '[Kaggle: olistbr/brazilian-ecommerce](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)')
    st.caption('UNIVESP · PJI410 — A2026S2N1 · Grupo 14')
    with st.expander('📌 Tema do PI'):
        st.write('Desenvolver análise de dados em escala utilizando algum conjunto de dados '
                 'existente ou capturado por IoT e aprendizagem de máquina. Preparar uma '
                 'interface para visualização dos resultados.')

    d = load()
    data = prep(d)

    # ---------------------------------------------------------------- 1
    st.header('🗺️ 1. Visão Logística — O Mapa do E-commerce Brasileiro')
    st.write('O desafio continental: vendedores concentrados no Sudeste/Sul, '
             'clientes espalhados por todo o país.')

    fig = px.scatter_geo(
        data['cust_map'], lat='lat', lon='lng', color='customer_state',
        scope='south america', opacity=0.5,
        title='Distribuição geográfica dos clientes por estado',
        labels={'customer_state': 'Estado'})
    fig.update_geos(fitbounds='locations', center=dict(lat=-14, lon=-53))
    fig.update_layout(height=520, margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        prazo = data['prazo_estado'].sort_values('entrega_dias', ascending=False)
        fig = px.bar(prazo, x='customer_state', y='entrega_dias',
                     title='Prazo médio de entrega (dias) por estado do cliente',
                     labels={'customer_state': 'Estado', 'entrega_dias': 'Dias'},
                     color='entrega_dias', color_continuous_scale='RdYlGn_r')
        fig.update_layout(height=420, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        amostra = data['dist'].sample(min(20000, len(data['dist'])), random_state=42)
        fig = px.scatter(amostra, x='dist_km', y='entrega_dias', opacity=0.35,
                         title='Distância vendedor→cliente vs. tempo de entrega',
                         labels={'dist_km': 'Distância (km)', 'entrega_dias': 'Dias de entrega'})
        fig.update_layout(height=420)
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f'Distância média por pedido: **{data["dist"]["dist_km"].mean():,.0f} km** '
                   f'(mediana {data["dist"]["dist_km"].median():,.0f} km)')

    # ---------------------------------------------------------------- 2
    st.divider()
    st.header('😊 2. Satisfação vs. Prazo de Entrega')
    st.write('A prova em dados da frase: *"Atrasos na entrega destroem a experiência do cliente"*.')

    sat = data['sat']
    corr = sat['atraso_dias'].corr(sat['review_score'])
    ontime = sat[sat['atraso_dias'] <= 0]['review_score'].mean()
    late = sat[sat['atraso_dias'] > 0]['review_score'].mean()
    atrasadas = (sat['atraso_dias'] > 0).mean() * 100

    m1, m2, m3, m4 = st.columns(4)
    m1.metric('Pedidos entregues com atraso', f'{atrasadas:.1f}%')
    m2.metric('Nota média no prazo', f'{ontime:.2f} ⭐')
    m3.metric('Nota média com atraso', f'{late:.2f} ⭐')
    m4.metric('Correlação atraso × nota', f'{corr:.2f}')

    bucket = (sat.groupby('atraso_dias', as_index=False)['review_score']
              .mean().query('atraso_dias >= -20 & atraso_dias <= 30'))
    fig = px.line(bucket, x='atraso_dias', y='review_score', markers=True,
                  title='Nota média por dias de atraso (negativo = entregue antes do prazo)',
                  labels={'atraso_dias': 'Atraso (dias)', 'review_score': 'Nota média'})
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)
    st.success(f'A correlação de **{corr:.2f}** e a queda de nota de {ontime:.2f} '
               f'(no prazo) para {late:.2f} (atrasado) confirmam: cada dia de atraso '
               f'corrói a satisfação do cliente.')

    # ---------------------------------------------------------------- 3
    st.divider()
    st.header('💰 3. Raio-X do Faturamento e Preferências de Compra')

    fig = px.line(data['rev_m'], x='mes', y='payment_value', markers=True,
                  title='Faturamento total por mês',
                  labels={'mes': 'Mês', 'payment_value': 'Faturamento (R$)'})
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        top_vol = data['cat'].nlargest(10, 'volume').sort_values('volume')
        fig = px.bar(top_vol, x='volume', y='categoria', orientation='h',
                     title='Top 10 categorias por volume de vendas',
                     labels={'volume': 'Itens vendidos', 'categoria': ''})
        fig.update_layout(height=450)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        top_rev = data['cat'].nlargest(10, 'faturamento').sort_values('faturamento')
        fig = px.bar(top_rev, x='faturamento', y='categoria', orientation='h',
                     title='Top 10 categorias por faturamento bruto',
                     labels={'faturamento': 'Faturamento (R$)', 'categoria': ''})
        fig.update_layout(height=450)
        st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        fig = px.pie(data['pay_t'], names='tipo', values='total',
                     title='Faturamento por tipo de pagamento', hole=0.45)
        fig.update_layout(height=420)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        parcelas = data['pay_t'].sort_values('parcelas_med', ascending=False)
        fig = px.bar(parcelas, x='tipo', y='parcelas_med',
                     title='Número médio de parcelas por tipo de pagamento',
                     labels={'tipo': 'Tipo', 'parcelas_med': 'Parcelas médias'},
                     color='tipo')
        fig.update_layout(height=420, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f'Parcelas médias no cartão de crédito: '
                   f'**{data["pay_t"].loc[data["pay_t"]["payment_type"] == "credit_card", "parcelas_med"].iloc[0]:.1f}**')


if st.runtime.exists():
    main()
elif __name__ == '__main__':
    data = prep(load())
    assert data['orders']['order_id'].nunique() > 90000, 'pedidos insuficientes'
    assert data['sat']['atraso_dias'].corr(data['sat']['review_score']) < 0, 'correlação deveria ser negativa'
    assert data['dist']['dist_km'].max() < 5000, 'distância irreal'
    assert data['rev_m']['payment_value'].sum() > 10_000_000, 'faturamento inconsistente'
    assert data['cat']['volume'].sum() > 100_000, 'categorias incompletas'
    assert set(data['pay_t']['payment_type']) <= set(PAGAMENTOS), 'tipo de pagamento desconhecido'
    print('OK: dataset carregado e insights validados')
