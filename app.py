# ==============================================================================
# IMPORTAÇÕES
# ==============================================================================
import dash
from dash import dcc, html, Input, Output, State, no_update
import plotly.express as px
import pandas as pd
from datetime import datetime
from pathlib import Path

# ==============================================================================
# 1. LÓGICA PRINCIPAL E FUNÇÕES DE TESTE
# ==============================================================================

# Definindo a data da ordem de serviço como referência global para as funções
ordem_de_servico = pd.to_datetime('2025-08-01')

def calcular_datas(df_original):
    """
    Calcula as colunas de data ('Data Início', 'Data Término', 'Duracao') 
    com base nos meses do DataFrame original.
    """
    df_calc = df_original.copy()
    df_calc['Data Início'] = ordem_de_servico + pd.to_timedelta((df_calc['Mês Início'] - 1) * 30, unit='d')
    df_calc['Data Término'] = ordem_de_servico + pd.to_timedelta((df_calc['Mês Fim'] - 1) * 30 + 29, unit='d')
    df_calc['Duracao'] = df_calc['Data Término'] - df_calc['Data Início']
    return df_calc

def run_tests(df_para_testar):
    """
    Executa uma suíte de testes nas principais lógicas do script.
    Retorna True se todos os testes passarem, caso contrário, False.
    """
    print("="*40)
    print("INICIANDO SUÍTE DE TESTES AUTOMÁTICOS...")
    print("="*40)

    # --- Teste 1: Carregamento e Validação dos Dados Iniciais ---
    print("\n[TESTE 1/3] Carregamento e Validação dos Dados...", end="")
    try:
        assert not df_para_testar.empty, "O DataFrame não deveria estar vazio."
        required_cols = ['Item', 'Nick', 'Projetos', 'Mês Início', 'Mês Fim']
        assert all(col in df_para_testar.columns for col in required_cols), f"Colunas faltando. Esperado: {required_cols}"
        print(" -> SUCESSO")
    except AssertionError as e:
        print(f" -> FALHA: {e}")
        return False

    # --- Teste 2: Lógica de Cálculo de Datas (função calcular_datas) ---
    print("[TESTE 2/3] Lógica de Cálculo de Datas...", end="")
    try:
        test_data = pd.DataFrame([{'Item': 99, 'Nick': 'Teste', 'Projetos': 'TestProj', 'Mês Início': 1, 'Mês Fim': 2}])
        df_calculado = calcular_datas(test_data)
        
        assert 'Data Início' in df_calculado.columns and 'Data Término' in df_calculado.columns and 'Duracao' in df_calculado.columns
        assert pd.api.types.is_datetime64_any_dtype(df_calculado['Data Início'])
        assert pd.api.types.is_timedelta64_ns_dtype(df_calculado['Duracao'])
        
        expected_start = pd.to_datetime('2025-08-01')
        expected_end = pd.to_datetime('2025-08-01') + pd.to_timedelta((2 - 1) * 30 + 29, unit='d')
        expected_duration = expected_end - expected_start

        assert df_calculado['Data Início'].iloc[0] == expected_start, f"Data de início incorreta."
        assert df_calculado['Data Término'].iloc[0] == expected_end, f"Data de término incorreta."
        assert df_calculado['Duracao'].iloc[0] == expected_duration, "Duração calculada incorretamente."
        print(" -> SUCESSO")
    except AssertionError as e:
        print(f" -> FALHA: {e}")
        return False

    # --- Teste 3: Lógica de Atualização de Tarefas (simula a callback) ---
    print("[TESTE 3/3] Lógica de Atualização de Tarefas...", end="")
    try:
        df_com_datas = calcular_datas(df_para_testar.copy())
        json_data = df_com_datas.to_json(date_format='iso', orient='split')
        task_index = df_com_datas.index[0] 
        task_duration = df_com_datas.loc[task_index, 'Duracao']
        new_start_date_str = '2025-09-15'
        
        # Replica a lógica da callback update_task_dates
        df_updated = pd.read_json(json_data, orient='split', convert_dates=False)
        df_updated.update(df_updated[['Data Início', 'Data Término']].apply(pd.to_datetime))
        df_updated['Duracao'] = pd.to_timedelta(df_updated['Duracao'])
        new_start_dt = pd.to_datetime(new_start_date_str)
        df_updated.loc[task_index, 'Data Início'] = new_start_dt
        df_updated.loc[task_index, 'Data Término'] = new_start_dt + task_duration

        assert df_updated.loc[task_index, 'Data Início'] == new_start_dt, "Data de início não foi atualizada."
        assert df_updated.loc[task_index, 'Data Término'] == (new_start_dt + task_duration), "Data de término não foi recalculada."
        print(" -> SUCESSO")
    except Exception as e:
        print(f" -> FALHA: {e}")
        return False

    print("\n" + "="*40)
    print("TODOS OS TESTES PASSARAM COM SUCESSO!")
    print("="*40)
    return True

