const root = document.documentElement;

const fileInput = document.querySelector("#resume_file");
const form = document.querySelector("#resume-form");
const dropZone = document.querySelector("[data-drop-zone]");
const fileMeta = document.querySelector("[data-file-meta]");
const fileNameTarget = document.querySelector("[data-file-name]");
const fileSizeTarget = document.querySelector("[data-file-size]");
const fileError = document.querySelector("[data-file-error]");
const scanProgress = document.querySelector("[data-scan-progress]");
const loadingMessage = document.querySelector("[data-loading-message]");
const progressBar = document.querySelector("[data-progress-bar]");

const allowedExtensions = ["pdf", "docx", "txt"];
const loadingSteps = [
  "Uploading...",
  "Extracting text...",
  "Analyzing resume signals...",
  "Matching jobs...",
  "Preparing feedback...",
];

function formatBytes(bytes) {
  if (!bytes) return "0 KB";
  const units = ["B", "KB", "MB"];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / 1024 ** index).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

function validateFile(file) {
  if (!file) return "Please choose a resume before scanning.";
  const extension = file.name.split(".").pop().toLowerCase();
  if (!allowedExtensions.includes(extension)) {
    return "Use a PDF, DOCX, or TXT resume file.";
  }
  if (file.size > 10 * 1024 * 1024) {
    return "File size must be 10 MB or smaller.";
  }
  return "";
}

function showSelectedFile(file) {
  const error = validateFile(file);

  if (fileNameTarget && fileSizeTarget && fileMeta && file) {
    fileNameTarget.textContent = file.name;
    fileSizeTarget.textContent = formatBytes(file.size);
    fileMeta.hidden = false;
  }

  if (dropZone && file) {
    const title = dropZone.querySelector(".upload-title");
    const subtitle = dropZone.querySelector(".upload-subtitle");
    if (title) title.textContent = file.name;
    if (subtitle) subtitle.textContent = formatBytes(file.size);
  }

  if (fileError) {
    fileError.textContent = error;
    fileError.hidden = !error;
  }

  fileInput?.classList.toggle("is-invalid", Boolean(error));
  return !error;
}

if (fileInput) {
  fileInput.addEventListener("change", (event) => {
    showSelectedFile(event.target.files[0]);
  });
}

if (dropZone && fileInput) {
  ["dragenter", "dragover"].forEach((eventName) => {
    dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropZone.classList.add("drag-over");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    dropZone.addEventListener(eventName, () => {
      dropZone.classList.remove("drag-over");
    });
  });

  dropZone.addEventListener("drop", (event) => {
    event.preventDefault();
    const file = event.dataTransfer.files[0];
    if (!file) return;
    fileInput.files = event.dataTransfer.files;
    showSelectedFile(file);
  });
}

if (form) {
  form.addEventListener("submit", (event) => {
    const file = fileInput?.files[0];
    if (!showSelectedFile(file)) {
      event.preventDefault();
      return;
    }

    const button = form.querySelector('button[type="submit"]');
    if (button) {
      button.textContent = "Scanning...";
      button.disabled = true;
    }

    if (scanProgress && loadingMessage && progressBar) {
      scanProgress.hidden = false;
      let step = 0;
      progressBar.style.width = "18%";
      loadingMessage.textContent = loadingSteps[step];

      window.setInterval(() => {
        step = Math.min(step + 1, loadingSteps.length - 1);
        loadingMessage.textContent = loadingSteps[step];
        progressBar.style.width = `${Math.min(18 + step * 20, 96)}%`;
      }, 650);
    }
  });
}

const passwordToggles = document.querySelectorAll("[data-toggle-password]");

passwordToggles.forEach((toggle) => {
  toggle.addEventListener("change", (event) => {
    const selectorList = event.target.dataset.togglePassword?.split(",") || [];
    const inputType = event.target.checked ? "text" : "password";

    selectorList.forEach((selector) => {
      const input = document.querySelector(selector.trim());
      if (input) {
        input.type = inputType;
      }
    });
  });
});

function scorePassword(value) {
  let score = 0;
  if (value.length >= 8) score += 25;
  if (/[A-Z]/.test(value)) score += 25;
  if (/[0-9]/.test(value)) score += 25;
  if (/[^A-Za-z0-9]/.test(value)) score += 25;
  return score;
}

