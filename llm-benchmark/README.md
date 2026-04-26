## Бенчмарк производительности LLM

В данном каталоге определяется контейнер для запуска инструментов vLLM для замера производительности генерации.

### Сборка

```
wget https://huggingface.co/datasets/anon8231489123/ShareGPT_Vicuna_unfiltered/resolve/main/ShareGPT_V3_unfiltered_cleaned_split.json
wget https://raw.githubusercontent.com/hemingkx/Spec-Bench/refs/heads/main/data/spec_bench/question.jsonl
docker build -t llm-benchmark .
```

### Запуск

Поддерживаются следующие параметры:
- `MODEL` - (обязательно) имя модели.
- `SERVED_MODEL_NAME` - имя модели, доступное через OpenAI API.
- `HOST` - имя узла с сервисом OpenAI API.
- `PORT` - порт.
- `NUM_PROMPTS` - общее число запросов к LLM.
- `REQUEST_RATE` - число запросов к LLM в секунду.
- `DATASET_NAME` - название набора данных (возможные значения: `sharegpt`, `spec_bench`).

Примеры запуска:

```
docker run -it --rm -e MODEL=Qwen/Qwen3.5-4B llm-benchmark
docker run -it --rm -e MODEL=Qwen/Qwen3.5-4B -e NUM_PROMPTS=-1 -e DATASET_NAME=spec_bench -e REQUEST_RATE=5 --network diplom_back_net llm-benchmark
```

### Спекулятивное декодирование

В таблице ниже представлены результаты замера производительности генерации со спекулятивным декодированием (SD) с различным числом черновых токенов. Использовалось 50 примеров из набора данных Spec Bench:

<table>
  <thead>
    <tr>
      <th >Draft tokens</th>
      <th >Duration, s $\downarrow$</th>
      <th >Total output tokens</th>
      <th >Token throughput $\uparrow$</th>
      <th >Acceptance rate, % $\uparrow$</th>
      <th >Acceptance length, tok. $\uparrow$</th>
      <th >TTFT, ms $\downarrow$</th>
      <th >TPOT, ms $\downarrow$</th>
      <th >ITL, ms $\downarrow$</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th >SD disabled</th>
      <td >198.01</td>
      <td >7717</td>
      <td >110.93</td>
      <td >-</td>
      <td >-</td>
      <td ><b>82.89 ± 70.80</b></td>
      <td >24.98 ± 0.18</td>
      <td ><b>25.02 ± 0.31</b></td>
    </tr>
    <tr>
      <th >3</th>
      <td ><ins>135.77</ins></td>
      <td >8056</td>
      <td ><ins>164.28</ins></td>
      <td ><b>56.74</b></td>
      <td >2.70</td>
      <td ><ins>105.89 ± 109.73</ins></td>
      <td ><b>16.42 ± 3.58</b></td>
      <td ><ins>43.08 ± 7.27</ins></td>
    </tr>
    <tr>
      <th >4</th>
      <td ><b>132.47</b></td>
      <td >7658</td>
      <td ><b>165.37</b></td>
      <td ><ins>50.08</ins></td>
      <td >3.00</td>
      <td >114.35 ± 106.67</td>
      <td ><ins>17.06 ± 4.37</ins></td>
      <td >48.98 ± 8.05</td>
    </tr>
    <tr>
      <th >5</th>
      <td >136.06</td>
      <td >7594</td>
      <td >160.54</td>
      <td >44.08</td>
      <td >3.20</td>
      <td >119.03 ± 111.35</td>
      <td >17.36 ± 5.36</td>
      <td >53.93 ± 8.24</td>
    </tr>
    <tr>
      <th >6</th>
      <td >136.55</td>
      <td >7658</td>
      <td >160.42</td>
      <td ><ins>50.08</ins></td>
      <td >3.00</td>
      <td >117.92 ± 115.08</td>
      <td >17.41 ± 4.46</td>
      <td >50.04 ± 7.98</td>
    </tr>
    <tr>
      <th >7</th>
      <td >152.44</td>
      <td >8048</td>
      <td >146.26</td>
      <td >37.74</td>
      <td >3.64</td>
      <td >134.62 ± 112.53</td>
      <td >19.48 ± 7.32</td>
      <td >64.72 ± 8.48</td>
    </tr>
    <tr>
      <th >8</th>
      <td >164.28</td>
      <td >7884</td>
      <td >134.72</td>
      <td >32.21</td>
      <td ><ins>3.58</ins></td>
      <td >141.92 ± 115.40</td>
      <td >21.20 ± 8.20</td>
      <td >70.14 ± 8.63</td>
    </tr>
    <tr>
      <th >10</th>
      <td >183.76</td>
      <td >7953</td>
      <td >120.81</td>
      <td >27.21</td>
      <td ><b>3.72</b></td>
      <td >157.51 ± 126.19</td>
      <td >23.59 ± 9.22</td>
      <td >81.15 ± 8.77</td>
    </tr>
  </tbody>
</table>

Применение спекулятивного декодирования существенно снижает время выполнения запросов. Имеет смысл использовать 4-6 черновых токенов для данного подхода.
