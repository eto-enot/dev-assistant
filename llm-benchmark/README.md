## Бенчмарк производительности LLM

В данном каталоге определяется контейнер для запуска инструментов vLLM для замера производительности генерации LLM.

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
- `DATASET_NAME` - название датасета (возможные значения: `sharegpt`, `spec_bench`).

Примеры запуска:

```
docker run -it --rm -e MODEL=Qwen/Qwen2.5-1.5B-Instruct llm-benchmark
docker run -it --rm -e MODEL=Qwen/Qwen2.5-1.5B-Instruct -e NUM_PROMPTS=-1 -e DATASET_NAME=spec_bench -e REQUEST_RATE=5 --network diplom_back_net llm-benchmark
```
