FROM python:3.11-slim

# Install system dependencies + deno (JS runtime for yt-dlp) + ffmpeg
# (ffmpeg is required by ffmpeg-python / Pyrogram media handling and is not
# installed by pip — without it, audio/video/thumbnail features break on
# every Docker-based host: Koyeb, Railway, Render Docker, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    unzip \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install deno
RUN curl -fsSL https://deno.land/install.sh | sh
ENV DENO_INSTALL="/root/.deno"
ENV PATH="${DENO_INSTALL}/bin:${PATH}"

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Default port if the platform doesn't inject one. Docker's EXPOSE doesn't
# support variable expansion, so this is just documentation — bot.py reads
# the real $PORT (or this default) at runtime and binds to it. Koyeb,
# Render, Railway, and Heroku all inject PORT automatically.
ENV PORT=8080
EXPOSE 8080

# Run the bot
CMD ["python", "bot.py"]