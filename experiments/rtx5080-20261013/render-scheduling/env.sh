# Workspace-local CUDA environment. Source this file; no system changes.
export CUDA_HOME='/home/ws/文档/ChatGPT/EXP_NUMA/affinity-render-5080/offline_inbox/toolchain/cuda-13.2'
export PATH="$CUDA_HOME/bin:$PATH"
export LD_LIBRARY_PATH="$CUDA_HOME/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
