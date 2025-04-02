# Dockerfile now located in the project root directory

# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Add parameter for PyTorch version with a default empty value
ARG TORCH_VERSION=""


# Set the working directory in the container
WORKDIR /app

# Install system dependencies for eSpeak and other requirements (removed git)
RUN apt-get update && apt-get install -y \
    espeak-ng \
    && rm -rf /var/lib/apt/lists/*

# Copy application code from the repository root (build context) to /app
# This command now copies the root requirements.txt directly into /app
COPY . .

# --- NO LONGER NEEDED: Explicit copy from a 'docker' subdir ---
# The line 'COPY docker/requirements.txt .' is removed as it's incorrect/unnecessary here.
# The 'COPY . .' above already copied the root requirements.txt to /app/requirements.txt.

# --- PyTorch Installation Logic (Relies on the root requirements.txt copied to /app) ---

# Extract torch-related versions from the root requirements.txt (now at /app/requirements.txt)
RUN TORCH_VERSION_REQ=$(grep -E "^torch==" requirements.txt | cut -d'=' -f3 || echo "") && \
    TORCHAUDIO_VERSION_REQ=$(grep -E "^torchaudio==" requirements.txt | cut -d'=' -f3 || echo "") && \
    TORCHVISION_VERSION_REQ=$(grep -E "^torchvision==" requirements.txt | cut -d'=' -f3 || echo "") && \
    TORCHMETRICS_VERSION_REQ=$(grep -E "^torchmetrics==" requirements.txt | cut -d'=' -f3 || echo "") && \
    echo "Found in requirements: torch==$TORCH_VERSION_REQ, torchaudio==$TORCHAUDIO_VERSION_REQ, torchvision==$TORCHVISION_VERSION_REQ, torchmetrics==$TORCHMETRICS_VERSION_REQ"

# Install PyTorch and related packages based on TORCH_VERSION build-arg
RUN if [ ! -z "$TORCH_VERSION" ]; then \
        # Check if we need to use specific versions from requirements.txt or get the latest versions
        if [ ! -z "$TORCH_VERSION_REQ" ] && [ ! -z "$TORCHVISION_VERSION_REQ" ] && [ ! -z "$TORCHAUDIO_VERSION_REQ" ] && [ ! -z "$TORCHMETRICS_VERSION_REQ" ]; then \
            echo "Using specific versions from requirements.txt" && \
            TORCH_SPEC="torch==${TORCH_VERSION_REQ}" && \
            TORCHVISION_SPEC="torchvision==${TORCHVISION_VERSION_REQ}" && \
            TORCHAUDIO_SPEC="torchaudio==${TORCHAUDIO_VERSION_REQ}" && \
            TORCHMETRICS_SPEC="torchmetrics==${TORCHMETRICS_VERSION_REQ}"; \
        else \
            echo "Using latest versions for the selected variant" && \
            TORCH_SPEC="torch" && \
            TORCHVISION_SPEC="torchvision" && \
            TORCHAUDIO_SPEC="torchaudio" && \
            TORCHMETRICS_SPEC="torchmetrics"; \
        fi && \
        \
        case "$TORCH_VERSION" in \
            "cuda12") \
                pip install --no-cache-dir $TORCH_SPEC $TORCHVISION_SPEC $TORCHAUDIO_SPEC $TORCHMETRICS_SPEC --extra-index-url https://download.pytorch.org/whl/cu121 \
                ;; \
            "cuda128") \
                pip install --no-cache-dir $TORCH_SPEC $TORCHVISION_SPEC $TORCHAUDIO_SPEC $TORCHMETRICS_SPEC --extra-index-url https://download.pytorch.org/whl/nightly/cu128 \
                ;; \
            "cuda11") \
                pip install --no-cache-dir $TORCH_SPEC $TORCHVISION_SPEC $TORCHAUDIO_SPEC $TORCHMETRICS_SPEC --extra-index-url https://download.pytorch.org/whl/cu118 \
                ;; \
            "rocm") \
                pip install --no-cache-dir $TORCH_SPEC $TORCHVISION_SPEC $TORCHAUDIO_SPEC $TORCHMETRICS_SPEC --extra-index-url https://download.pytorch.org/whl/rocm6.2 \
                ;; \
            "xpu") \
                pip install --no-cache-dir $TORCH_SPEC $TORCHVISION_SPEC $TORCHAUDIO_SPEC $TORCHMETRICS_SPEC && \
                pip install --no-cache-dir intel-extension-for-pytorch --extra-index-url https://pytorch-extension.intel.com/release-whl/stable/xpu/us/ \
                ;; \
            "cpu") \
                pip install --no-cache-dir $TORCH_SPEC $TORCHVISION_SPEC $TORCHAUDIO_SPEC $TORCHMETRICS_SPEC --extra-index-url https://download.pytorch.org/whl/cpu \
                ;; \
            *) \
                pip install --no-cache-dir $TORCH_VERSION \
                ;; \
        esac && \
        # Install remaining requirements, skipping lines for all forced torch packages
        # This reads the root requirements.txt (at /app/requirements.txt)
        echo "Installing remaining dependencies from requirements.txt..." && \
        grep -v -E "^torch==|^torchvision==|^torchaudio==|^torchmetrics==" requirements.txt > requirements_no_torch.txt && \
        if [ -s requirements_no_torch.txt ]; then \
             pip install --no-cache-dir --upgrade -r requirements_no_torch.txt; \
        else \
             echo "No remaining dependencies to install."; \
        fi && \
        rm requirements_no_torch.txt; \
    else \
        # Install all requirements as specified if no specific TORCH_VERSION is provided
        # This reads the root requirements.txt (at /app/requirements.txt)
        echo "TORCH_VERSION not specified, installing all dependencies from requirements.txt..." && \
        pip install --no-cache-dir --upgrade -r requirements.txt; \
    fi

# --- End PyTorch Installation Logic ---

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
