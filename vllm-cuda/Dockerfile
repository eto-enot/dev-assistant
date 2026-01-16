FROM vllm/vllm-openai:v0.13.0-x86_64

RUN mkdir -p /usr/lib64 && \
    ln -s /usr/local/cuda/targets/x86_64-linux/lib/stubs/libcuda.so /usr/lib64/libcuda.so