# ==============================================================================
# 2. FUNÇÃO DE CARREGAMENTO DE DADOS
# ==============================================================================
def load_schedule_data(file_path: Path) -> pd.DataFrame:
    """
    Carrega e valida os dados do cronograma a partir de um arquivo CSV.

    Args:
        file_path (Path): O caminho para o arquivo CSV.

    Returns:
        pd.DataFrame: DataFrame com os dados do cronograma.

    Raises:
        FileNotFoundError: Se o arquivo CSV não for encontrado.
        pd.errors.EmptyDataError: Se o arquivo CSV estiver completamente vazio.
        pd.errors.ParserError: Se houver um erro ao parsear o CSV.
        ValueError: Se as colunas necessárias não forem encontradas ou se o DataFrame
                    resultante estiver vazio após a seleção de colunas.
    """
    required_cols = ['Item', 'Nick', 'Projetos', 'Mês Início', 'Mês Fim']
    col_dtypes = {
        'Item': int,
        'Nick': str,
        'Projetos': str,
        'Mês Início': int,
        'Mês Fim': int
    }
    df = pd.read_csv(file_path, usecols=required_cols, dtype=col_dtypes)
    if df.empty:
        raise ValueError(f"O arquivo CSV em {file_path} está vazio ou não contém as colunas/dados esperados ({required_cols}).")
    
    # Validação adicional para consistência dos meses
    if not (df['Mês Início'] <= df['Mês Fim']).all():
        invalid_rows = df[~(df['Mês Início'] <= df['Mês Fim'])]
        # Adiciona 2 ao índice do DataFrame para corresponder ao número da linha no arquivo CSV (1 para cabeçalho, 1 para 0-based vs 1-based)
        invalid_rows_display = invalid_rows[['Item', 'Mês Início', 'Mês Fim']].copy()
        invalid_rows_display.index = invalid_rows_display.index + 2
        raise ValueError(
            f"Dados inválidos no CSV: 'Mês Início' deve ser menor ou igual a 'Mês Fim'. "
            f"Linhas problemáticas (número da linha no arquivo CSV):\n{invalid_rows_display}"
        )
    return df

