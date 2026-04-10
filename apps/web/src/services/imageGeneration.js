/**
 * Nano Banana image generation client.
 *
 * All API keys stay on the server — this module only calls the
 * /generate proxy endpoint on the Maya orchestrator backend.
 *
 * Required env vars (server-side, not exposed to client):
 *   NANO_BANANA_API_KEY
 *   NANO_BANANA_BASE_URL
 */

const POLL_INTERVAL_MS = 3000;
const MAX_POLL_ATTEMPTS = 40; // 2 minutes max

/**
 * Start image generation.
 * Returns { image_url, job_id, status } from the backend.
 * - If status === 'complete', image_url is ready immediately.
 * - If status === 'pending', poll with pollGeneration(job_id).
 */
export async function startGeneration(state, hallId) {
  const resp = await fetch('/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ state, hall_id: hallId }),
  });

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || `Generation failed (${resp.status})`);
  }

  return resp.json();
}

/**
 * Poll a pending generation job until it completes or times out.
 * Calls onProgress({ status, attempt }) on each poll.
 * Returns { image_url } when done.
 */
export async function pollGeneration(jobId, onProgress) {
  for (let attempt = 1; attempt <= MAX_POLL_ATTEMPTS; attempt++) {
    await _sleep(POLL_INTERVAL_MS);

    const resp = await fetch(`/generate/${jobId}`);
    if (!resp.ok) {
      throw new Error(`Poll failed (${resp.status})`);
    }
    const data = await resp.json();
    onProgress?.({ status: data.status, attempt });

    if (data.status === 'complete' || data.status === 'succeeded') {
      return { image_url: data.image_url };
    }
    if (data.status === 'failed' || data.status === 'error') {
      throw new Error('Image generation failed on server.');
    }
  }
  throw new Error('Image generation timed out. Please retry.');
}

/**
 * Convenience: start + poll, calling onProgress throughout.
 * Returns { image_url }.
 */
export async function generateAndWait(state, hallId, onProgress) {
  const initial = await startGeneration(state, hallId);
  onProgress?.({ status: initial.status, attempt: 0 });

  if (initial.status === 'complete' || initial.status === 'succeeded') {
    return { image_url: initial.image_url };
  }

  if (!initial.job_id) {
    throw new Error('No job_id returned for async generation.');
  }

  return pollGeneration(initial.job_id, onProgress);
}

function _sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Download a generated image (data-URL) as PNG or JPG.
 * For JPG: composites the image onto a white canvas first (removes alpha).
 *
 * @param {string} dataUrl  - data:image/…;base64,… URL
 * @param {'png'|'jpg'} format
 * @param {string} [basename]  - filename without extension
 */
export function downloadImage(dataUrl, format = 'png', basename = 'maya-visualization') {
  if (format === 'png') {
    _triggerDownload(dataUrl, `${basename}.png`);
    return;
  }

  // JPG: draw onto canvas with white background
  const img = new Image();
  img.onload = () => {
    const canvas = document.createElement('canvas');
    canvas.width  = img.naturalWidth  || 1920;
    canvas.height = img.naturalHeight || 1080;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#fff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0);
    _triggerDownload(canvas.toDataURL('image/jpeg', 0.93), `${basename}.jpg`);
  };
  img.src = dataUrl;
}

function _triggerDownload(href, filename) {
  const a = document.createElement('a');
  a.href = href;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}
