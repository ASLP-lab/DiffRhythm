# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Add parameter for PyTorch version with a default empty value
ARG TORCH_VERSION=""


# Set the working directory in the container
WORKDIR /app

# Install system dependencies for eSpeak and other requirements
RUN apt-get update && apt-get install -y \
    git \
    espeak-ng \
    && rm -rf /var/lib/apt/lists/*

# Clone the DiffRhythm repository
RUN git clone https://github.com/ASLP-lab/DiffRhythm.git .

# Copy the requirements file into the container
COPY requirements.txt .

# Extract torch versions from requirements.txt or set to empty strings if not found
RUN TORCH_VERSION_REQ=$(grep -E "^torch==" requirements.txt | cut -d'=' -f3 || echo "") && \
    TORCHAUDIO_VERSION_REQ=$(grep -E "^torchaudio==" requirements.txt | cut -d'=' -f3 || echo "") && \
    TORCHVISION_VERSION_REQ=$(grep -E "^torchvision==" requirements.txt | cut -d'=' -f3 || echo "") && \
    echo "Found in requirements: torch==$TORCH_VERSION_REQ torchaudio==$TORCHAUDIO_VERSION_REQ torchvision==$TORCHVISION_VERSION_REQ"

# Install PyTorch with CUDA support if specified
RUN if [ ! -z "$TORCH_VERSION" ]; then \
        # Check if we need to use specific versions or get the latest
        if [ ! -z "$TORCH_VERSION_REQ" ] && [ ! -z "$TORCHVISION_VERSION_REQ" ] && [ ! -z "$TORCHAUDIO_VERSION_REQ" ]; then \
            echo "Using specific versions from requirements.txt" && \
            TORCH_SPEC="torch==${TORCH_VERSION_REQ}" && \
            TORCHVISION_SPEC="torchvision==${TORCHVISION_VERSION_REQ}" && \
            TORCHAUDIO_SPEC="torchaudio==${TORCHAUDIO_VERSION_REQ}"; \
        else \
            echo "Using latest versions for the selected variant" && \
            TORCH_SPEC="torch" && \
            TORCHVISION_SPEC="torchvision" && \
            TORCHAUDIO_SPEC="torchaudio"; \
        fi && \
        \
        case "$TORCH_VERSION" in \
            "cuda12") \
                pip install --no-cache-dir $TORCH_SPEC $TORCHVISION_SPEC $TORCHAUDIO_SPEC --extra-index-url https://download.pytorch.org/whl/cu121 \
                ;; \
            "cuda128") \
                pip install --no-cache-dir $TORCH_SPEC $TORCHVISION_SPEC $TORCHAUDIO_SPEC --extra-index-url https://download.pytorch.org/whl/nightly/cu128 \
                ;; \
            "cuda11") \
                pip install --no-cache-dir $TORCH_SPEC $TORCHVISION_SPEC $TORCHAUDIO_SPEC --extra-index-url https://download.pytorch.org/whl/cu118 \
                ;; \
            "rocm") \
                # Using the correct syntax for ROCm PyTorch installation
                pip install --no-cache-dir $TORCH_SPEC $TORCHVISION_SPEC $TORCHAUDIO_SPEC --extra-index-url https://download.pytorch.org/whl/rocm6.2 \
                ;; \
            "xpu") \
                # Install PyTorch with Intel XPU support through IPEX
                pip install --no-cache-dir $TORCH_SPEC $TORCHVISION_SPEC $TORCHAUDIO_SPEC && \
                pip install --no-cache-dir intel-extension-for-pytorch --extra-index-url https://pytorch-extension.intel.com/release-whl/stable/xpu/us/ \
                ;; \
            "cpu") \
                pip install --no-cache-dir $TORCH_SPEC $TORCHVISION_SPEC $TORCHAUDIO_SPEC --extra-index-url https://download.pytorch.org/whl/cpu \
                ;; \
            *) \
                pip install --no-cache-dir $TORCH_VERSION \
                ;; \
        esac && \
        # Install remaining requirements, skipping torch packages that might be there
        grep -v -E "^torch==|^torchvision==|^torchaudio==|^torchvision$" requirements.txt > requirements_no_torch.txt && \
        pip install --no-cache-dir --upgrade -r requirements_no_torch.txt && \
        rm requirements_no_torch.txt; \
    else \
        # Install all requirements as specified
        pip install --no-cache-dir --upgrade -r requirements.txt; \
    fi

# Set environment variables for eSpeak (if needed)
ENV PHONEMIZER_ESPEAK_LIBRARY=/usr/lib/x86_64-linux-gnu/libespeak-ng.so.1
ENV PHONEMIZER_ESPEAK_PATH=/usr/bin

# Expose any necessary ports (if applicable)
# EXPOSE 8000

# Create a volume for input/output files
VOLUME ["/app/input", "/app/output"]

# Set the default command to run when starting the container
# You might want to modify this based on specific inference scripts
CMD ["bash"]
