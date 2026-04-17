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
      <th >Random</th>
      <td >0.0141</td>
      <td >0.0164</td>
      <td >0.0267</td>
      <td >0.0185</td>
      <td >0.0235</td>
      <td >0.0568</td>
      <td >0.0068</td>
      <td >0.0056</td>
      <td >0.0063</td>
      <td >0.1558</td>
      <td >-</td>
      <td >0.0136</td>
    </tr>
    <tr>
      <th >BM25</th>
      <td >0.2564</td>
      <td >0.2933</td>
      <td >0.3335</td>
      <td >0.3026</td>
      <td >0.3907</td>
      <td >0.5123</td>
      <td >0.1097</td>
      <td >0.0854</td>
      <td >0.0567</td>
      <td >1.2312</td>
      <td >-</td>
      <td >0.2974</td>
    </tr>
    <tr>
      <th >SentenceSplitter</th>
      <td ><ins>0.5996</ins></td>
      <td >0.6172</td>
      <td >0.6193</td>
      <td >0.6884</td>
      <td >0.7281</td>
      <td >0.7339</td>
      <td >0.2450</td>
      <td >0.1573</td>
      <td >0.0792</td>
      <td><b>372.6455</b></td>
      <td>0.5694</td>
      <td>0.6509</td>
    </tr>
    <tr>
      <th >CodeSplitter</th>
      <td >0.5889</td>
      <td ><ins>0.6265</ins></td>
      <td ><ins>0.6291</ins></td>
      <td ><ins>0.7203</ins></td>
      <td ><b>0.8080</b></td>
      <td ><ins>0.8153</ins></td>
      <td ><ins>0.2573</ins></td>
      <td ><b>0.1742</b></td>
      <td ><ins>0.0880</ins></td>
      <td><ins>500.4722</ins></td>
      <td><ins>0.6027</ins></td>
      <td><ins>0.7246</ins></td>
    </tr>
    <tr>
      <th >AST Splitter</th>
      <td ><b>0.6072</b></td>
      <td ><b>0.6360</b></td>
      <td ><b>0.6413</b></td>
      <td ><b>0.7380</b></td>
      <td ><ins>0.8056</ins></td>
      <td ><b>0.8206</b></td>
      <td ><b>0.2644</b></td>
      <td ><ins>0.1740</ins></td>
      <td ><b>0.0885</b></td>
      <td>582.9660</td>
      <td><b>0.6123<b></td>
      <td><b>0.7372<b></td>
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
      <th>AST Splitter + BM25</th>
      <td>0.3411</td>
      <td>0.4496</td>
      <td>0.4759</td>
      <td>0.4729</td>
      <td>0.7355</td>
      <td>0.8093</td>
      <td>0.1718</td>
      <td>0.1586</td>
      <td>0.0874</td>
      <td>33.1137</td>
      <td>0.0182</td>
      <td>0.6681</td>
    </tr>
    <tr>
      <th>AST Splitter + RoBERTa</th>
      <td><ins>0.5962</ins></td>
      <td><ins>0.6283</ins></td>
      <td><ins>0.6315</ins></td>
      <td><b>0.7365</b></td>
      <td><b>0.8116</b></td>
      <td>0.8206</td>
      <td><b>0.2634</b></td>
      <td><b>0.1752</b></td>
      <td>0.0885</td>
      <td>178.6905</td>
      <td>0.4554</td>
      <td>0.6450</td>
    </tr>
    <tr>
      <th>AST Splitter + Qwen</th>
      <td>0.5343</td>
      <td>0.5777</td>
      <td>0.5873</td>
      <td>0.6909</td>
      <td>0.7940</td>
      <td>0.8206</td>
      <td>0.2476</td>
      <td>0.1711</td>
      <td>0.0885</td>
      <td>187.8500</td>
      <td>0.4115</td>
      <td>0.5210</td>
    </tr>
    <tr>
      <th>AST Splitter + BGE</th>
      <td><b>0.6103</b></td>
      <td><b>0.6461</b></td>
      <td><b>0.6507</b></td>
      <td><ins>0.7238</ins></td>
      <td><ins>0.8075</ins></td>
      <td>0.8206</td>
      <td><ins>0.2596</ins></td>
      <td><ins>0.1744</ins></td>
      <td>0.0885</td>
      <td>150.5946</td>
      <td>0.2173</td>
      <td><b>0.7576</b></td>
    </tr>
    <tr>
      <th>AST Splitter + BM25 + BGE</th>
      <td>0.5366</td>
      <td>0.5850</td>
      <td>0.5979</td>
      <td>0.6745</td>
      <td>0.7882</td>
      <td><b>0.8244</b></td>
      <td>0.2434</td>
      <td>0.1707</td>
      <td><b>0.0894</b></td>
      <td>268.4935</td>
      <td>0.2275</td>
      <td><ins>0.7017</ins></td>
    </tr>
    <tr>
      <th>AST Splitter + BM25 + RoBERTa</th>
      <td>0.3283</td>
      <td>0.4390</td>
      <td>0.4665</td>
      <td>0.4789</td>
      <td>0.7448</td>
      <td><ins>0.8213</ins></td>
      <td>0.1712</td>
      <td>0.1594</td>
      <td><ins>0.0887</ins></td>
      <td>338.0665</td>
      <td>0.4907</td>
      <td>0.4295</td>
    </tr>
    <tr>
      <th>AST Splitter + BM25 + Qwen</th>
      <td>0.2767</td>
      <td>0.3939</td>
      <td>0.4308</td>
      <td>0.4039</td>
      <td>0.6857</td>
      <td>0.7902</td>
      <td>0.1463</td>
      <td>0.1484</td>
      <td>0.0855</td>
      <td>353.2382</td>
      <td>0.4149</td>
      <td>0.3828</td>
    </tr>
  </tbody>
</table>

Добавление дополнительного ранжирования улучает качество поиска. Гибридный же поиск в целом ухудшает качество. Вероятно, это связано с тем, что запросы к документам сфорумлированы на естественном языке, а сами документы - на формальном языке программирования.

Ноутбуки:
- `make_dataset` - построение набора данных для бенчмарка.
- `calc_metrics` - вычисление метрик, представленных в таблице выше.
