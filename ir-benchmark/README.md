## IR-бенчмарк

Идея бенчмарка состоит в измерении качества извлечения документов по описанию (docstring) типов, методов, функций и т.п., содержащихся в них, в зависимости от используемого алгортима сегментации исходных текстов. Сами docstring при этом удаляются из исходного кода. Помимо представленного алгоритма на основе AST, используются стандартные функции сегментации из LlamaIndex:

- `SentenceSplitter` - базовый алгоритм разбиения текстов на фиксированные сегменты.
- `CodeSplitter` - алгоритм, разбивающий код только по границам блоков кода.
- `BM25` - алгоритм Okapi BM25.

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
    
Метрики качества извлечения, полученные на данном наборе данных, представлены в следующей таблице. Для расчета метрик использовалась библиотека [beir](https://github.com/beir-cellar/beir). Оценка релевантности запроса к извлеченным сегментам осуществлялась с помощью LLM [Google Gemma 4](https://huggingface.co/google/gemma-4-26B-A4B-it).

<table>
  <thead>
    <tr>
      <th rowspan="2">&nbsp;</th>
      <th colspan="3">NDCG@k $\uparrow$</th>
      <th colspan="3">Recall@k $\uparrow$</th>
      <th colspan="3">Precision@k $\uparrow$</th>
      <th rowspan="2">Mean<br/>Latency (ms) $\downarrow$</th>
      <th rowspan="2">Mean<br/>Score $\uparrow$</th>
      <th rowspan="2">Mean Relevance<br/>(LLM-as-a-Judge) $\uparrow$</th>
    </tr>
    <tr>
      <th >$k = 3 $</th>
      <th >$k = 5 $</th>
      <th >$k = 10$</th>
      <th >$k = 3 $</th>
      <th >$k = 5 $</th>
      <th >$k = 10$</th>
      <th >$k = 3 $</th>
      <th >$k = 5 $</th>
      <th >$k = 10$</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th id="T_180ef_level0_row0" class="row_heading level0 row0">Random</th>
      <td id="T_180ef_row0_col0" class="data row0 col0">0.0386</td>
      <td id="T_180ef_row0_col1" class="data row0 col1">0.0601</td>
      <td id="T_180ef_row0_col2" class="data row0 col2">0.0834</td>
      <td id="T_180ef_row0_col3" class="data row0 col3">0.0511</td>
      <td id="T_180ef_row0_col4" class="data row0 col4">0.1034</td>
      <td id="T_180ef_row0_col5" class="data row0 col5">0.1714</td>
      <td id="T_180ef_row0_col6" class="data row0 col6">0.0197</td>
      <td id="T_180ef_row0_col7" class="data row0 col7">0.0227</td>
      <td id="T_180ef_row0_col8" class="data row0 col8">0.0184</td>
      <td id="T_180ef_row0_col9" class="data row0 col9" style="font-weight:bold">0.5991</td>
      <td id="T_180ef_row0_col10" class="data row0 col10">-</td>
      <td id="T_180ef_row0_col11" class="data row0 col11">0.0497</td>
    </tr>
    <tr>
      <th id="T_180ef_level0_row1" class="row_heading level0 row1">BM25</th>
      <td id="T_180ef_row1_col0" class="data row1 col0">0.2138</td>
      <td id="T_180ef_row1_col1" class="data row1 col1">0.2586</td>
      <td id="T_180ef_row1_col2" class="data row1 col2">0.2768</td>
      <td id="T_180ef_row1_col3" class="data row1 col3">0.2860</td>
      <td id="T_180ef_row1_col4" class="data row1 col4">0.3938</td>
      <td id="T_180ef_row1_col5" class="data row1 col5">0.4470</td>
      <td id="T_180ef_row1_col6" class="data row1 col6">0.1074</td>
      <td id="T_180ef_row1_col7" class="data row1 col7">0.0876</td>
      <td id="T_180ef_row1_col8" class="data row1 col8">0.0494</td>
      <td id="T_180ef_row1_col9" class="data row1 col9" style="text-decoration:underline">0.6322</td>
      <td id="T_180ef_row1_col10" class="data row1 col10">-</td>
      <td id="T_180ef_row1_col11" class="data row1 col11">0.2461</td>
    </tr>
    <tr>
      <th id="T_180ef_level0_row2" class="row_heading level0 row2">SentenceSplitter</th>
      <td id="T_180ef_row2_col0" class="data row2 col0" style="text-decoration:underline">0.5996</td>
      <td id="T_180ef_row2_col1" class="data row2 col1">0.6172</td>
      <td id="T_180ef_row2_col2" class="data row2 col2">0.6193</td>
      <td id="T_180ef_row2_col3" class="data row2 col3">0.6884</td>
      <td id="T_180ef_row2_col4" class="data row2 col4">0.7281</td>
      <td id="T_180ef_row2_col5" class="data row2 col5">0.7339</td>
      <td id="T_180ef_row2_col6" class="data row2 col6">0.2450</td>
      <td id="T_180ef_row2_col7" class="data row2 col7">0.1573</td>
      <td id="T_180ef_row2_col8" class="data row2 col8">0.0792</td>
      <td id="T_180ef_row2_col9" class="data row2 col9">31.3442</td>
      <td id="T_180ef_row2_col10" class="data row2 col10">0.5694</td>
      <td id="T_180ef_row2_col11" class="data row2 col11">0.6509</td>
    </tr>
    <tr>
      <th id="T_180ef_level0_row3" class="row_heading level0 row3">CodeSplitter</th>
      <td id="T_180ef_row3_col0" class="data row3 col0">0.5889</td>
      <td id="T_180ef_row3_col1" class="data row3 col1" style="text-decoration:underline">0.6265</td>
      <td id="T_180ef_row3_col2" class="data row3 col2" style="text-decoration:underline">0.6291</td>
      <td id="T_180ef_row3_col3" class="data row3 col3" style="text-decoration:underline">0.7203</td>
      <td id="T_180ef_row3_col4" class="data row3 col4" style="text-decoration:underline">0.8080</td>
      <td id="T_180ef_row3_col5" class="data row3 col5" style="text-decoration:underline">0.8153</td>
      <td id="T_180ef_row3_col6" class="data row3 col6" style="text-decoration:underline">0.2573</td>
      <td id="T_180ef_row3_col7" class="data row3 col7" style="text-decoration:underline">0.1742</td>
      <td id="T_180ef_row3_col8" class="data row3 col8" style="text-decoration:underline">0.0880</td>
      <td id="T_180ef_row3_col9" class="data row3 col9">31.6780</td>
      <td id="T_180ef_row3_col10" class="data row3 col10" style="text-decoration:underline">0.6027</td>
      <td id="T_180ef_row3_col11" class="data row3 col11" style="text-decoration:underline">0.7246</td>
    </tr>
    <tr>
      <th id="T_180ef_level0_row4" class="row_heading level0 row4">AST Splitter</th>
      <td id="T_180ef_row4_col0" class="data row4 col0" style="font-weight:bold">0.6104</td>
      <td id="T_180ef_row4_col1" class="data row4 col1" style="font-weight:bold">0.6398</td>
      <td id="T_180ef_row4_col2" class="data row4 col2" style="font-weight:bold">0.6455</td>
      <td id="T_180ef_row4_col3" class="data row4 col3" style="font-weight:bold">0.7414</td>
      <td id="T_180ef_row4_col4" class="data row4 col4" style="font-weight:bold">0.8106</td>
      <td id="T_180ef_row4_col5" class="data row4 col5" style="font-weight:bold">0.8265</td>
      <td id="T_180ef_row4_col6" class="data row4 col6" style="font-weight:bold">0.2657</td>
      <td id="T_180ef_row4_col7" class="data row4 col7" style="font-weight:bold">0.1749</td>
      <td id="T_180ef_row4_col8" class="data row4 col8" style="font-weight:bold">0.0892</td>
      <td id="T_180ef_row4_col9" class="data row4 col9">32.2281</td>
      <td id="T_180ef_row4_col10" class="data row4 col10" style="font-weight:bold">0.6195</td>
      <td id="T_180ef_row4_col11" class="data row4 col11" style="font-weight:bold">0.7384</td>
    </tr>
  </tbody>
</table>


Новый алгоритм в целом показывает увеличение качества извлечения по сравнению со стандартными методами LlamaIndex. Увеличение задержки связано с необходимостью извлечения иерархической структуры узлов с данными.

Кроме того, качество поиска можно дополнительно улучшить, применив следующие подходы:
- Гибридный поиск с использованием алгоритмов BM25 и AST Splitter и слияние результатов с помощью Reciprocal Rerank Fusion (RRF)
- Ранжирование результатов с помощью специальных моделей (например, BGE, RoBERTa, Qwen Reranker)
- Гибридный поиск и ранжирование результатов.

В следующей таблице представлены полученные метрики:

<table>
  <thead>
    <tr>
      <th rowspan="2">&nbsp;</th>
      <th colspan="3">NDCG@k $\uparrow$</th>
      <th colspan="3">Recall@k $\uparrow$</th>
      <th colspan="3">Precision@k $\uparrow$</th>
      <th rowspan="2">Mean<br/>Latency (ms) $\downarrow$</th>
      <th rowspan="2">Mean<br/>Score $\uparrow$</th>
      <th rowspan="2">Mean Relevance<br/>(LLM-as-a-Judge) $\uparrow$</th>
    </tr>
    <tr>
      <th >$k = 3 $</th>
      <th >$k = 5 $</th>
      <th >$k = 10$</th>
      <th >$k = 3 $</th>
      <th >$k = 5 $</th>
      <th >$k = 10$</th>
      <th >$k = 3 $</th>
      <th >$k = 5 $</th>
      <th >$k = 10$</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th id="T_1ad46_level0_row0" class="row_heading level0 row0">AST Splitter + BM25</th>
      <td id="T_1ad46_row0_col0" class="data row0 col0">0.3453</td>
      <td id="T_1ad46_row0_col1" class="data row0 col1">0.4471</td>
      <td id="T_1ad46_row0_col2" class="data row0 col2">0.4792</td>
      <td id="T_1ad46_row0_col3" class="data row0 col3">0.4771</td>
      <td id="T_1ad46_row0_col4" class="data row0 col4">0.7242</td>
      <td id="T_1ad46_row0_col5" class="data row0 col5">0.8145</td>
      <td id="T_1ad46_row0_col6" class="data row0 col6">0.1738</td>
      <td id="T_1ad46_row0_col7" class="data row0 col7">0.1567</td>
      <td id="T_1ad46_row0_col8" class="data row0 col8">0.0882</td>
      <td id="T_1ad46_row0_col9" class="data row0 col9" style="font-weight:bold">33.2067</td>
      <td id="T_1ad46_row0_col10" class="data row0 col10">0.0182</td>
      <td id="T_1ad46_row0_col11" class="data row0 col11">0.6854</td>
    </tr>
    <tr>
      <th id="T_1ad46_level0_row1" class="row_heading level0 row1">AST Splitter + BM25 + BGE</th>
      <td id="T_1ad46_row1_col0" class="data row1 col0">0.5570</td>
      <td id="T_1ad46_row1_col1" class="data row1 col1">0.6037</td>
      <td id="T_1ad46_row1_col2" class="data row1 col2">0.6153</td>
      <td id="T_1ad46_row1_col3" class="data row1 col3">0.6863</td>
      <td id="T_1ad46_row1_col4" class="data row1 col4">0.7961</td>
      <td id="T_1ad46_row1_col5" class="data row1 col5" style="text-decoration:underline">0.8291</td>
      <td id="T_1ad46_row1_col6" class="data row1 col6">0.2469</td>
      <td id="T_1ad46_row1_col7" class="data row1 col7">0.1726</td>
      <td id="T_1ad46_row1_col8" class="data row1 col8" style="font-weight:bold">0.0899</td>
      <td id="T_1ad46_row1_col9" class="data row1 col9">276.3971</td>
      <td id="T_1ad46_row1_col10" class="data row1 col10">0.2478</td>
      <td id="T_1ad46_row1_col11" class="data row1 col11" style="text-decoration:underline">0.6996</td>
    </tr>
    <tr>
      <th id="T_1ad46_level0_row2" class="row_heading level0 row2">AST Splitter + RoBERTa</th>
      <td id="T_1ad46_row2_col0" class="data row2 col0" style="text-decoration:underline">0.5992</td>
      <td id="T_1ad46_row2_col1" class="data row2 col1" style="text-decoration:underline">0.6317</td>
      <td id="T_1ad46_row2_col2" class="data row2 col2" style="text-decoration:underline">0.6335</td>
      <td id="T_1ad46_row2_col3" class="data row2 col3" style="font-weight:bold">0.7444</td>
      <td id="T_1ad46_row2_col4" class="data row2 col4" style="font-weight:bold">0.8213</td>
      <td id="T_1ad46_row2_col5" class="data row2 col5">0.8265</td>
      <td id="T_1ad46_row2_col6" class="data row2 col6" style="font-weight:bold">0.2676</td>
      <td id="T_1ad46_row2_col7" class="data row2 col7" style="font-weight:bold">0.1773</td>
      <td id="T_1ad46_row2_col8" class="data row2 col8">0.0892</td>
      <td id="T_1ad46_row2_col9" class="data row2 col9">179.0764</td>
      <td id="T_1ad46_row2_col10" class="data row2 col10">0.4724</td>
      <td id="T_1ad46_row2_col11" class="data row2 col11">0.6411</td>
    </tr>
    <tr>
      <th id="T_1ad46_level0_row3" class="row_heading level0 row3">AST Splitter + Qwen</th>
      <td id="T_1ad46_row3_col0" class="data row3 col0">0.5385</td>
      <td id="T_1ad46_row3_col1" class="data row3 col1">0.5874</td>
      <td id="T_1ad46_row3_col2" class="data row3 col2">0.5949</td>
      <td id="T_1ad46_row3_col3" class="data row3 col3">0.6899</td>
      <td id="T_1ad46_row3_col4" class="data row3 col4">0.8053</td>
      <td id="T_1ad46_row3_col5" class="data row3 col5">0.8265</td>
      <td id="T_1ad46_row3_col6" class="data row3 col6">0.2476</td>
      <td id="T_1ad46_row3_col7" class="data row3 col7">0.1736</td>
      <td id="T_1ad46_row3_col8" class="data row3 col8">0.0892</td>
      <td id="T_1ad46_row3_col9" class="data row3 col9">193.2814</td>
      <td id="T_1ad46_row3_col10" class="data row3 col10" style="font-weight:bold">0.6780</td>
      <td id="T_1ad46_row3_col11" class="data row3 col11">0.5238</td>
    </tr>
    <tr>
      <th id="T_1ad46_level0_row4" class="row_heading level0 row4">AST Splitter + BGE</th>
      <td id="T_1ad46_row4_col0" class="data row4 col0" style="font-weight:bold">0.6253</td>
      <td id="T_1ad46_row4_col1" class="data row4 col1" style="font-weight:bold">0.6563</td>
      <td id="T_1ad46_row4_col2" class="data row4 col2" style="font-weight:bold">0.6618</td>
      <td id="T_1ad46_row4_col3" class="data row4 col3" style="text-decoration:underline">0.7391</td>
      <td id="T_1ad46_row4_col4" class="data row4 col4" style="text-decoration:underline">0.8111</td>
      <td id="T_1ad46_row4_col5" class="data row4 col5">0.8265</td>
      <td id="T_1ad46_row4_col6" class="data row4 col6" style="text-decoration:underline">0.2647</td>
      <td id="T_1ad46_row4_col7" class="data row4 col7" style="text-decoration:underline">0.1752</td>
      <td id="T_1ad46_row4_col8" class="data row4 col8">0.0892</td>
      <td id="T_1ad46_row4_col9" class="data row4 col9" style="text-decoration:underline">151.7253</td>
      <td id="T_1ad46_row4_col10" class="data row4 col10">0.2360</td>
      <td id="T_1ad46_row4_col11" class="data row4 col11" style="font-weight:bold">0.7509</td>
    </tr>
    <tr>
      <th id="T_1ad46_level0_row5" class="row_heading level0 row5">AST Splitter + BM25 + RoBERTa</th>
      <td id="T_1ad46_row5_col0" class="data row5 col0">0.3307</td>
      <td id="T_1ad46_row5_col1" class="data row5 col1">0.4480</td>
      <td id="T_1ad46_row5_col2" class="data row5 col2">0.4734</td>
      <td id="T_1ad46_row5_col3" class="data row5 col3">0.4771</td>
      <td id="T_1ad46_row5_col4" class="data row5 col4">0.7593</td>
      <td id="T_1ad46_row5_col5" class="data row5 col5" style="font-weight:bold">0.8302</td>
      <td id="T_1ad46_row5_col6" class="data row5 col6">0.1712</td>
      <td id="T_1ad46_row5_col7" class="data row5 col7">0.1635</td>
      <td id="T_1ad46_row5_col8" class="data row5 col8" style="text-decoration:underline">0.0898</td>
      <td id="T_1ad46_row5_col9" class="data row5 col9">348.3318</td>
      <td id="T_1ad46_row5_col10" class="data row5 col10" style="text-decoration:underline">0.5029</td>
      <td id="T_1ad46_row5_col11" class="data row5 col11">0.4234</td>
    </tr>
    <tr>
      <th id="T_1ad46_level0_row6" class="row_heading level0 row6">AST Splitter + BM25 + Qwen</th>
      <td id="T_1ad46_row6_col0" class="data row6 col0">0.2327</td>
      <td id="T_1ad46_row6_col1" class="data row6 col1">0.3606</td>
      <td id="T_1ad46_row6_col2" class="data row6 col2">0.4071</td>
      <td id="T_1ad46_row6_col3" class="data row6 col3">0.3354</td>
      <td id="T_1ad46_row6_col4" class="data row6 col4">0.6448</td>
      <td id="T_1ad46_row6_col5" class="data row6 col5">0.7772</td>
      <td id="T_1ad46_row6_col6" class="data row6 col6">0.1246</td>
      <td id="T_1ad46_row6_col7" class="data row6 col7">0.1394</td>
      <td id="T_1ad46_row6_col8" class="data row6 col8">0.0840</td>
      <td id="T_1ad46_row6_col9" class="data row6 col9">370.5733</td>
      <td id="T_1ad46_row6_col10" class="data row6 col10">0.2543</td>
      <td id="T_1ad46_row6_col11" class="data row6 col11">0.3618</td>
    </tr>
  </tbody>
</table>

Добавление дополнительного ранжирования улучает качество поиска. Гибридный же поиск в целом не дает прироста качества. Вероятно, это связано с тем, что запросы к документам сфорумлированы на естественном языке, а сами документы - на формальном языке программирования.

Ноутбуки:
- `make_dataset.ipynb` - построение набора данных для бенчмарка.
- `calc_metrics.ipynb` - вычисление метрик, представленных в таблице выше.
