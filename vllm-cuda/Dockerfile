FROM vllm/vllm-openai:v0.15.1-x86_64-cu130

RUN mv /etc/ld.so.conf.d/00-cuda-compat.conf /etc/ld.so.conf.d/cuda-compat.conf && ldconfig
