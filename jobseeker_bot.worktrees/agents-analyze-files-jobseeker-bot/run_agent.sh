#!/bin/bash

LM_IP="198.18.0.1" # Твой актуальный IP из LM Studio

./.venv/bin/aider --openai-api-base http://$LM_IP:1234/v1 \
                  --openai-api-key lm-studio \
                  --model openai/qwen3.6-27b \
                  --set-env LITELLM_STREAM_TIMEOUT=600 \
                  --no-show-model-warnings \
                  --yes