function setFieldMessage(input, message, type = "error") {
  const messageTarget = document.querySelector(`[data-message-for="${input.name}"]`);
  input.classList.toggle("is-invalid", type === "error" && Boolean(message));
  if (messageTarget) {
    messageTarget.textContent = message;
    messageTarget.className = `field-message ${message ? type : ""}`;
  }
}

function validateAuthField(input) {
  const value = input.value.trim();

  if (input.dataset.validate === "username") {
    if (value.length < 3) {
      setFieldMessage(input, "Username needs at least 3 characters.");
      return false;
    }
    if (!/^[A-Za-z0-9_.-]+$/.test(value)) {
      setFieldMessage(input, "Use letters, numbers, dots, underscores, or hyphens.");
      return false;
    }
    setFieldMessage(input, "Looks good.", "success");
    return true;
  }

  if (input.dataset.validate === "password") {
    const strength = scorePassword(input.value);
    const bar = document.querySelector("[data-strength-bar]");
    if (bar) {
      bar.style.width = `${strength}%`;
      bar.style.background = strength < 50 ? "var(--danger)" : strength < 75 ? "var(--warning)" : "var(--success)";
    }
    if (input.value.length < 8) {
      setFieldMessage(input, "Password needs at least 8 characters.");
      return false;
    }
    setFieldMessage(input, strength >= 75 ? "Strong password." : "Add uppercase, number, or symbol.", strength >= 75 ? "success" : "error");
    return strength >= 50;
  }

  if (input.dataset.validate === "login-password") {
    if (input.value.length < 8) {
      setFieldMessage(input, "Password needs at least 8 characters.");
      return false;
    }
    setFieldMessage(input, "Ready to sign in.", "success");
    return true;
  }

  if (input.dataset.validate === "confirm") {
    const password = document.querySelector("#register_password");
    if (password && input.value !== password.value) {
      setFieldMessage(input, "Passwords do not match.");
      return false;
    }
    setFieldMessage(input, input.value ? "Passwords match." : "", input.value ? "success" : "error");
    return Boolean(input.value);
  }

  return true;
}

document.querySelectorAll("[data-auth-form]").forEach((authForm) => {
  const inputs = authForm.querySelectorAll("[data-validate]");

  inputs.forEach((input) => {
    input.addEventListener("input", () => validateAuthField(input));
    input.addEventListener("blur", () => validateAuthField(input));
  });

  authForm.addEventListener("submit", (event) => {
    const isValid = Array.from(inputs).every((input) => validateAuthField(input));
    if (!isValid) {
      event.preventDefault();
    }
  });
});

function parseChartData(canvas) {
  return {
    labels: JSON.parse(canvas.dataset.labels || "[]"),
    values: JSON.parse(canvas.dataset.values || "[]"),
  };
}

function chartColors() {
  const styles = getComputedStyle(root);
  return {
    text: styles.getPropertyValue("--text").trim(),
    muted: styles.getPropertyValue("--muted").trim(),
    accent: styles.getPropertyValue("--accent").trim(),
    accentStrong: styles.getPropertyValue("--accent-strong").trim(),
  };
}

function setupCanvas(canvas) {
  const parentWidth = canvas.parentElement?.clientWidth || 640;
  const width = Math.max(320, Math.min(parentWidth, 900));
  const height = canvas.id === "historyTrendChart" ? 280 : 380;
  const ratio = window.devicePixelRatio || 1;
  canvas.width = width * ratio;
  canvas.height = height * ratio;
  canvas.style.width = `${width}px`;
  canvas.style.height = `${height}px`;
  const ctx = canvas.getContext("2d");
  ctx.scale(ratio, ratio);
  return { ctx, width, height };
}

function drawWrappedLabel(ctx, text, x, y, maxWidth) {
  const words = text.split(" ");
  let line = "";
  words.forEach((word) => {
    const nextLine = line ? `${line} ${word}` : word;
    if (ctx.measureText(nextLine).width > maxWidth && line) {
      ctx.fillText(line, x, y);
      y += 13;
      line = word;
    } else {
      line = nextLine;
    }
  });
  if (line) ctx.fillText(line, x, y);
}

