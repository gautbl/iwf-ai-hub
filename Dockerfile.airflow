FROM apache/airflow:2.7.1-python3.11

USER root
RUN apt-get update && apt-get install -y git gcc && rm -rf /var/lib/apt/lists/*

USER airflow

# Définir le PATH pour les packages user
ENV PATH="/home/airflow/.local/bin:${PATH}"

# Copier d'abord les fichiers de dépendances
COPY pyproject.toml /opt/airflow/
COPY src/ /opt/airflow/src/

# Installer NumPy 1.x d'abord
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    "numpy==1.24.3" \
    "pandas==2.0.3"

# Installer avec versions fixes pour éviter les conflits
RUN pip install --no-cache-dir \
    "duckdb==0.10.2" \
    "dbt-duckdb==1.7.0" \
    "dbt-core==1.7.0" \
    "requests>=2.28.0" \
    "pypdf>=4.0.0"

# Installation unique depuis pyproject.toml
# La contrainte numpy<2 sera respectée
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e /opt/airflow/

# Vérification
RUN python -c "import numpy; print(f'✅ numpy: {numpy.__version__}')" && \
    python -c "import pandas; print(f'✅ pandas: {pandas.__version__}')" && \
    python -c "import duckdb; print(f'✅ duckdb: {duckdb.__version__}')"