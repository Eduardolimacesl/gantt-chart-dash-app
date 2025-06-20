# ==============================================================================
# IMPORTAÇÕES
# ==============================================================================
import dash
from dash import dcc, html, Input, Output, State, no_update
import plotly.express as px
import pandas as pd
from datetime import datetime
from pathlib import Path
import io

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
        df_updated = pd.read_json(io.StringIO(json_data), orient='split', convert_dates=False)
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
        df_inicial_calculado = calcular_datas(df_raw) # Renomeado para clareza

        # --- DEFINIÇÃO DA APLICAÇÃO DASH ---
        app = dash.Dash(__name__)
        server = app.server

        app.layout = html.Div(style={'fontFamily': 'Arial, sans-serif', 'padding': '20px'}, children=[
            html.H1("ITA-FZ: Cronograma Interativo da 2ª Etapa da 1ª Fase - SOP", style={'textAlign': 'center', 'color': '#333'}),
            html.Div(className='control-panel', style={'backgroundColor': '#f9f9f9', 'padding': '15px', 'borderRadius': '8px', 'marginBottom': '20px', 'border': '1px solid #ddd'}, children=[
                html.H3("Instruções:", style={'marginTop': '0'}),
                html.P("1. Clique em uma das barras de tarefa no gráfico para selecioná-la, ou remover a seleção clicando novamente."),
                html.P("2. Use o seletor de data abaixo para escolher um novo dia de início para a tarefa."),
                html.P("A duração total da tarefa será mantida automaticamente.", style={'fontWeight': 'bold'}),
                html.Hr(),
                html.Div(style={'display': 'flex', 'alignItems': 'center', 'gap': '10px', 'flexWrap': 'wrap'}, children=[ # Ajustado gap e adicionado flexWrap
                    html.B("Projeto Selecionado:"),
                    html.Span("Nenhuma", id='selected-task-name', style={'color': 'blue', 'fontWeight': 'bold'}),
                    html.B("Nova Data de Início:"),
                    dcc.DatePickerSingle(id='start-date-picker', display_format='DD/MM/YYYY', disabled=True, style={'width': '150px', 'marginRight': '10px'}),
                    html.Button('Datas Originais', id='reset-dates-button', n_clicks=0, style={'padding': '5px 10px'})
                ])
            ]),
            dcc.Graph(id='gantt-chart', style={'height': '700px'}),
            dcc.Store(id='gantt-data-store', data=df_inicial_calculado.to_json(date_format='iso', orient='split'), storage_type='local'), # Persistir no localStorage
            dcc.Store(id='original-gantt-data-store', data=df_inicial_calculado.to_json(date_format='iso', orient='split')), # Estado original, não persistido
            dcc.Store(id='selected-task-store', data=None, storage_type='memory') # Seleção é efêmera
        ])

        # --- DEFINIÇÃO DAS CALLBACKS (INTERATIVIDADE) ---
        @app.callback(
            Output('selected-task-store', 'data'),
            Output('selected-task-name', 'children'),
            Output('start-date-picker', 'disabled'),
            Output('start-date-picker', 'date'),
            Input('gantt-chart', 'clickData'),
            State('gantt-data-store', 'data'),
            State('selected-task-store', 'data')
        )
        def store_selected_task(clickData, json_data, current_selected_index):
            # Se não houver clique (ex: clique fora das barras), limpa a seleção.
            if not clickData:
                return None, "Nenhuma", True, None

            # Usa io.StringIO para evitar o aviso de depreciação do Pandas
            df_current = pd.read_json(io.StringIO(json_data), orient='split', convert_dates=['Data Início', 'Data Término', 'Duracao'])
            
            task_nick = clickData['points'][0]['y']
            task_info = df_current[df_current['Nick'] == task_nick]

            if task_info.empty:
                return no_update

            clicked_task_index = task_info.index[0]

            # Se a barra clicada já for a selecionada, limpa a seleção.
            if clicked_task_index == current_selected_index:
                return None, "Nenhuma", True, None
            
            # Caso contrário, seleciona a nova tarefa.
            task_start_date = task_info.iloc[0]['Data Início']
            return clicked_task_index, f"'{task_nick}'", False, task_start_date

        @app.callback(
            Output('gantt-data-store', 'data', allow_duplicate=True),
            Output('selected-task-store', 'data', allow_duplicate=True),
            Output('selected-task-name', 'children', allow_duplicate=True),
            Output('start-date-picker', 'disabled', allow_duplicate=True),
            Output('start-date-picker', 'date', allow_duplicate=True),
            Input('reset-dates-button', 'n_clicks'),
            State('original-gantt-data-store', 'data'),
            prevent_initial_call=True
        )
        def reset_to_original_dates(n_clicks, original_json_data):
            if not n_clicks or original_json_data is None:
                # Evita execução desnecessária ou se o estado original não estiver disponível
                return no_update, no_update, no_update, no_update, no_update
            # Retorna os dados originais para o gantt-data-store e limpa a seleção
            return original_json_data, None, "Nenhuma", True, None


        @app.callback(
            Output('gantt-data-store', 'data'),
            Input('start-date-picker', 'date'),
            State('selected-task-store', 'data'),
            State('gantt-data-store', 'data'),
            prevent_initial_call=True
        )
        def update_task_dates(new_start_date, task_index, json_data):
            if not new_start_date or task_index is None:
                return no_update
            # Usa io.StringIO para evitar o aviso de depreciação do Pandas
            df_updated = pd.read_json(io.StringIO(json_data), orient='split', convert_dates=False)
            df_updated.update(df_updated[['Data Início', 'Data Término']].apply(pd.to_datetime))
            df_updated['Duracao'] = pd.to_timedelta(df_updated['Duracao'])
            duration = df_updated.loc[task_index, 'Duracao']
            new_start_dt = pd.to_datetime(new_start_date)
            df_updated.loc[task_index, 'Data Início'] = new_start_dt
            df_updated.loc[task_index, 'Data Término'] = new_start_dt + duration
            return df_updated.to_json(date_format='iso', orient='split')

        @app.callback(
            Output('gantt-chart', 'figure'),
            [Input('gantt-data-store', 'data'),
             Input('selected-task-store', 'data')] # Tarefa selecionada como Input
        )
        def update_gantt_chart(json_data, selected_task_idx_from_store):
            df_chart = pd.read_json(io.StringIO(json_data), orient='split', convert_dates=['Data Início', 'Data Término'])
            df_chart = df_chart.sort_values(by='Item', ascending=False)

            # Obter detalhes da tarefa selecionada (se houver) para destaque
            selected_nick_to_highlight = None
            selected_project_of_highlighted_task = None
            if selected_task_idx_from_store is not None:
                # Usa io.StringIO para evitar o aviso de depreciação do Pandas
                df_full_for_selection_details = pd.read_json(io.StringIO(json_data), orient='split')
                try:
                    # selected_task_idx_from_store é o índice do DataFrame original
                    task_details = df_full_for_selection_details.loc[selected_task_idx_from_store]
                    selected_nick_to_highlight = task_details['Nick']
                    selected_project_of_highlighted_task = task_details['Projetos']
                except KeyError:
                    pass

            fig = px.timeline(df_chart, x_start='Data Início', x_end='Data Término', y='Nick', color='Projetos', text="Projetos")
            fig.update_traces(insidetextanchor='start')
            fig.update_xaxes(dtick="M1", tick0=ordem_de_servico, tickformat='%b/%Y')
            
            # Definir opacidade padrão e destacada
            default_opacity = 1.0
            dimmed_opacity = 0.35 # Ajuste este valor conforme sua preferência

            # Aplicar opacidade e bordas
            for trace in fig.data:
                if not hasattr(trace, 'y') or not trace.y: # Pular se a trace não tiver barras
                    continue

                num_bars_in_trace = len(trace.y)
                
                # Inicializar opacidades e bordas para a trace atual
                current_opacities = [default_opacity] * num_bars_in_trace
                current_line_widths = [0.5] * num_bars_in_trace # Borda sutil padrão
                current_line_colors = ['rgba(0,0,0,0.2)'] * num_bars_in_trace # Cor sutil padrão

                if selected_nick_to_highlight and selected_project_of_highlighted_task:
                    # Se uma tarefa está selecionada, todas as barras ficam opacas por padrão
                    current_opacities = [dimmed_opacity] * num_bars_in_trace
                    
                    # Se esta trace contém a tarefa selecionada
                    if hasattr(trace, 'name') and trace.name == selected_project_of_highlighted_task:
                        if selected_nick_to_highlight in trace.y:
                            try:
                                bar_idx_in_trace = list(trace.y).index(selected_nick_to_highlight)
                                
                                # Destacar a barra selecionada
                                current_opacities[bar_idx_in_trace] = default_opacity  # Opacidade total
                                current_line_widths[bar_idx_in_trace] = 5 # Borda mais espessa
                                # Para um efeito de sombra suave, usar uma cor de borda escura e semi-transparente
                                current_line_colors[bar_idx_in_trace] = trace.marker.color
                            except (ValueError, AttributeError):
                                pass # Ignorar se não encontrar ou atributo faltar
                
                trace.marker.opacity = current_opacities
                trace.marker.line.width = current_line_widths
                trace.marker.line.color = current_line_colors

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