function renderCriteriaChart() {
  const canvas = document.querySelector("#criteriaChart");
  if (!canvas) return;

  const { labels, values } = parseChartData(canvas);
  const colors = chartColors();
  const { ctx, width, height } = setupCanvas(canvas);
  const left = 170;
  const right = 34;
  const top = 24;
  const rowHeight = Math.max(28, (height - top - 24) / Math.max(labels.length, 1));
  const barWidth = width - left - right;

  ctx.clearRect(0, 0, width, height);
  ctx.font = "12px Inter, system-ui, sans-serif";
  ctx.textBaseline = "middle";
  labels.forEach((label, index) => {
    const value = Number(values[index] || 0);
    const y = top + index * rowHeight + rowHeight / 2;
    ctx.fillStyle = colors.muted;
    drawWrappedLabel(ctx, label, 12, y, left - 28);
    ctx.fillStyle = "rgba(255,255,255,0.09)";
    ctx.fillRect(left, y - 8, barWidth, 16);
    const gradient = ctx.createLinearGradient(left, 0, left + barWidth, 0);
    gradient.addColorStop(0, colors.accent);
    gradient.addColorStop(1, colors.accentStrong);
    ctx.fillStyle = gradient;
    ctx.fillRect(left, y - 8, Math.max(2, (barWidth * value) / 10), 16);
    ctx.fillStyle = colors.text;
    ctx.fillText(`${value}/10`, left + barWidth - 42, y);
  });
}

function renderHistoryTrendChart() {
  const canvas = document.querySelector("#historyTrendChart");
  if (!canvas) return;

  const { labels, values } = parseChartData(canvas);
  const colors = chartColors();
  const { ctx, width, height } = setupCanvas(canvas);
  const padding = { left: 42, right: 24, top: 22, bottom: 44 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;
  const points = values.map((value, index) => {
    const x = padding.left + (chartWidth * index) / Math.max(values.length - 1, 1);
    const y = padding.top + chartHeight - (chartHeight * Number(value || 0)) / 100;
    return { x, y, value: Number(value || 0), label: labels[index] || "" };
  });

  ctx.clearRect(0, 0, width, height);
  ctx.strokeStyle = "rgba(255,255,255,0.1)";
  ctx.fillStyle = colors.muted;
  ctx.font = "12px Inter, system-ui, sans-serif";
  for (let tick = 0; tick <= 100; tick += 25) {
    const y = padding.top + chartHeight - (chartHeight * tick) / 100;
    ctx.beginPath();
    ctx.moveTo(padding.left, y);
    ctx.lineTo(width - padding.right, y);
    ctx.stroke();
    ctx.fillText(String(tick), 8, y + 4);
  }

  if (points.length) {
    ctx.beginPath();
    points.forEach((point, index) => {
      if (index === 0) ctx.moveTo(point.x, point.y);
      else ctx.lineTo(point.x, point.y);
    });
    ctx.strokeStyle = colors.accent;
    ctx.lineWidth = 3;
    ctx.stroke();

    points.forEach((point) => {
      ctx.beginPath();
      ctx.arc(point.x, point.y, 4, 0, Math.PI * 2);
      ctx.fillStyle = colors.accentStrong;
      ctx.fill();
      ctx.fillStyle = colors.text;
      ctx.fillText(String(point.value), point.x - 8, point.y - 12);
    });
  }

  ctx.fillStyle = colors.muted;
  points.forEach((point) => ctx.fillText(point.label, point.x - 18, height - 18));
}

function animateScore() {
  const scoreTarget = document.querySelector("[data-score-value]");
  if (!scoreTarget) return;

  const finalScore = Number(scoreTarget.dataset.scoreValue || 0);
  const duration = 900;
  const start = performance.now();

  function tick(now) {
    const progress = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    const current = Math.round(finalScore * eased);
    scoreTarget.textContent = `${current} / 100`;

    if (progress < 1) {
      requestAnimationFrame(tick);
    }
  }

  requestAnimationFrame(tick);
}

renderCriteriaChart();
renderHistoryTrendChart();
animateScore();
