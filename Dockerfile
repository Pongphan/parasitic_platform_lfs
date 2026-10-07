FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    YOLO_CONFIG_DIR=/tmp

WORKDIR /app

# OpenCV and the inference runtimes need these libraries on Debian slim.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-ai.txt requirements-yolo.txt requirements-rcnn.txt constraints-tested.txt ./

RUN python -m pip install -r requirements-ai.txt -c constraints-tested.txt

# Install the matched CPU builds before Ultralytics can pull in CUDA wheels.
RUN python -m pip install torch torchvision \
    -c constraints-tested.txt \
    --index-url https://download.pytorch.org/whl/cpu

RUN python -m pip install \
    -r requirements-yolo.txt \
    -r requirements-rcnn.txt \
    -c constraints-tested.txt \
    && python -m pip check

RUN useradd --create-home appuser
COPY --chown=appuser:appuser . .
USER appuser

# Fail the build on missing native libraries or incompatible AI packages.
RUN python -c "import cv2, tensorflow, torch, torchvision, ultralytics; \
    assert not torch.backends.cuda.is_built(), 'Expected CPU-only PyTorch'; \
    assert torchvision.ops.nms(torch.tensor([[0., 0., 1., 1.]]), torch.tensor([1.]), 0.5).tolist() == [0]"

EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health', timeout=4)"
CMD ["python", "-m", "streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
