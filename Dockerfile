FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    libgl1-mesa-glx \
    libglib2.0-0 \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Clone the repository
RUN git clone https://github.com/dms1981/python-ocr.git /app

# Set up working directory
WORKDIR /app

# Install Python dependencies
RUN pip install --no-cache-dir \
    pytesseract \
    pdf2image \
    opencv-python \
    Pillow

# Create volume for input/output
VOLUME /data

# Set entrypoint
ENTRYPOINT ["python", "app/pdf_ocr.py"]

# Default command
CMD ["--help"]