# ==============================================================================
# 3. FUNÇÃO PRINCIPAL DA APLICAÇÃO
# ==============================================================================
def main():
    """
    Carrega os dados, roda os testes e, se bem-sucedido, inicia a aplicação Dash.
    """
    print("Carregando dados da fonte...")
    file_path = Path(__file__).resolve().parent / "data" / "cronograma_sop.csv"
    try:
        df_raw = load_schedule_data(file_path)
        print("Dados carregados com sucesso.")
    except Exception as e:
        print(f"Erro CRÍTICO ao carregar os dados de '{file_path}': {e}")
        print("Usando DataFrame de exemplo para continuar.")
        df_raw = pd.DataFrame([
            {'Item': 1, 'Nick': 'Tarefa A', 'Projetos': 'Projeto 1', 'Mês Início': 1, 'Mês Fim': 3},
            {'Item': 2, 'Nick': 'Tarefa B', 'Projetos': 'Projeto 1', 'Mês Início': 4, 'Mês Fim': 6},
            {'Item': 3, 'Nick': 'Tarefa C', 'Projetos': 'Projeto 2', 'Mês Início': 2, 'Mês Fim': 5},
        ])
        
    # Roda os testes antes de definir e iniciar a aplicação
    if run_tests(df_raw.copy()):
        
        # --- PREPARAÇÃO DOS DADOS PARA APLICAÇÃO ---
        df = calcular_datas(df_raw)

        # --- DEFINIÇÃO DA APLICAÇÃO DASH ---
        app = dash.Dash(__name__)
        server = app.server

        app.layout = html.Div(style={'fontFamily': 'Arial, sans-serif', 'padding': '20px'}, children=[
            html.H1("ITA-FZ: Cronograma Interativo da 2ª Etapa da 1ª Fase - SOP", style={'textAlign': 'center', 'color': '#333'}),
            html.Div(className='control-panel', style={'backgroundColor': '#f9f9f9', 'padding': '15px', 'borderRadius': '8px', 'marginBottom': '20px', 'border': '1px solid #ddd'}, children=[
                html.H3("Instruções:", style={'marginTop': '0'}),
                html.P("1. Clique em uma das barras de tarefa no gráfico para selecioná-la."),
                html.P("2. Use o seletor de data abaixo para escolher um novo dia de início para a tarefa."),
                html.P("A duração total da tarefa será mantida automaticamente.", style={'fontWeight': 'bold'}),
                html.Hr(),
                html.Div(style={'display': 'flex', 'alignItems': 'center', 'gap': '20px'}, children=[
                    html.B("Projeto Selecionado:"),
                    html.Span("Nenhuma", id='selected-task-name', style={'color': 'blue', 'fontWeight': 'bold'}),
                    html.B("Nova Data de Início:"),
                    dcc.DatePickerSingle(id='start-date-picker', display_format='DD/MM/YYYY', disabled=True, style={'width': '150px'})
                ])
            ]),
            dcc.Graph(id='gantt-chart', style={'height': '700px'}),
            dcc.Store(id='gantt-data-store', data=df.to_json(date_format='iso', orient='split')),
            dcc.Store(id='selected-task-store', data=None)
        ])

        # --- DEFINIÇÃO DAS CALLBACKS (INTERATIVIDADE) ---
        @app.callback(
            Output('selected-task-store', 'data'),
            Output('selected-task-name', 'children'),
            Output('start-date-picker', 'disabled'),
            Output('start-date-picker', 'date'),
            Input('gantt-chart', 'clickData'),
            State('gantt-data-store', 'data')
        )
        def store_selected_task(clickData, json_data):
            if not clickData: return None, "Nenhuma", True, None
            df_current = pd.read_json(json_data, orient='split', convert_dates=['Data Início', 'Data Término', 'Duracao'])
            task_nick = clickData['points'][0]['y']
            task_info = df_current[df_current['Nick'] == task_nick]
            if task_info.empty: return no_update
            task_index = task_info.index[0]
            task_start_date = task_info.iloc[0]['Data Início']
            return task_index, f"'{task_nick}'", False, task_start_date

        @app.callback(
            Output('gantt-data-store', 'data'),
            Input('start-date-picker', 'date'),
            State('selected-task-store', 'data'),
            State('gantt-data-store', 'data'),
            prevent_initial_call=True
        )
        def update_task_dates(new_start_date, task_index, json_data):
            if not new_start_date or task_index is None: return no_update
            df_updated = pd.read_json(json_data, orient='split', convert_dates=False)
            df_updated.update(df_updated[['Data Início', 'Data Término']].apply(pd.to_datetime))
            df_updated['Duracao'] = pd.to_timedelta(df_updated['Duracao'])
            duration = df_updated.loc[task_index, 'Duracao']
            new_start_dt = pd.to_datetime(new_start_date)
            df_updated.loc[task_index, 'Data Início'] = new_start_dt
            df_updated.loc[task_index, 'Data Término'] = new_start_dt + duration
            return df_updated.to_json(date_format='iso', orient='split')

        @app.callback(Output('gantt-chart', 'figure'), Input('gantt-data-store', 'data'))
        def update_gantt_chart(json_data):
            df_chart = pd.read_json(json_data, orient='split', convert_dates=['Data Início', 'Data Término'])
            df_chart = df_chart.sort_values(by='Item', ascending=False)
            fig = px.timeline(df_chart, x_start='Data Início', x_end='Data Término', y='Nick', color='Projetos', text="Projetos")
            fig.update_traces(insidetextanchor='start')
            fig.update_xaxes(dtick="M1", tick0=ordem_de_servico, tickformat='%b/%Y')
            
            data_os_ts = datetime(2025, 8, 1).timestamp() * 1000
            credenciamento_ts = datetime(2026, 6, 3).timestamp() * 1000
            pre_credenciamento_ts = datetime(2026, 4, 3).timestamp() * 1000
            fim_execucao_ts = datetime(2026, 10, 25).timestamp() * 1000
            fig.add_vline(x=data_os_ts, line_width=2, line_dash="longdashdot", line_color="red", annotation_text="Data da Ordem de Serviço", annotation_position="top")
            fig.add_vline(x=credenciamento_ts, line_width=2, line_dash="longdashdot", line_color="red", annotation_text="Credenciamento", annotation_position="top")
            fig.add_vline(x=pre_credenciamento_ts, line_width=2, line_dash="longdashdot", line_color="red", annotation_text="Pré-Credenciamento", annotation_position="top")
            fig.add_vline(x=fim_execucao_ts, line_width=2, line_dash="longdashdot", line_color="red", annotation_text="Fim da Execução", annotation_position="top")

            fig.update_layout(
                title={'text': "ITA-FZ: 2ªEtapa da 1ª FASE - Cronograma SOP", 'y':0.98, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top', 'font': dict(size=20, color="Black", family="Arial, sans-serif")},
                yaxis_title="Projetos", 
                showlegend=False,
                legend_title_text='Projetos',
                transition_duration=300,
                margin=dict(l=150, r=20, t=80, b=50)
            )
            return fig

        # --- INÍCIO DO SERVIDOR ---
        print("\nIniciando a aplicação Dash. Acesse http://127.0.0.1:8050/ no seu navegador.")
        app.run(debug=True)

    else:
        print("\nA aplicação NÃO será iniciada devido a falhas nos testes.")

# ==============================================================================
# 4. PONTO DE ENTRADA DO SCRIPT
# ==============================================================================
if __name__ == '__main__':
    main()

