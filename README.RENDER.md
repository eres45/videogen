# Deploying MoneyPrinterTurbo on Render

This guide explains how to deploy MoneyPrinterTurbo on Render.com as a web service with optimized settings for reliable operation.

## Prerequisites

1. A [Render.com](https://render.com) account (Standard plan or higher recommended for video processing)
2. API keys for the services you plan to use:
   - [Pexels API Key](https://www.pexels.com/api/) (Recommended for video sources)
   - [Pixabay API Key](https://pixabay.com/api/docs/) (Optional alternative video source)
   - [OpenAI API Key](https://platform.openai.com/api-keys) (or other LLM provider)

## Deployment Steps

### 1. Fork or Clone the Repository

First, make sure you have your own copy of the repository on GitHub or GitLab, as Render requires a Git repository to deploy from.

### 2. Create a New Web Service on Render

1. Log in to your Render account
2. Go to the Dashboard and click on "New +"
3. Select "Web Service"
4. Connect your GitHub/GitLab account and select the MoneyPrinterTurbo repository
5. Configure the service:
   - **Name**: `moneyprinterturbo` (or your preferred name)
   - **Environment**: `Python`
   - **Region**: Choose the region closest to your users
   - **Branch**: `main` (or your default branch)
   - **Build Command**: `./build.sh`
   - **Start Command**: `bash ./start.sh`
   - **Plan**: Standard or higher (required for video processing)

### 3. Set Environment Variables

Add the following **required** environment variables in the Render dashboard:

- `PEXELS_API_KEY`: Your Pexels API key
- `OPENAI_API_KEY`: Your OpenAI API key (or other LLM provider key)

**Optional** environment variables (with defaults):

- `PIXABAY_API_KEY`: Your Pixabay API key (if using Pixabay)
- `VIDEO_SOURCE`: Video source provider (`pexels` or `pixabay`, default: `pexels`)
- `LLM_PROVIDER`: LLM provider to use (default: `openai`)
- `OPENAI_MODEL`: OpenAI model to use (default: `gpt-4o-mini`)
- `SUBTITLE_PROVIDER`: Subtitle generation method (`edge`, `whisper`, or empty to disable, default: `edge`)
- `MAX_CONCURRENT_TASKS`: Maximum number of concurrent video generation tasks (default: `3`)
- `CLEANUP_DAYS`: Days to keep videos before automatic cleanup (default: `2`)
- `LOG_LEVEL`: Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, default: `INFO`)

Render automatically provides these environment variables:
- `PORT`: The port your app should listen on
- `RENDER_EXTERNAL_URL`: The public URL of your service

### 4. Configure Persistent Disk (Recommended)

To ensure your generated videos persist between service restarts:

1. In the Render dashboard, go to your web service settings
2. Navigate to the "Disks" tab
3. Add a new disk:
   - **Name**: `moneyprinterturbo-storage`
   - **Mount Path**: `/MoneyPrinterTurbo/storage`
   - **Size**: At least 10GB (depending on your needs)

### 5. Deploy

Click "Create Web Service" and wait for the deployment to complete. This may take several minutes for the first deployment.

## Usage

Once deployed, you can access:

- Web API documentation: `https://your-service-name.onrender.com/docs`
- Web UI (if enabled): `https://your-service-name.onrender.com/webui/Main.py`
- Health check endpoint: `https://your-service-name.onrender.com/health`

## Enhanced Features in This Deployment

1. **Automatic Cleanup**: Old video files are automatically deleted after the specified number of days to manage disk space.

2. **Health Monitoring**: A `/health` endpoint provides system metrics including CPU, memory, and disk usage.

3. **Persistent Storage**: Configuration for persistent disk storage ensuring videos are preserved between service restarts.

4. **Optimized ImageMagick**: Modified ImageMagick policies to allow processing larger videos and images.

5. **Enhanced Logging**: Configurable logging levels and formats for better debugging.

6. **Fail-safe Configuration**: Default values for all settings ensure the service will run even with minimal configuration.

## Advanced Configuration

The deployment includes a highly customizable configuration system using environment variables. All settings in `config.render.toml` can be overridden using environment variables in the Render dashboard.

### Using Redis for Task Management (Optional)

For better task management with multiple instances:

1. Add a Redis service in your Render account
2. Configure the following environment variables:
   - `ENABLE_REDIS`: Set to `true`
   - `REDIS_HOST`: Your Redis host
   - `REDIS_PORT`: Your Redis port (default: `6379`)
   - `REDIS_PASSWORD`: Your Redis password

## Troubleshooting

1. **Service Crashes**: Check the Render logs and the `/health` endpoint for system resource usage.

2. **Video Generation Fails**: Ensure you have sufficient CPU and memory allocated in your Render plan.

3. **API Key Issues**: Verify your API keys are correctly set in the environment variables.

4. **Disk Space**: If you're running out of disk space, decrease the `CLEANUP_DAYS` setting to remove older files more quickly.
