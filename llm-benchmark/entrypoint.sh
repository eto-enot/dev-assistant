#!/bin/bash

set -e

if [ -z "${MODEL}" ]; then
    echo 'MODEL variable is undefined'
    exit 1
fi

served_model=${SERVED_MODEL_NAME:-'Coder LLM'}
host=${HOST:-vllm_llm}
port=${PORT:-8000}
num_prompts=${NUM_PROMPTS:-10}
dataset=${DATASET_NAME:-sharegpt}
request_rate=${REQUEST_RATE:-4}

extra_args=("$@")
echo "Extra args: ${extra_args[@]}"

case "$dataset" in
    sharegpt)
        dataset_path=/root/ShareGPT_V3_unfiltered_cleaned_split.json
        ;;
    spec_bench)
        dataset_path=/root/question.jsonl
        ;;
    *)
        echo "Unsupported dataset: $dataset"
        echo "Allowed values: sharegpt, spec_bench"
        exit 1
        ;;
esac

vllm bench serve --backend vllm \
    --model "$MODEL" \
    --served-model-name "$served_model" \
    --host "$host" --port $port \
    --endpoint /v1/completions \
    --dataset-name "$dataset" \
    --dataset-path "$dataset_path" \
    --num-prompts $num_prompts \
    --request-rate $request_rate \
    "${extra_args[@]}"
