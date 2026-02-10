## IR-бенчмарк

Идея бенчмарка состоит в измерении качества извлечения документов по описанию (docstring) типов, методов, функций и т.п., содержащихся в них, в зависимости от используемого алгортима сегментации исходных текстов. Сами docstring при этом удаляются из исходного кода. Помимо представленного алгоритма на основе AST, используются стандартные функции сегментации из LlamaIndex:

- `SentenceSplitter` - базовый алгоритм разбиения текстов на фиксированные сегменты.
- `CodeSplitter` - алгоритм, разбивающий код только по границам блоков кода.
- `BM25` - алгоритм Okapi BM25 (без сегментации, поиск осуществляется по всему документу).

В качестве модели эмбеддингов использовалась [Qwen3-Embedding-0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B). Размер блока для сегментации во всех алгоритмах равен 256. Стоит заметить, что качество SentenceSplitter будет повышаться при увеличении размера блока, т.к. в контекст будет включаться все больше информации.

Для оценки качества извлечения был собран [набор данных](https://huggingface.co/datasets/kmvi/code-ir-dataset), состоящий из трех блоков:

- `docs` - файлы исходного кода (документы) с удаленными из них docstring:
    - `doc_id` - идентификатор документа
    - `file` - имя файла
    - `content` - содержимое файла (с удаленными docstring's)
- `queries` - запросы к документам. В качестве запросов выступают docstring
    - `query_id` - идентификатор запроса
    - `query` - текст запроса
    - `type` - тип элемента кода, к которому относился docstring (тип, либо метод/функция)
- `qrels` - корректные пары запрос/документ
    - `query_id` - идентификатор запроса
    - `doc_id` - идентификатор документа
    
Метрики качества извлечения, полученные на данном наборе данных, представлены в следующей таблице. Для расчета метрик использовалась библиотека [beir](https://github.com/beir-cellar/beir).

<style type="text/css">
#T_e59bf_row3_col4, #T_e59bf_row3_col7, #T_e59bf_row4_col0, #T_e59bf_row4_col1, #T_e59bf_row4_col2, #T_e59bf_row4_col3, #T_e59bf_row4_col5, #T_e59bf_row4_col6, #T_e59bf_row4_col8 {
  background-color: lightgreen;
}
</style>
<table id="T_e59bf">
  <thead>
    <tr>
      <th class="blank level0" >&nbsp;</th>
      <th id="T_e59bf_level0_col0" class="col_heading level0 col0" >NDCG@3</th>
      <th id="T_e59bf_level0_col1" class="col_heading level0 col1" >NDCG@5</th>
      <th id="T_e59bf_level0_col2" class="col_heading level0 col2" >NDCG@10</th>
      <th id="T_e59bf_level0_col3" class="col_heading level0 col3" >Recall@3</th>
      <th id="T_e59bf_level0_col4" class="col_heading level0 col4" >Recall@5</th>
      <th id="T_e59bf_level0_col5" class="col_heading level0 col5" >Recall@10</th>
      <th id="T_e59bf_level0_col6" class="col_heading level0 col6" >P@3</th>
      <th id="T_e59bf_level0_col7" class="col_heading level0 col7" >P@5</th>
      <th id="T_e59bf_level0_col8" class="col_heading level0 col8" >P@10</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th id="T_e59bf_level0_row0" class="row_heading level0 row0" >Random</th>
      <td id="T_e59bf_row0_col0" class="data row0 col0" >0.0141</td>
      <td id="T_e59bf_row0_col1" class="data row0 col1" >0.0164</td>
      <td id="T_e59bf_row0_col2" class="data row0 col2" >0.0267</td>
      <td id="T_e59bf_row0_col3" class="data row0 col3" >0.0185</td>
      <td id="T_e59bf_row0_col4" class="data row0 col4" >0.0235</td>
      <td id="T_e59bf_row0_col5" class="data row0 col5" >0.0568</td>
      <td id="T_e59bf_row0_col6" class="data row0 col6" >0.0068</td>
      <td id="T_e59bf_row0_col7" class="data row0 col7" >0.0056</td>
      <td id="T_e59bf_row0_col8" class="data row0 col8" >0.0063</td>
    </tr>
    <tr>
      <th id="T_e59bf_level0_row1" class="row_heading level0 row1" >BM25</th>
      <td id="T_e59bf_row1_col0" class="data row1 col0" >0.2564</td>
      <td id="T_e59bf_row1_col1" class="data row1 col1" >0.2933</td>
      <td id="T_e59bf_row1_col2" class="data row1 col2" >0.3335</td>
      <td id="T_e59bf_row1_col3" class="data row1 col3" >0.3026</td>
      <td id="T_e59bf_row1_col4" class="data row1 col4" >0.3907</td>
      <td id="T_e59bf_row1_col5" class="data row1 col5" >0.5123</td>
      <td id="T_e59bf_row1_col6" class="data row1 col6" >0.1097</td>
      <td id="T_e59bf_row1_col7" class="data row1 col7" >0.0854</td>
      <td id="T_e59bf_row1_col8" class="data row1 col8" >0.0567</td>
    </tr>
    <tr>
      <th id="T_e59bf_level0_row2" class="row_heading level0 row2" >SentenceSplitter</th>
      <td id="T_e59bf_row2_col0" class="data row2 col0" >0.5996</td>
      <td id="T_e59bf_row2_col1" class="data row2 col1" >0.6172</td>
      <td id="T_e59bf_row2_col2" class="data row2 col2" >0.6193</td>
      <td id="T_e59bf_row2_col3" class="data row2 col3" >0.6884</td>
      <td id="T_e59bf_row2_col4" class="data row2 col4" >0.7281</td>
      <td id="T_e59bf_row2_col5" class="data row2 col5" >0.7339</td>
      <td id="T_e59bf_row2_col6" class="data row2 col6" >0.2450</td>
      <td id="T_e59bf_row2_col7" class="data row2 col7" >0.1573</td>
      <td id="T_e59bf_row2_col8" class="data row2 col8" >0.0792</td>
    </tr>
    <tr>
      <th id="T_e59bf_level0_row3" class="row_heading level0 row3" >CodeSplitter</th>
      <td id="T_e59bf_row3_col0" class="data row3 col0" >0.5889</td>
      <td id="T_e59bf_row3_col1" class="data row3 col1" >0.6265</td>
      <td id="T_e59bf_row3_col2" class="data row3 col2" >0.6291</td>
      <td id="T_e59bf_row3_col3" class="data row3 col3" >0.7203</td>
      <td id="T_e59bf_row3_col4" class="data row3 col4" >0.8080</td>
      <td id="T_e59bf_row3_col5" class="data row3 col5" >0.8153</td>
      <td id="T_e59bf_row3_col6" class="data row3 col6" >0.2573</td>
      <td id="T_e59bf_row3_col7" class="data row3 col7" >0.1742</td>
      <td id="T_e59bf_row3_col8" class="data row3 col8" >0.0880</td>
    </tr>
    <tr>
      <th id="T_e59bf_level0_row4" class="row_heading level0 row4" >AST Splitter</th>
      <td id="T_e59bf_row4_col0" class="data row4 col0" >0.6072</td>
      <td id="T_e59bf_row4_col1" class="data row4 col1" >0.6360</td>
      <td id="T_e59bf_row4_col2" class="data row4 col2" >0.6413</td>
      <td id="T_e59bf_row4_col3" class="data row4 col3" >0.7380</td>
      <td id="T_e59bf_row4_col4" class="data row4 col4" >0.8056</td>
      <td id="T_e59bf_row4_col5" class="data row4 col5" >0.8206</td>
      <td id="T_e59bf_row4_col6" class="data row4 col6" >0.2644</td>
      <td id="T_e59bf_row4_col7" class="data row4 col7" >0.1740</td>
      <td id="T_e59bf_row4_col8" class="data row4 col8" >0.0885</td>
    </tr>
  </tbody>
</table>

Новый алгоритм в целом показывает увеличение качества извлечения по сравнению со стандартными методами LlamaIndex.

Ноутбуки:
- `make_dataset` - построение набора данных для бенчмарка.
- `calc_metrics` - вычисление метрик, представленных в таблице выше.
